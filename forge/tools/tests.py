"""Test execution tool: auto-detects test runners, executes tests, and extracts failures."""

import re
from pathlib import Path
from typing import Dict, Any, Optional

from forge.tools.filesystem import resolve_path
from forge.tools.shell import execute_command


def detect_test_command(workspace_path: Path) -> str:
    """Detects the standard test command for the workspace."""
    if (workspace_path / "pytest.ini").exists() or (workspace_path / "pyproject.toml").exists() or any(workspace_path.glob("test_*.py")):
        return "pytest"
    if (workspace_path / "Cargo.toml").exists():
        return "cargo test"
    if (workspace_path / "package.json").exists():
        return "npm test"
    if (workspace_path / "go.mod").exists():
        return "go test ./..."
    if (workspace_path / "pom.xml").exists():
        return "mvn test"
    return "pytest"


async def run_tests(
    test_command: Optional[str] = None,
    path: Optional[str] = None,
    workspace: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs test suite and returns parsed results, failures, and output.

    Args:
        test_command: Explicit command (e.g. 'pytest tests/test_auth.py' or 'cargo test').
        path: Optional specific test file or directory path.
        workspace: Workspace root path.
    """
    ws = resolve_path(".", workspace)
    cmd = test_command

    if not cmd:
        base_cmd = detect_test_command(ws)
        cmd = f"{base_cmd} {path}" if path else base_cmd

    result = await execute_command(command=cmd, cwd=str(ws), timeout=180)
    output = result["output"]
    exit_code = result["exit_code"]

    # Extract failure snippets
    failures = []
    lines = output.splitlines()

    # Look for common test failure headers
    capture = False
    cur_fail = []
    for line in lines:
        if any(marker in line for marker in ("FAILURES", "FAILED", "failures:", "FAIL:", "--- FAIL:")):
            capture = True
        if capture:
            cur_fail.append(line)
            if len(cur_fail) > 40:
                cur_fail.append("... [failure snippet truncated]")
                break

    failure_summary = "\n".join(cur_fail) if cur_fail else ""

    return {
        "command": cmd,
        "success": exit_code == 0,
        "exit_code": exit_code,
        "failure_summary": failure_summary,
        "output": output,
    }
