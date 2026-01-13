from contextlib import asynccontextmanager
from typing import ClassVar, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from app.harness.recording import RunRecorder
from app.llm import LLM
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import ROLE_TYPE, AgentState, Memory, Message

if TYPE_CHECKING:
    from app.memory import ContextManager
    from app.memory.checkpoint_manager import CheckpointManager, CheckpointData


class BaseAgent(BaseModel):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    run_recorder: Optional[RunRecorder] = Field(default=None, exclude=True)
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    # Three-tier effort control
    effort_level: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Effort level: 'low' (10 steps, quick), 'medium' (20 steps, balanced), 'high' (50 steps, thorough)",
    )

    # Context management for long-running agents (works with any LLM)
    context_manager: Optional["ContextManager"] = Field(default=None, exclude=True)

    # Phase 4: Checkpoint management for state persistence
    checkpoint_manager: Optional["CheckpointManager"] = Field(default=None, exclude=True)

    duplicate_threshold: int = 2

    # Effort level to max steps mapping (class variable, not a field)
    EFFORT_STEPS: ClassVar[Dict[str, int]] = {"low": 10, "medium": 20, "high": 50}

    @property
    def effective_max_steps(self) -> int:
        """Get max steps based on effort level, or use explicit max_steps if set higher"""
        effort_steps = self.EFFORT_STEPS.get(self.effort_level, 20)
        return max(self.max_steps, effort_steps)

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            # Phase 4: Checkpoint on error if enabled
            if self.checkpoint_manager and self.checkpoint_manager.checkpoint_on_error:
                try:
                    import asyncio
                    asyncio.create_task(
                        self.checkpoint_manager.save(
                            f"error_step_{self.current_step}",
                            self,
                            trigger="error",
                            description=f"Error: {str(e)[:200]}"
                        )
                    )
                except Exception:
                    pass  # Don't let checkpoint failure mask original error
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        message = message_map[role](content, **kwargs)
        self.memory.add_message(message)
        self._record_event("message", {"message": message.to_dict()})

    def _record_event(self, event_type: str, payload: Optional[dict] = None) -> None:
        if self.run_recorder:
            self.run_recorder.event(event_type, payload)

    def get_run_summary(self) -> dict:
        tool_messages = [msg for msg in self.memory.messages if msg.role == "tool"]
        assistant_messages = [
            msg for msg in self.memory.messages if msg.role == "assistant"
        ]
        final_output = assistant_messages[-1].content if assistant_messages else None
        summary = {
            "steps": self.current_step,
            "messages": len(self.memory.messages),
            "tool_calls": len(tool_messages),
            "state": self.state.value,
            "final_preview": (final_output or "")[:500],
        }
        if hasattr(self.llm, "total_input_tokens"):
            summary["llm"] = {
                "input_tokens": getattr(self.llm, "total_input_tokens", 0),
                "completion_tokens": getattr(self.llm, "total_completion_tokens", 0),
            }
        return summary

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        self._record_event("run_start", {"request": request})
        if request:
            self.update_memory("user", request)

        # Use effective_max_steps which considers effort_level
        max_steps_limit = self.effective_max_steps

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < max_steps_limit and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{max_steps_limit}")

                # Phase 4: Auto-checkpoint every N steps
                if self.checkpoint_manager:
                    interval = self.checkpoint_manager.auto_checkpoint_interval
                    if interval > 0 and self.current_step % interval == 0:
                        try:
                            await self.checkpoint_manager.save(
                                f"step_{self.current_step}",
                                self,
                                trigger="auto"
                            )
                        except Exception as e:
                            logger.warning(f"Auto-checkpoint failed: {e}")

                # Context management: compact if needed before each step
                if self.context_manager:
                    # Phase 4: Checkpoint before compaction if enabled
                    if self.checkpoint_manager and self.checkpoint_manager.checkpoint_before_compaction:
                        health = await self.context_manager.check_context_health(
                            self.memory.messages, self.llm
                        )
                        if health.get("needs_compaction"):
                            try:
                                await self.checkpoint_manager.save(
                                    f"pre_compaction_{self.context_manager.compaction_count + 1}",
                                    self,
                                    trigger="compaction"
                                )
                            except Exception as e:
                                logger.warning(f"Pre-compaction checkpoint failed: {e}")

                    try:
                        self.memory.messages = await self.context_manager.compact_if_needed(
                            self.memory.messages, self.llm
                        )
                    except Exception as e:
                        logger.warning(f"Context compaction failed: {e}")

                self._record_event("step_start", {"step": self.current_step})
                step_result = await self.step()
                self._record_event(
                    "step_end",
                    {
                        "step": self.current_step,
                        "result_preview": step_result[:500],
                    },
                )

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= max_steps_limit:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({max_steps_limit})")
        await SANDBOX_CLIENT.cleanup()
        summary = self.get_run_summary()
        self._record_event("run_end", summary)
        return "\n".join(results) if results else "No steps executed"

    async def step(self) -> str:
        """
        Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """
        raise NotImplementedError("Subclasses must implement the step() method")

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value

    # Phase 4: Checkpoint serialization methods
    def from_checkpoint_data(self, data: "CheckpointData") -> None:
        """
        Restore agent state from checkpoint data.

        Args:
            data: CheckpointData containing saved state
        """
        from app.schema import Message as MessageClass, ToolCall

        # Restore messages
        self.memory.messages = [
            MessageClass(**msg_data) for msg_data in data.messages
        ]

        # Restore execution state
        self.current_step = data.current_step
        self.state = AgentState(data.state) if data.state else AgentState.IDLE

        # Restore configuration
        self.effort_level = data.effort_level
        self.max_steps = data.max_steps
        if data.system_prompt is not None:
            self.system_prompt = data.system_prompt
        if data.next_step_prompt is not None:
            self.next_step_prompt = data.next_step_prompt

        # Restore tool state if applicable
        if hasattr(self, "tool_calls") and data.tool_calls:
            self.tool_calls = [ToolCall(**tc) for tc in data.tool_calls]
        if hasattr(self, "loaded_tool_names"):
            self.loaded_tool_names = list(data.loaded_tool_names)
        if hasattr(self, "connected_servers"):
            self.connected_servers = dict(data.connected_servers)

        # Restore context stats if context_manager exists
        if self.context_manager and data.compaction_count > 0:
            self.context_manager.compaction_count = data.compaction_count
            self.context_manager.total_tokens_saved = data.total_tokens_saved

        logger.info(
            f"Restored agent from checkpoint: step {data.current_step}, "
            f"{len(data.messages)} messages"
        )

    @classmethod
    async def from_checkpoint(cls, checkpoint_path: str, **kwargs) -> "BaseAgent":
        """
        Create an agent instance from a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint JSON file
            **kwargs: Additional arguments passed to agent constructor

        Returns:
            Agent instance restored from checkpoint
        """
        from app.memory.checkpoint_manager import CheckpointManager

        # Load checkpoint data
        cm = CheckpointManager()
        data = await cm.load_from_path(checkpoint_path)

        # Create new agent instance
        agent = cls(**kwargs)

        # Restore state from checkpoint
        agent.from_checkpoint_data(data)

        logger.info(f"Created agent from checkpoint: {checkpoint_path}")
        return agent
