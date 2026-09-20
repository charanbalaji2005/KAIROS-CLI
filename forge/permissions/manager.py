"""Permission manager handling approvals, security prompts, and policy enforcement."""

import inspect
from typing import Callable, Optional, Set
from forge.permissions.policy import (
    OperationType,
    classify_tool_operation,
    is_dangerous_command,
    HIGH_RISK_TOOLS,
)


class PermissionManager:
    """Manages authorization for tool executions."""

    def __init__(self, auto_mode: bool = False, approval_callback: Optional[Callable] = None):
        self.auto_mode = auto_mode
        self.approval_callback = approval_callback
        self.always_allowed_tools: Set[str] = set()
        self.always_allowed_operations: Set[OperationType] = {OperationType.READ}

    def set_auto_mode(self, enabled: bool) -> None:
        self.auto_mode = enabled

    def allow_tool_for_session(self, tool_name: str) -> None:
        self.always_allowed_tools.add(tool_name.lower())

    async def check(self, tool_name: str, arguments: dict) -> bool:
        """Evaluates whether the tool execution is permitted."""
        tool_name_lower = tool_name.lower()
        op_type = classify_tool_operation(tool_name, arguments)

        # 1. READ operations are always allowed
        if op_type == OperationType.READ:
            return True

        # 2. Dangerous command detection (always blocks or requires explicit human confirmation)
        command_str = str(arguments.get("command", "") or arguments.get("test_command", ""))
        if command_str and is_dangerous_command(command_str):
            # Dangerous commands require explicit approval even in auto_mode
            if self.approval_callback:
                return await self._call_approval(
                    tool_name=tool_name,
                    arguments=arguments,
                    warning=f"HIGH RISK: Destructive or dangerous command pattern detected: {command_str}"
                )
            return False

        # 3. Session whitelisted tools
        if tool_name_lower in self.always_allowed_tools:
            return True

        # 4. Auto mode permits safe edits/writes/commands, but still prompts on high-risk operations
        if self.auto_mode:
            if tool_name_lower in HIGH_RISK_TOOLS:
                if self.approval_callback:
                    return await self._call_approval(
                        tool_name=tool_name,
                        arguments=arguments,
                        warning=f"High-impact operation '{tool_name}' requires confirmation"
                    )
                return False
            return True

        # 5. Interactive prompt for user confirmation
        if self.approval_callback:
            return await self._call_approval(tool_name=tool_name, arguments=arguments)

        # Default fallback if no UI callback is registered
        return False

    async def _call_approval(self, tool_name: str, arguments: dict, warning: Optional[str] = None) -> bool:
        if not self.approval_callback:
            return False
        try:
            if inspect.iscoroutinefunction(self.approval_callback):
                return await self.approval_callback(tool_name, arguments, warning)
            return bool(self.approval_callback(tool_name, arguments, warning))
        except Exception:
            return False
