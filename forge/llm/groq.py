"""Groq API provider adapter for ultra-fast Llama, Qwen, and OpenAI-OSS models."""

import json
import os
from typing import Any, Dict, List, Optional
import httpx

from forge.llm.base import LLMProvider, LLMResponse, ToolCall

GROQ_DEFAULT_MODEL = "qwen/qwen3.8-27b"

# Convenient model aliases
GROQ_MODEL_ALIASES: Dict[str, str] = {
    "qwen": "qwen/qwen3.8-27b",
    "qwen-coder": "qwen/qwen3.8-27b",
    "qwen-27b": "qwen/qwen3.8-27b",
    "gpt-120b": "openai/gpt-oss-120b",
    "gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-20b": "openai/gpt-oss-20b",
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "compound": "groq/compound",
    "compound-mini": "groq/compound-mini",
    "llama": "llama-3.3-70b-versatile",
    "llama-70b": "llama-3.3-70b-versatile",
    "llama-8b": "llama-3.1-8b-instant",
    "deepseek": "deepseek-r1-distill-llama-70b",
}


class GroqProvider(LLMProvider):
    """Adapter for Groq LPUs providing blazing fast inference on open models."""

    def __init__(
        self,
        model: str = GROQ_DEFAULT_MODEL,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        resolved_model = GROQ_MODEL_ALIASES.get(model.lower(), model)
        super().__init__(model=resolved_model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"
        self.endpoint = f"{self.base_url}/chat/completions"

    @classmethod
    async def list_available_models(cls, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches all models dynamically from the Groq API."""
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if res.status_code == 200:
                    return res.json().get("data", [])
        except Exception:
            pass
        return []

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(content="ERROR: Groq API key not provided. Set GROQ_API_KEY or configure with 'forge config groq_api_key <key>'.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Format messages for OpenAI/Groq standard
        groq_messages = []
        for m in messages:
            msg = dict(m)
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
            groq_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": groq_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if tools:
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

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    return LLMResponse(content=f"Groq API Error ({resp.status_code}): {resp.text}")

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return LLMResponse(content="ERROR: No response returned by Groq.")

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

        except httpx.ConnectError:
            return LLMResponse(content="ERROR: Could not connect to Groq API. Please verify network connection.")
        except Exception as e:
            return LLMResponse(content=f"ERROR during Groq call: {str(e)}")
