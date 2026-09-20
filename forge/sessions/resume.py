"""Session resumption: hydrates an AgentRuntime from a previous session file."""

from typing import Optional

from forge.agent.runtime import AgentRuntime
from forge.sessions.storage import load_session


def resume_session_into_runtime(runtime: AgentRuntime, session_id: str) -> bool:
    """Loads past conversation messages into runtime, returning True if session existed."""
    data = load_session(session_id)
    if not data:
        return False

    messages = data.get("messages", [])
    runtime.messages = messages
    return True
