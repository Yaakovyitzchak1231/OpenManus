"""
Memory module for long-running agents.

Provides context management, persistent storage, and checkpointing that works with any LLM provider.

Components:
- ContextManager: Manages context window, triggers compaction when needed
- MemoryTool: Persistent SQLite storage for important information
- CheckpointManager: Save/restore agent state snapshots (Phase 4)
- Compaction Strategies: Various methods to reduce context size

Usage:
    from app.memory import ContextManager, MemoryTool, CheckpointManager

    # Create context manager
    cm = ContextManager(compaction_threshold_tokens=100000)

    # In agent run loop:
    messages = await cm.compact_if_needed(messages, llm)

    # For persistent storage:
    memory_tool = MemoryTool()
    await memory_tool.execute("store", key="decision_1", value="Use SQLite", category="decisions")

    # For checkpointing:
    cpm = CheckpointManager(agent_id="manus")
    await cpm.save("before_refactor", agent)
    data = await cpm.load("before_refactor")
"""

from .context_manager import ContextManager
from .memory_tool import MemoryTool
from .checkpoint_manager import CheckpointManager, CheckpointData, CheckpointMetadata
from .compaction_strategies import (
    CompactionStrategy,
    ToolResultClearer,
    ThinkingClearer,
    MessageSummarizer,
    SelectiveRetention,
    CompositeStrategy
)

__all__ = [
    "ContextManager",
    "MemoryTool",
    "CheckpointManager",
    "CheckpointData",
    "CheckpointMetadata",
    "CompactionStrategy",
    "ToolResultClearer",
    "ThinkingClearer",
    "MessageSummarizer",
    "SelectiveRetention",
    "CompositeStrategy"
]
