"""Google Gemini provider adapter supporting google-genai SDK and REST fallback."""

import json
import os
from typing import Any, Dict, List, Optional
import httpx

from forge.llm.base import LLMProvider, LLMResponse, ToolCall


class GeminiProvider(LLMProvider):
    """Adapter for Google Gemini models (gemini-2.5-flash, gemini-1.5-pro, etc.)."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(content="ERROR: Gemini API key not provided. Set GEMINI_API_KEY or configure via 'forge config gemini_api_key <key>'.")

        # Try google.genai SDK if available
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Build system instruction and contents
            system_instruction = None
            contents = []

            for m in messages:
                role = m.get("role")
                content = m.get("content", "")

                if role == "system":
                    system_instruction = content
                elif role == "user":
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=str(content))]))
                elif role == "assistant":
                    parts = []
                    if content:
                        parts.append(types.Part.from_text(text=str(content)))
                    for tc in m.get("tool_calls", []):
                        parts.append(types.Part.from_function_call(
                            name=tc.name if hasattr(tc, "name") else tc["name"],
                            args=tc.arguments if hasattr(tc, "arguments") else tc["arguments"],
                        ))
                    contents.append(types.Content(role="model", parts=parts))
                elif role == "tool":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=m.get("name", "tool"),
                            response={"result": str(content)},
                        )]
                    ))

            # Convert tools to genai FunctionDeclarations
            genai_tools = []
            if tools:
                function_declarations = []
                for t in tools:
                    fn = t.get("function", t)
                    function_declarations.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", fn.get("input_schema", {})),
                    })
                if function_declarations:
                    genai_tools = [types.Tool(function_declarations=function_declarations)]

            config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else self.temperature,
                max_output_tokens=max_tokens or self.max_tokens,
                system_instruction=system_instruction,
                tools=genai_tools or None,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            out_text = response.text or ""
            tool_calls = []

            if response.function_calls:
                for fc in response.function_calls:
                    tool_calls.append(
                        ToolCall.create(
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {},
                        )
                    )

            return LLMResponse(content=out_text, tool_calls=tool_calls)

        except ImportError:
            # Fallback to REST API
            return await self._complete_rest(messages, tools, temperature, max_tokens)
        except Exception as e:
            return LLMResponse(content=f"Gemini Error: {str(e)}")

    async def _complete_rest(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        contents = []
        system_text = None

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_text = content
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": str(content)}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": str(content)}]})
            elif role == "tool":
                contents.append({"role": "user", "parts": [{"text": f"Tool Result: {content}"}]})

        body: Dict[str, Any] = {"contents": contents}
        if system_text:
            body["systemInstruction"] = {"parts": [{"text": system_text}]}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body)
            if resp.status_code != 200:
                return LLMResponse(content=f"Gemini REST Error ({resp.status_code}): {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return LLMResponse(content="No response returned by Gemini.")

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return LLMResponse(content=text)
