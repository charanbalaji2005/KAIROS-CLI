"""MCP (Model Context Protocol) client connector for external tool servers."""

import asyncio
import json
from typing import Dict, List, Any, Optional


class McpServerConnection:
    """Manages a stdio-based connection to an external MCP server."""

    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args
        self.env = env
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0

    async def connect(self) -> None:
        """Launches the MCP subprocess."""
        cmd = [self.command] + self.args
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Sends tools/list request to MCP server."""
        if not self.process or not self.process.stdin:
            return []

        self._request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/list",
            "params": {},
        }
        try:
            line = json.dumps(req) + "\n"
            self.process.stdin.write(line.encode("utf-8"))
            await self.process.stdin.drain()

            if self.process.stdout:
                res_line = await self.process.stdout.readline()
                data = json.loads(res_line.decode("utf-8"))
                return data.get("result", {}).get("tools", [])
        except Exception:
            pass
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Sends tools/call request to MCP server."""
        if not self.process or not self.process.stdin:
            return "ERROR: MCP server not running."

        self._request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }
        try:
            line = json.dumps(req) + "\n"
            self.process.stdin.write(line.encode("utf-8"))
            await self.process.stdin.drain()

            if self.process.stdout:
                res_line = await self.process.stdout.readline()
                data = json.loads(res_line.decode("utf-8"))
                return data.get("result", {}).get("content", str(data))
        except Exception as e:
            return f"ERROR executing MCP tool {name}: {str(e)}"
        return "No response from MCP server."

    async def close(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            self.process = None
