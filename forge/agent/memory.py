"""In-memory session state, notes, and scratchpad for the agent."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionMemory:
    """Stores working notes, active files, and persistent key-values for the current session."""

    scratchpad: str = ""
    pinned_files: List[str] = field(default_factory=list)
    key_facts: Dict[str, str] = field(default_factory=dict)
    active_task: Optional[str] = None

    def add_fact(self, key: str, value: str) -> None:
        self.key_facts[key] = value

    def pin_file(self, path: str) -> None:
        if path not in self.pinned_files:
            self.pinned_files.append(path)

    def unpin_file(self, path: str) -> None:
        if path in self.pinned_files:
            self.pinned_files.remove(path)

    def set_scratchpad(self, text: str) -> None:
        self.scratchpad = text

    def clear(self) -> None:
        self.scratchpad = ""
        self.pinned_files.clear()
        self.key_facts.clear()
        self.active_task = None
