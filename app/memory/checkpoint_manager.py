"""
Context Checkpointing for long-running agents - LLM-agnostic implementation.

Enables saving and restoring agent state snapshots for:
- Resumption after failures
- Branching experiments from saved states
- Recovery from context corruption
- Debugging agent behavior over time
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Literal
from pydantic import BaseModel, Field
import logging
import shutil

if TYPE_CHECKING:
    from app.agent.base import BaseAgent
    from app.schema import Message, ToolCall

logger = logging.getLogger(__name__)


class CheckpointMetadata(BaseModel):
    """Lightweight metadata for checkpoint listing."""

    checkpoint_id: str
    name: str
    agent_name: str
    created_at: datetime
    current_step: int
    message_count: int
    token_count: Optional[int] = None
    trigger: str  # "manual", "auto", "error", "compaction"
    description: Optional[str] = None
    file_path: str


class CheckpointData(BaseModel):
    """Complete agent state snapshot."""

    # Identity
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Critical State - stored as dicts for JSON serialization
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    current_step: int = 0
    state: str = "idle"  # AgentState as string

    # Tool State
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    loaded_tool_names: List[str] = Field(default_factory=list)
    connected_servers: Dict[str, str] = Field(default_factory=dict)

    # Configuration
    effort_level: str = "medium"
    max_steps: int = 20
    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    # Context Stats
    compaction_count: int = 0
    total_tokens_saved: int = 0
    token_count: Optional[int] = None

    # Metadata
    description: Optional[str] = None
    trigger: Literal["manual", "auto", "error", "compaction"] = "manual"

    class Config:
        arbitrary_types_allowed = True

    def to_metadata(self, file_path: str) -> CheckpointMetadata:
        """Convert to lightweight metadata for listing."""
        return CheckpointMetadata(
            checkpoint_id=self.checkpoint_id,
            name=file_path.split("/")[-1].replace(".json", ""),
            agent_name=self.agent_name,
            created_at=self.created_at,
            current_step=self.current_step,
            message_count=len(self.messages),
            token_count=self.token_count,
            trigger=self.trigger,
            description=self.description,
            file_path=file_path,
        )


class CheckpointManager(BaseModel):
    """
    Manages context checkpoints for long-running agents.

    Usage:
        cm = CheckpointManager(agent_id="manus")

        # Save checkpoint
        metadata = await cm.save("before_refactor", agent, description="Clean state")

        # List checkpoints
        checkpoints = await cm.list_checkpoints()

        # Load checkpoint
        data = await cm.load("before_refactor")

        # Resume agent from checkpoint
        agent.from_checkpoint_data(data)
    """

    checkpoint_dir: Path = Field(
        default_factory=lambda: Path("workspace/checkpoints")
    )
    agent_id: str = Field(default="default")
    max_checkpoints: int = Field(
        default=10,
        description="Maximum checkpoints to keep (oldest auto-deleted)"
    )
    auto_checkpoint_interval: int = Field(
        default=5,
        description="Auto-checkpoint every N steps (0 to disable)"
    )
    checkpoint_on_error: bool = Field(
        default=True,
        description="Auto-checkpoint on error states"
    )
    checkpoint_before_compaction: bool = Field(
        default=True,
        description="Checkpoint before context compaction"
    )

    class Config:
        arbitrary_types_allowed = True

    def _get_agent_dir(self) -> Path:
        """Get checkpoint directory for this agent."""
        return self.checkpoint_dir / self.agent_id

    def _get_checkpoint_path(self, name: str) -> Path:
        """Get full path for a checkpoint file."""
        # Sanitize name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self._get_agent_dir() / f"{safe_name}.json"

    def _get_index_path(self) -> Path:
        """Get path to checkpoint index file."""
        return self._get_agent_dir() / "index.json"

    async def save(
        self,
        name: str,
        agent: "BaseAgent",
        trigger: Literal["manual", "auto", "error", "compaction"] = "manual",
        description: Optional[str] = None,
    ) -> CheckpointMetadata:
        """
        Save agent state to a checkpoint.

        Args:
            name: Checkpoint name (used as filename)
            agent: Agent instance to checkpoint
            trigger: What triggered this checkpoint
            description: Optional description for this checkpoint

        Returns:
            CheckpointMetadata with checkpoint info
        """
        # Ensure directory exists
        agent_dir = self._get_agent_dir()
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create checkpoint data from agent
        data = self._agent_to_checkpoint_data(agent, trigger, description)

        # Write checkpoint file atomically
        checkpoint_path = self._get_checkpoint_path(name)
        temp_path = checkpoint_path.with_suffix(".tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data.model_dump(mode="json"), f, indent=2, default=str)
            temp_path.replace(checkpoint_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save checkpoint: {e}") from e

        # Update index
        metadata = data.to_metadata(str(checkpoint_path))
        await self._update_index(metadata)

        # Cleanup old checkpoints if needed
        await self._cleanup_old_checkpoints()

        logger.info(
            f"Checkpoint saved: {name} (step {data.current_step}, "
            f"{len(data.messages)} messages, trigger={trigger})"
        )

        return metadata

    async def load(self, name: str) -> CheckpointData:
        """
        Load checkpoint data by name.

        Args:
            name: Checkpoint name

        Returns:
            CheckpointData with full agent state

        Raises:
            FileNotFoundError: If checkpoint doesn't exist
        """
        checkpoint_path = self._get_checkpoint_path(name)

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {name}")

        with open(checkpoint_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Parse datetime
        if "created_at" in raw_data and isinstance(raw_data["created_at"], str):
            raw_data["created_at"] = datetime.fromisoformat(
                raw_data["created_at"].replace("Z", "+00:00")
            )

        data = CheckpointData(**raw_data)
        logger.info(f"Checkpoint loaded: {name} (step {data.current_step})")
        return data

    async def load_from_path(self, path: str) -> CheckpointData:
        """Load checkpoint from absolute path."""
        checkpoint_path = Path(path)

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {path}")

        with open(checkpoint_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if "created_at" in raw_data and isinstance(raw_data["created_at"], str):
            raw_data["created_at"] = datetime.fromisoformat(
                raw_data["created_at"].replace("Z", "+00:00")
            )

        return CheckpointData(**raw_data)

    async def list_checkpoints(self) -> List[CheckpointMetadata]:
        """
        List all checkpoints for this agent.

        Returns:
            List of CheckpointMetadata sorted by creation time (newest first)
        """
        index_path = self._get_index_path()

        if not index_path.exists():
            return []

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)

            checkpoints = []
            for item in index_data.get("checkpoints", []):
                if "created_at" in item and isinstance(item["created_at"], str):
                    item["created_at"] = datetime.fromisoformat(
                        item["created_at"].replace("Z", "+00:00")
                    )
                checkpoints.append(CheckpointMetadata(**item))

            # Sort by creation time (newest first)
            checkpoints.sort(key=lambda x: x.created_at, reverse=True)
            return checkpoints

        except Exception as e:
            logger.warning(f"Failed to read checkpoint index: {e}")
            return []

    async def delete(self, name: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            name: Checkpoint name

        Returns:
            True if deleted, False if not found
        """
        checkpoint_path = self._get_checkpoint_path(name)

        if not checkpoint_path.exists():
            return False

        checkpoint_path.unlink()
        await self._remove_from_index(name)
        logger.info(f"Checkpoint deleted: {name}")
        return True

    async def get_latest(self) -> Optional[CheckpointData]:
        """
        Get the most recent checkpoint.

        Returns:
            CheckpointData or None if no checkpoints exist
        """
        checkpoints = await self.list_checkpoints()
        if not checkpoints:
            return None

        return await self.load(checkpoints[0].name)

    async def clear_all(self) -> int:
        """
        Delete all checkpoints for this agent.

        Returns:
            Number of checkpoints deleted
        """
        agent_dir = self._get_agent_dir()
        if not agent_dir.exists():
            return 0

        count = 0
        for f in agent_dir.glob("*.json"):
            if f.name != "index.json":
                f.unlink()
                count += 1

        # Clear index
        index_path = self._get_index_path()
        if index_path.exists():
            index_path.unlink()

        logger.info(f"Cleared {count} checkpoints for agent {self.agent_id}")
        return count

    def _agent_to_checkpoint_data(
        self,
        agent: "BaseAgent",
        trigger: str,
        description: Optional[str],
    ) -> CheckpointData:
        """Convert agent state to checkpoint data."""
        from app.schema import AgentState

        # Serialize messages
        messages_data = []
        for msg in agent.memory.messages:
            msg_dict = msg.model_dump(mode="json")
            messages_data.append(msg_dict)

        # Serialize tool calls if present
        tool_calls_data = []
        if hasattr(agent, "tool_calls") and agent.tool_calls:
            for tc in agent.tool_calls:
                tool_calls_data.append(tc.model_dump(mode="json"))

        # Get context stats if available
        compaction_count = 0
        total_tokens_saved = 0
        if hasattr(agent, "context_manager") and agent.context_manager:
            stats = agent.context_manager.get_stats()
            compaction_count = stats.get("compaction_count", 0)
            total_tokens_saved = stats.get("total_tokens_saved", 0)

        # Get connected servers if Manus agent
        connected_servers = {}
        if hasattr(agent, "connected_servers"):
            connected_servers = dict(agent.connected_servers)

        # Get loaded tool names
        loaded_tool_names = []
        if hasattr(agent, "loaded_tool_names"):
            loaded_tool_names = list(agent.loaded_tool_names)

        return CheckpointData(
            agent_name=agent.name,
            messages=messages_data,
            current_step=agent.current_step,
            state=agent.state.value if isinstance(agent.state, AgentState) else str(agent.state),
            tool_calls=tool_calls_data,
            loaded_tool_names=loaded_tool_names,
            connected_servers=connected_servers,
            effort_level=getattr(agent, "effort_level", "medium"),
            max_steps=agent.max_steps,
            system_prompt=agent.system_prompt,
            next_step_prompt=agent.next_step_prompt,
            compaction_count=compaction_count,
            total_tokens_saved=total_tokens_saved,
            trigger=trigger,
            description=description,
        )

    async def _update_index(self, metadata: CheckpointMetadata) -> None:
        """Update the checkpoint index with new metadata."""
        index_path = self._get_index_path()

        # Load existing index or create new
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {"checkpoints": []}

        # Remove existing entry with same name if present
        index_data["checkpoints"] = [
            cp for cp in index_data["checkpoints"]
            if cp.get("name") != metadata.name
        ]

        # Add new entry
        index_data["checkpoints"].append(metadata.model_dump(mode="json"))

        # Write atomically
        temp_path = index_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, default=str)
        temp_path.replace(index_path)

    async def _remove_from_index(self, name: str) -> None:
        """Remove a checkpoint from the index."""
        index_path = self._get_index_path()

        if not index_path.exists():
            return

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        index_data["checkpoints"] = [
            cp for cp in index_data["checkpoints"]
            if cp.get("name") != name
        ]

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, default=str)

    async def _cleanup_old_checkpoints(self) -> None:
        """Remove oldest checkpoints if over limit."""
        checkpoints = await self.list_checkpoints()

        if len(checkpoints) <= self.max_checkpoints:
            return

        # Sort by creation time (oldest last)
        checkpoints.sort(key=lambda x: x.created_at, reverse=True)

        # Remove excess checkpoints
        to_remove = checkpoints[self.max_checkpoints:]
        for cp in to_remove:
            await self.delete(cp.name)
            logger.debug(f"Auto-deleted old checkpoint: {cp.name}")
