"""Interactive terminal UI using Prompt Toolkit and Rich."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.prompt import Confirm, Prompt

from forge.agent.runtime import AgentRuntime
from forge.agent.state import AgentEvent
from forge.config.loader import get_forge_dir, save_config, load_config
from forge.config.schema import ForgeConfig
from forge.llm import get_provider
from forge.sessions.manager import SessionManager
from forge.sessions.storage import list_sessions
from forge.terminal.renderer import (
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_ORANGE_DARK,
    COLOR_SUCCESS,
    COLOR_WARNING,
    render_banner,
    render_diff,
    render_error,
    render_success,
    render_tool_result,
    render_tool_start,
)
from forge.terminal.streaming import live_spinner
from forge.tools.git import git_diff, git_status
from forge.tools.github import gh_status

console = Console()

SLASH_COMMANDS = [
    "/help",
    "/clear",
    "/git",
    "/github",
    "/diff",
    "/model",
    "/doctor",
    "/compact",
    "/permissions",
    "/sessions",
    "/auto",
    "/exit",
    "/quit",
]


async def interactive_approval_callback(tool_name: str, arguments: dict, warning: Optional[str] = None) -> bool:
    """Prompts the user interactively before dangerous or modifying actions."""
    console.print()
    if warning:
        console.print(f"[{COLOR_WARNING}]⚠ {warning}[/]")

    cmd_desc = arguments.get("command") or arguments.get("path") or arguments.get("message") or ""
    console.print(f"[{COLOR_ORANGE}]Forge wants to run:[/] [bold white]{tool_name}[/] [dim]{cmd_desc}[/dim]")

    choice = Prompt.ask(
        "Allow execution?",
        choices=["y", "n", "a"],
        default="n",
    )

    if choice == "y":
        return True
    elif choice == "a":
        return True
    return False


class TerminalUI:
    """Interactive command shell for the Forge AI Engineer."""

    def __init__(self, config: ForgeConfig, workspace: Optional[str] = None, session_id: Optional[str] = None):
        self.config = config
        self.workspace = workspace or str(Path.cwd())
        self.session_manager = SessionManager(workspace=self.workspace, session_id=session_id)

        # Setup prompt toolkit history & styling
        history_path = get_forge_dir() / "history"
        self.prompt_history = FileHistory(str(history_path))
        self.completer = WordCompleter(SLASH_COMMANDS, ignore_case=True)
        self.pt_style = Style.from_dict({
            "prompt": "#F97316 bold",
        })

        # Initialize LLM provider & AgentRuntime
        self.llm = get_provider(self.config)
        self.runtime = AgentRuntime(
            llm=self.llm,
            workspace=self.workspace,
            auto_mode=self.config.auto_mode,
            max_iterations=self.config.max_iterations,
            event_callback=self._handle_event,
        )
        self.runtime.permissions.approval_callback = interactive_approval_callback

    async def _handle_event(self, event: AgentEvent) -> None:
        """Handles agent lifecycle events for terminal output."""
        if event.type == "tool_start":
            data = event.data
            render_tool_start(data["name"], data["arguments"])
        elif event.type == "tool_end":
            res = event.data
            render_tool_result(res.tool_name, res.output, res.success, res.duration_ms)

    async def start(self) -> None:
        """Starts the interactive session loop."""
        # Check git & GitHub status for banner
        g_stat = await git_status(self.workspace)
        branch = g_stat.get("branch") if "error" not in g_stat else None
        gh = await gh_status()

        render_banner(
            workspace=self.workspace,
            model=f"{self.config.provider}:{self.config.model}",
            branch=branch,
            github_connected=gh.get("connected", False),
            github_user=gh.get("username"),
            compact=self.config.compact_mode,
        )

        session = PromptSession(
            history=self.prompt_history,
            completer=self.completer,
            style=self.pt_style,
        )

        while True:
            try:
                prompt_text = [
                    ("class:prompt", "forge > "),
                ]
                user_input = await asyncio.to_thread(session.prompt, prompt_text)
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    handled = await self._handle_slash_command(user_input)
                    if handled == "exit":
                        break
                    continue

                # Run Agent task
                with live_spinner("Forge is working..."):
                    response = await self.runtime.run(user_input)

                # Persist session
                self.session_manager.save(self.runtime.messages)

                # Render final markdown response
                console.print()
                console.print(f"[{COLOR_ORANGE}]Forge:[/] {response}")
                console.print()

            except (KeyboardInterrupt, EOFError):
                console.print(f"\n[{COLOR_MUTED}]Session saved. Exiting Forge.[/]")
                break
            except Exception as e:
                render_error(str(e))

    async def _handle_slash_command(self, cmd: str) -> Optional[str]:
        """Processes built-in in-session commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command in ("/exit", "/quit"):
            return "exit"

        elif command == "/help":
            console.print(f"\n[bold {COLOR_ORANGE}]Available Commands:[/]")
            console.print("  /help         Show this command reference")
            console.print("  /clear        Clear active conversation history")
            console.print("  /git          Show git status summary")
            console.print("  /diff         Show uncommitted git changes")
            console.print("  /github       Check GitHub CLI status")
            console.print("  /model        View or change current LLM model")
            console.print("  /doctor       Check local environment")
            console.print("  /compact      Toggle compact header view")
            console.print("  /auto         Toggle autonomous confirmation mode")
            console.print("  /sessions     List previous sessions")
            console.print("  /exit         Exit Forge\n")

        elif command == "/clear":
            self.runtime.messages.clear()
            self.runtime.memory.clear()
            render_success("Conversation history cleared.")

        elif command == "/git":
            stat = await git_status(self.workspace)
            console.print(f"[{COLOR_ORANGE}]Git Branch:[/] {stat.get('branch', 'unknown')}")
            console.print(f"Modified: {len(stat.get('modified', []))}, Staged: {len(stat.get('staged', []))}, Untracked: {len(stat.get('untracked', []))}")

        elif command == "/diff":
            diff_text = await git_diff(workspace=self.workspace)
            render_diff(diff_text)

        elif command == "/github":
            gh = await gh_status()
            if gh.get("connected"):
                render_success(f"Connected as {gh.get('username')} (repo: {gh.get('repo')})")
            else:
                render_error(f"GitHub disconnected ({gh.get('error', 'not authenticated')})")

        elif command == "/compact":
            self.config.compact_mode = not self.config.compact_mode
            save_config(self.config)
            render_success(f"Compact mode: {self.config.compact_mode}")

        elif command == "/auto":
            self.config.auto_mode = not self.config.auto_mode
            self.runtime.auto_mode = self.config.auto_mode
            self.runtime.permissions.set_auto_mode(self.config.auto_mode)
            save_config(self.config)
            render_success(f"Auto mode set to: {self.config.auto_mode}")

        elif command == "/model":
            if arg:
                self.config.model = arg
                save_config(self.config)
                self.llm = get_provider(self.config)
                self.runtime.llm = self.llm
                render_success(f"Switched model to: {arg}")
            else:
                console.print(f"Active model: [{COLOR_ORANGE}]{self.config.provider}:{self.config.model}[/]")
                console.print("Change with: /model <model-name>")

        elif command == "/sessions":
            sessions = list_sessions()
            console.print(f"\n[bold {COLOR_ORANGE}]Recent Sessions:[/]")
            for s in sessions[:5]:
                console.print(f"  • [bold white]{s['session_id']}[/] ({s['message_count']} messages, {s['workspace']})")
            console.print("Resume with: python forge.py --resume <session_id>\n")

        return None
