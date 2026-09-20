"""OpenAI API and OpenAI-compatible endpoint provider adapter."""

import json
import os
from typing import Any, Dict, List, Optional
import httpx

from forge.llm.base import LLMProvider, LLMResponse, ToolCall


class OpenAIProvider(LLMProvider):
    """Adapter for OpenAI models (GPT-4o, GPT-4o-mini, etc.) or compatible endpoints."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            return LLMResponse(content="ERROR: OpenAI API key not provided. Set OPENAI_API_KEY or configure via 'forge config openai_api_key <key>'.")

        headers = {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type": "application/json",
        }

        # Format messages
        openai_messages = []
        for m in messages:
            msg = dict(m)
            # Ensure tool_calls are serialized properly if present
            if "tool_calls" in msg and msg["tool_calls"]:
                serialized_calls = []
                for tc in msg["tool_calls"]:
                    if hasattr(tc, "id"):
                        serialized_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        })
                    else:
                        serialized_calls.append(tc)
                msg["tool_calls"] = serialized_calls
            openai_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if tools:
            # Ensure OpenAI schema
            formatted_tools = []
            for t in tools:
                if "type" in t and t["type"] == "function":
                    formatted_tools.append(t)
                elif "name" in t and "input_schema" in t:
                    formatted_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t.get("description", ""),
                            "parameters": t["input_schema"],
                        },
                    })
            if formatted_tools:
                payload["tools"] = formatted_tools
                payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                return LLMResponse(content=f"OpenAI API Error ({resp.status_code}): {resp.text}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return LLMResponse(content="ERROR: No response returned by model.")

            message = choices[0].get("message", {})
            content = message.get("content") or ""
            raw_tool_calls = message.get("tool_calls", [])

            tool_calls: List[ToolCall] = []
            for rtc in raw_tool_calls:
                fn = rtc.get("function", {})
                args_str = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {"raw_arguments": args_str}

                tool_calls.append(
                    ToolCall(
                        id=rtc.get("id", ""),
                        name=fn.get("name", ""),
                        arguments=args,
                    )
                )

            usage = data.get("usage")
            return LLMResponse(content=content, tool_calls=tool_calls, usage=usage)
