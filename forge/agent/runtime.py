"""AgentRuntime: The central autonomous loop of Forge.

Orchestrates user goals, LLM reasoning, structured tool invocation, permission checking,
and the iterative test/fix loop.
"""

import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from forge.agent.context import ContextManager
from forge.agent.memory import SessionMemory
from forge.agent.planner import TaskPlanner
from forge.agent.state import AgentEvent, AgentState, ToolExecutionResult
from forge.llm.base import LLMProvider, ToolCall
from forge.permissions.manager import PermissionManager
from forge.tools.registry import ToolRegistry, create_default_registry


class AgentRuntime:
    """Core autonomous coding agent loop."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: Optional[ToolRegistry] = None,
        permissions: Optional[PermissionManager] = None,
        workspace: Optional[str] = None,
        auto_mode: bool = False,
        max_iterations: int = 30,
        event_callback: Optional[Callable[[AgentEvent], Any]] = None,
    ):
        self.llm = llm
        self.workspace = workspace
        self.auto_mode = auto_mode
        self.max_iterations = max_iterations
        self.event_callback = event_callback

        self.tools = tools or create_default_registry(workspace=workspace)
        self.permissions = permissions or PermissionManager(auto_mode=auto_mode)
        self.memory = SessionMemory()
        self.planner = TaskPlanner()
        self.context = ContextManager(
            workspace=workspace,
            auto_mode=auto_mode,
            memory=self.memory,
            planner=self.planner,
        )

        self.messages: List[Dict[str, Any]] = []
        self.state = AgentState.IDLE
        self._cancelled = False

    async def emit(self, event: AgentEvent) -> None:
        """Dispatches an agent event to the UI or logger."""
        if self.event_callback:
            if inspect.iscoroutinefunction(self.event_callback):
                await self.event_callback(event)
            else:
                self.event_callback(event)

    def cancel(self) -> None:
        """Signals the runtime to stop after the current iteration."""
        self._cancelled = True

    async def run(self, user_message: str) -> str:
        """Runs the complete autonomous agent loop for a user request.

        Architecture flow:
        User message -> Context -> LLM -> Tool Call?
            ├── No -> Return final text answer
            └── Yes -> Check permission -> Execute tool -> Tool result -> Loop back to LLM!
        """
        self._cancelled = False
        self.messages.append({"role": "user", "content": user_message})

        iteration = 0
        final_answer = ""

        # Transition state to THINKING
        self.state = AgentState.THINKING
        await self.emit(AgentEvent.state_changed(self.state))

        while iteration < self.max_iterations and not self._cancelled:
            iteration += 1

            # Build full contextual message history (with prompt & compaction)
            context_messages = await self.context.build_messages(self.messages)

            # Get model completion with structured tool schemas
            self.state = AgentState.THINKING
            await self.emit(AgentEvent.state_changed(self.state))

            schemas = self.tools.schemas()
            response = await self.llm.complete(
                messages=context_messages,
                tools=schemas,
            )

            # Emit text output if present
            if response.content:
                await self.emit(AgentEvent.text_chunk(response.content))

            # Case A: Model has finished and requested NO tool calls
            if response.is_final:
                final_answer = response.content
                self.messages.append({"role": "assistant", "content": final_answer})
                self.state = AgentState.COMPLETED
                await self.emit(AgentEvent.state_changed(self.state))
                await self.emit(AgentEvent.done(final_answer))
                return final_answer

            # Case B: Model requested one or more tool calls
            self.state = AgentState.EXECUTING
            await self.emit(AgentEvent.state_changed(self.state))

            # Record assistant's tool call invocation in history
            self.messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls,
            })

            for call in response.tool_calls:
                if self._cancelled:
                    break

                await self.emit(AgentEvent.tool_start(call.name, call.arguments))

                # 1. Check permissions
                start_time = time.time()
                allowed = await self.permissions.check(call.name, call.arguments)

                if not allowed:
                    result_output = f"ERROR: Permission denied by user for {call.name}."
                    success = False
                else:
                    # 2. Execute tool
                    try:
                        result_output = await self.tools.execute(call.name, **call.arguments)
                        success = not str(result_output).startswith("ERROR:")
                    except Exception as e:
                        result_output = f"ERROR executing tool: {str(e)}"
                        success = False

                duration_ms = int((time.time() - start_time) * 1000)
                exec_result = ToolExecutionResult(
                    tool_name=call.name,
                    arguments=call.arguments,
                    output=result_output,
                    success=success,
                    duration_ms=duration_ms,
                )
                await self.emit(AgentEvent.tool_end(exec_result))

                # 3. Append tool result message for next turn in loop
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": result_output,
                })

        # Max iterations reached or cancelled
        if self._cancelled:
            final_answer = "Task interrupted by user."
        else:
            final_answer = f"Reached maximum autonomous iteration limit ({self.max_iterations})."

        self.state = AgentState.COMPLETED if not self._cancelled else AgentState.FAILED
        await self.emit(AgentEvent.state_changed(self.state))
        await self.emit(AgentEvent.done(final_answer))
        return final_answer
