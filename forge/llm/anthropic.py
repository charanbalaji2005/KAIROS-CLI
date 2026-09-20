"""Anthropic Claude API provider adapter."""

import json
import os
from typing import Any, Dict, List, Optional
import httpx

from forge.llm.base import LLMProvider, LLMResponse, ToolCall


class AnthropicProvider(LLMProvider):
    """Adapter for Anthropic Claude models (Claude 3.5 Sonnet, Claude 3 Opus/Haiku)."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(content="ERROR: Anthropic API key not provided. Set ANTHROPIC_API_KEY or configure via 'forge config anthropic_api_key <key>'.")

        # Extract system message if present
        system_content = ""
        claude_messages: List[Dict[str, Any]] = []

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")

            if role == "system":
                system_content = content
            elif role == "user":
                claude_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                # Check for assistant tool calls
                if m.get("tool_calls"):
                    content_blocks = []
                    if content:
                        content_blocks.append({"type": "text", "text": content})
                    for tc in m["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.id if hasattr(tc, "id") else tc.get("id"),
                            "name": tc.name if hasattr(tc, "name") else tc.get("name"),
                            "input": tc.arguments if hasattr(tc, "arguments") else tc.get("arguments", {}),
                        })
                    claude_messages.append({"role": "assistant", "content": content_blocks})
                else:
                    claude_messages.append({"role": "assistant", "content": content})
            elif role == "tool":
                # Convert tool output to user tool_result block
                tool_result_block = {
                    "type": "tool_result",
                    "tool_use_id": m.get("tool_call_id", ""),
                    "content": str(content),
                }
                # Check if last message was already a user message with tool results
                if claude_messages and claude_messages[-1]["role"] == "user" and isinstance(claude_messages[-1]["content"], list):
                    claude_messages[-1]["content"].append(tool_result_block)
                else:
                    claude_messages.append({"role": "user", "content": [tool_result_block]})

        # Format tools for Anthropic
        anthropic_tools = []
        if tools:
            for t in tools:
                if "function" in t:
                    fn = t["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                    })
                elif "input_schema" in t:
                    anthropic_tools.append(t)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": claude_messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        if system_content:
            payload["system"] = system_content
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            if resp.status_code != 200:
                return LLMResponse(content=f"Anthropic API Error ({resp.status_code}): {resp.text}")

            data = resp.json()
            out_text = ""
            tool_calls: List[ToolCall] = []

            for block in data.get("content", []):
                if block.get("type") == "text":
                    out_text += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            arguments=block.get("input", {}),
                        )
                    )

            usage = data.get("usage")
            return LLMResponse(content=out_text, tool_calls=tool_calls, usage=usage)
