"""Tests for the AgentRuntime autonomous loop and test/fix cycle."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from forge.agent.runtime import AgentRuntime
from forge.agent.state import AgentEvent
from forge.llm.base import LLMProvider, LLMResponse, ToolCall
from forge.permissions.manager import PermissionManager
from forge.tools.registry import create_default_registry


class MockMultiTurnLLM(LLMProvider):
    """Simulates an LLM that reads a file, edits it, and then reports success."""

    def __init__(self, target_file_path: str):
        super().__init__(model="mock-model")
        self.target_file_path = target_file_path
        self.step = 0

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        self.step += 1

        if self.step == 1:
            # Turn 1: Model calls read_file
            return LLMResponse(
                content="I will read the file to locate the bug.",
                tool_calls=[
                    ToolCall.create("read_file", {"path": self.target_file_path})
                ],
            )
        elif self.step == 2:
            # Turn 2: Model inspected the read lines and now calls edit_file
            return LLMResponse(
                content="I found the timeout bug. Editing file now.",
                tool_calls=[
                    ToolCall.create(
                        "edit_file",
                        {
                            "path": self.target_file_path,
                            "old_text": "timeout = 1000",
                            "new_text": "timeout = 5000",
                        },
                    )
                ],
            )
        else:
            # Turn 3: Model finishes
            return LLMResponse(
                content="The bug has been successfully resolved and timeout set to 5000."
            )


def test_agent_runtime_multi_turn_execution():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.ts"
            test_file.write_text("const timeout = 1000;\nexport default timeout;\n", encoding="utf-8")

            mock_llm = MockMultiTurnLLM(target_file_path=str(test_file))
            events: List[AgentEvent] = []

            runtime = AgentRuntime(
                llm=mock_llm,
                workspace=tmpdir,
                auto_mode=True,
                event_callback=lambda e: events.append(e),
            )

            final_response = await runtime.run("Fix the timeout in config.ts")

            # Verify final response
            assert "successfully resolved" in final_response
            assert mock_llm.step == 3

            # Verify file was actually edited on disk
            updated_content = test_file.read_text(encoding="utf-8")
            assert "timeout = 5000" in updated_content

            # Verify events were dispatched
            tool_names = [e.data["name"] for e in events if e.type == "tool_start"]
            assert "read_file" in tool_names
            assert "edit_file" in tool_names

    asyncio.run(_test())
