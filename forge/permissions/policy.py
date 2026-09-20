"""Permission policies, operation types, and dangerous pattern detection."""

from enum import Enum
from typing import List, Set


class PermissionLevel(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class OperationType(str, Enum):
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    SHELL = "shell"
    NETWORK = "network"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    PACKAGE_INSTALL = "package_install"


DANGEROUS_PATTERNS: List[str] = [
    "rm -rf",
    "rmdir /s",
    "del /s",
    "del /f /s",
    "sudo",
    "chmod 777",
    "mkfs",
    "dd if=",
    "> /dev/sd",
    "format ",
    ":(){ :|:& };:",
    "DROP DATABASE",
    "DROP TABLE",
]

HIGH_RISK_TOOLS: Set[str] = {
    "delete_file",
    "git_push",
    "gh_pr_create",
}


def is_dangerous_command(command: str) -> bool:
    """Checks if a command contains high-risk or destructive patterns."""
    lower = command.lower()
    return any(pattern.lower() in lower for pattern in DANGEROUS_PATTERNS)


def classify_tool_operation(tool_name: str, arguments: dict) -> OperationType:
    """Classifies a tool call into an OperationType."""
    name = tool_name.lower()
    if name in ("read_file", "search", "glob_files", "list_files", "git_status", "git_diff", "git_log", "gh_pr_list", "gh_ci_status"):
        return OperationType.READ
    elif name in ("write_file",):
        return OperationType.WRITE
    elif name in ("edit_file", "apply_patch"):
        return OperationType.EDIT
    elif name in ("delete_file",):
        return OperationType.DELETE
    elif name in ("git_commit",):
        return OperationType.GIT_COMMIT
    elif name in ("git_push",):
        return OperationType.GIT_PUSH
    elif name in ("execute_command", "shell_exec", "run_tests"):
        cmd = str(arguments.get("command", "") or arguments.get("test_command", ""))
        cmd_lower = cmd.lower()
        if any(pkg_cmd in cmd_lower for pkg_cmd in ("npm install", "pnpm add", "yarn add", "pip install", "cargo add", "go get")):
            return OperationType.PACKAGE_INSTALL
        return OperationType.SHELL
    return OperationType.SHELL
