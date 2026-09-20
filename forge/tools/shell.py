"""Shell tool: async subprocess execution for builds, tests, and CLI commands."""

import asyncio
import os
import sys
from typing import Dict, Optional, Any

from forge.tools.filesystem import resolve_path


async def execute_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 120,
    workspace: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes a shell command in the workspace directory.

    Args:
        command: The shell command line to run.
        cwd: Optional working directory for the command.
        timeout: Maximum seconds to allow the command to run.
        workspace: Workspace root path.
    """
    target_dir = resolve_path(cwd or ".", workspace)
    if not target_dir.exists():
        return {
            "exit_code": -1,
            "output": f"ERROR: Working directory does not exist: {target_dir}",
            "timed_out": False,
        }

    # Use shell appropriate for platform
    is_win = sys.platform == "win32"
    shell_cmd = command

    try:
        process = await asyncio.create_subprocess_shell(
            shell_cmd,
            cwd=str(target_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        try:
            stdout_data, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout),
            )
            raw_output = stdout_data.decode(errors="replace")
            exit_code = process.returncode if process.returncode is not None else 0
            return {
                "exit_code": exit_code,
                "output": raw_output.strip(),
                "timed_out": False,
            }
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            return {
                "exit_code": -1,
                "output": f"ERROR: Command timed out after {timeout} seconds: {command}",
                "timed_out": True,
            }

    except Exception as e:
        return {
            "exit_code": -1,
            "output": f"ERROR: Failed to launch command: {str(e)}",
            "timed_out": False,
        }
