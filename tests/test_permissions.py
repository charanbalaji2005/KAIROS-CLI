"""Tests for permission management and security policies."""

import asyncio
from forge.permissions.policy import (
    OperationType,
    is_dangerous_command,
    classify_tool_operation,
)
from forge.permissions.manager import PermissionManager


def test_dangerous_command_detection():
    assert is_dangerous_command("rm -rf /") is True
    assert is_dangerous_command("sudo apt install") is True
    assert is_dangerous_command("del /s /q C:\\") is True
    assert is_dangerous_command("cargo test") is False
    assert is_dangerous_command("git status") is False


def test_operation_classification():
    assert classify_tool_operation("read_file", {"path": "main.py"}) == OperationType.READ
    assert classify_tool_operation("write_file", {"path": "main.py"}) == OperationType.WRITE
    assert classify_tool_operation("edit_file", {"path": "main.py"}) == OperationType.EDIT
    assert classify_tool_operation("delete_file", {"path": "main.py"}) == OperationType.DELETE
    assert classify_tool_operation("git_push", {}) == OperationType.GIT_PUSH
    assert classify_tool_operation("execute_command", {"command": "gh auth status"}) == OperationType.READ
    assert classify_tool_operation("execute_command", {"command": "git status"}) == OperationType.READ
    assert classify_tool_operation("execute_command", {"command": "python --version"}) == OperationType.READ
    assert classify_tool_operation("execute_command", {"command": "npm run build"}) == OperationType.SHELL


def test_permission_manager_auto_mode():
    async def _test():
        manager = PermissionManager(auto_mode=True)

        # Read is allowed
        assert await manager.check("read_file", {"path": "foo.txt"}) is True

        # Safe write is allowed in auto_mode
        assert await manager.check("write_file", {"path": "foo.txt"}) is True

        # High risk operations require approval even in auto_mode if no callback
        assert await manager.check("delete_file", {"path": "foo.txt"}) is False
        assert await manager.check("execute_command", {"command": "rm -rf node_modules"}) is False

    asyncio.run(_test())
