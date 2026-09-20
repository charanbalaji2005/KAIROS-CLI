"""Session storage: persists and loads conversation sessions to ~/.forge/sessions/."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

from forge.config.loader import get_forge_dir


def get_sessions_dir() -> Path:
    """Returns ~/.forge/sessions/ directory, ensuring it exists."""
    sess_dir = get_forge_dir() / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)
    return sess_dir


def _json_serializable(obj: Any) -> Any:
    """Fallback serializer for objects like ToolCall or custom dataclasses."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def save_session(
    session_id: str,
    workspace: str,
    messages: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Saves session messages and metadata to JSON file."""
    sess_dir = get_sessions_dir()
    sess_file = sess_dir / f"{session_id}.json"

    data = {
        "session_id": session_id,
        "workspace": workspace,
        "updated_at": time.time(),
        "metadata": metadata or {},
        "messages": messages,
    }

    with open(sess_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_json_serializable)

    return sess_file


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Loads a saved session by ID."""
    sess_file = get_sessions_dir() / f"{session_id}.json"
    if not sess_file.exists():
        return None
    try:
        with open(sess_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_sessions(limit: int = 15) -> List[Dict[str, Any]]:
    """Lists saved sessions sorted by most recently modified."""
    sess_dir = get_sessions_dir()
    sessions = []

    for file in sess_dir.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data.get("session_id", file.stem),
                    "workspace": data.get("workspace", "unknown"),
                    "updated_at": data.get("updated_at", file.stat().st_mtime),
                    "message_count": len(data.get("messages", [])),
                })
        except Exception:
            continue

    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions[:limit]
