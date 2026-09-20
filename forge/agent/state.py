"""Agent states, lifecycle events, and message data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    READING = "reading"
    EXECUTING = "executing"
    TESTING = "testing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolExecutionResult:
    tool_name: str
    arguments: Dict[str, Any]
    output: str
    success: bool = True
    duration_ms: int = 0


@dataclass
class AgentEvent:
    type: str  # "state_changed", "text_chunk", "text_output", "tool_start", "tool_end", "approval_needed", "done", "error"
    data: Any = None
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def state_changed(cls, state: AgentState) -> "AgentEvent":
        return cls("state_changed", state)

    @classmethod
    def text_chunk(cls, text: str) -> "AgentEvent":
        return cls("text_chunk", text)

    @classmethod
    def text_output(cls, text: str) -> "AgentEvent":
        return cls("text_output", text)

    @classmethod
    def tool_start(cls, name: str, arguments: dict) -> "AgentEvent":
        return cls("tool_start", {"name": name, "arguments": arguments})

    @classmethod
    def tool_end(cls, result: ToolExecutionResult) -> "AgentEvent":
        return cls("tool_end", result)

    @classmethod
    def approval_needed(cls, tool_name: str, arguments: dict, warning: Optional[str] = None) -> "AgentEvent":
        return cls("approval_needed", {"tool_name": tool_name, "arguments": arguments, "warning": warning})

    @classmethod
    def done(cls, final_text: str = "") -> "AgentEvent":
        return cls("done", final_text)

    @classmethod
    def error(cls, message: str) -> "AgentEvent":
        return cls("error", message)
