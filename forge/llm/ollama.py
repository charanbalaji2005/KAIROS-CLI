"""Ollama local model provider adapter with native tool support and fallback parser."""

import json
import re
import uuid
from typing import Any, Dict, List, Optional
import httpx

from forge.llm.base import LLMProvider, LLMResponse, ToolCall


class OllamaProvider(LLMProvider):
    """Adapter for local models running in Ollama (Qwen2.5-Coder, DeepSeek-Coder, Llama, etc.)."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:3b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/chat"

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        ollama_messages = []
        for m in messages:
            msg = {"role": m.get("role", "user"), "content": m.get("content") or ""}
            if m.get("role") == "tool":
                msg["role"] = "tool"
            ollama_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(self.endpoint, json=payload)
                if resp.status_code != 200:
                    return LLMResponse(content=f"Ollama Error ({resp.status_code}): {resp.text}")

                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                raw_tool_calls = msg.get("tool_calls", [])

                tool_calls: List[ToolCall] = []

                # 1. Check native Ollama tool calls
                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        fn = tc.get("function", {})
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{uuid.uuid4().hex[:8]}",
                                name=fn.get("name", ""),
                                arguments=fn.get("arguments", {}),
                            )
                        )

                # 2. Resilient fallback parser: Check if text contains structured JSON tool call
                if not tool_calls and content and tools:
                    known_tools = set()
                    for t in tools:
                        if "function" in t:
                            known_tools.add(t["function"]["name"])
                        elif "name" in t:
                            known_tools.add(t["name"])

                    parsed_calls, clean_text = self._parse_embedded_tool_calls(content, known_tools)
                    if parsed_calls:
                        tool_calls = parsed_calls
                        content = clean_text

                return LLMResponse(content=content, tool_calls=tool_calls)

        except httpx.ConnectError:
            return LLMResponse(
                content="""Cannot connect to Ollama at http://localhost:11434.

To make Forge work, choose one of these options:

1. Local AI (Free & Offline):
   Install & start Ollama in your terminal:
     curl -fsSL https://ollama.com/install.sh | sh
     ollama pull qwen2.5-coder:3b

2. Or Cloud AI (Gemini / Claude / OpenAI):
   Exit Forge (`/exit`) and configure your provider:
     forge config provider gemini
     forge config gemini_api_key <YOUR_GEMINI_API_KEY>
   (or for Claude):
     forge config provider anthropic
     forge config anthropic_api_key <YOUR_ANTHROPIC_API_KEY>
"""
            )
        except Exception as e:
            return LLMResponse(content=f"ERROR during Ollama call: {str(e)}")

    def _parse_embedded_tool_calls(self, text: str, known_tools: set) -> tuple[List[ToolCall], str]:
        """Extracts JSON tool calls emitted in markdown code blocks by smaller models."""
        calls: List[ToolCall] = []
        cleaned = text

        # Look for ```json { "name": ..., "arguments": ... } ``` blocks
        json_pattern = re.compile(r"```(?:json)?\s*(\{(?:[^{}]|(?R))*\})\s*```", re.DOTALL)
        for match in json_pattern.finditer(text):
            block = match.group(1)
            try:
                data = json.loads(block)
                name = data.get("name") or data.get("tool")
                if name in known_tools:
                    args = data.get("arguments") or data.get("parameters") or {k: v for k, v in data.items() if k not in ("name", "tool")}
                    calls.append(ToolCall.create(name=name, arguments=args))
                    cleaned = cleaned.replace(match.group(0), "")
            except Exception:
                pass

        return calls, cleaned.strip()
