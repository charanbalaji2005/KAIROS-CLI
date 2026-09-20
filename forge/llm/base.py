"""LLM provider interface, message schemas, and response types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents a structured tool call requested by the model."""
    id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def create(cls, name: str, arguments: Dict[str, Any], call_id: Optional[str] = None) -> "ToolCall":
        return cls(
            id=call_id or f"call_{uuid.uuid4().hex[:8]}",
            name=name,
            arguments=arguments,
        )


@dataclass
class LLMResponse:
    """Standardized response from an LLM provider."""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Optional[Dict[str, int]] = None

    @property
    def is_final(self) -> bool:
        """Returns True if the model has finished its thought without requesting tool calls."""
        return len(self.tool_calls) == 0


class LLMProvider(ABC):
    """Abstract interface implemented by all LLM adapters."""

    def __init__(self, model: str, temperature: float = 0.1, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generates a model completion with structured tool support."""
        pass

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Streams text chunks if supported by provider, defaults to non-streaming fallback."""
        resp = await self.complete(messages, tools)
        if resp.content:
            yield resp.content
