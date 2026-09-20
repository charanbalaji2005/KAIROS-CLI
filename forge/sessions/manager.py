"""Session manager: coordinates active session lifecycle."""

import uuid
from typing import Any, Dict, List, Optional

from forge.sessions.storage import save_session, load_session


class SessionManager:
    """Manages active session ID and automatic saving."""

    def __init__(self, workspace: str, session_id: Optional[str] = None):
        self.workspace = workspace
        self.session_id = session_id or uuid.uuid4().hex[:10]
        self.metadata: Dict[str, Any] = {}

    def save(self, messages: List[Dict[str, Any]]) -> None:
        save_session(
            session_id=self.session_id,
            workspace=self.workspace,
            messages=messages,
            metadata=self.metadata,
        )

    def load(self) -> Optional[List[Dict[str, Any]]]:
        data = load_session(self.session_id)
        if data:
            self.metadata = data.get("metadata", {})
            return data.get("messages", [])
        return None
