"""Terminal renderer with Forge's signature orange-on-black aesthetic and ASCII mascot."""

import os
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# Force UTF-8 on Windows consoles to prevent cp1252 charmap encoding errors
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)

# Forge Brand Colors
COLOR_ORANGE = "#F97316"
COLOR_ORANGE_DARK = "#EA580C"
COLOR_ORANGE_LIGHT = "#FB923C"
COLOR_ORANGE_FAINT = "#FDBA74"
COLOR_MUTED = "#A3A3A3"
COLOR_SUCCESS = "#22C55E"
COLOR_WARNING = "#F59E0B"
COLOR_ERROR = "#EF4444"
COLOR_INFO = "#60A5FA"

MASCOT_ART = r"""
     ╭●╮
   ╭─┴─┴─╮
 ╭┤ ╭───╮ ├╮
 ││ [>_ ] ││
 ╰┤ ╰───╯ ├╯
   ╰┬─┬─┬╯
""".strip("\n")


def render_banner(
    workspace: str,
    model: str,
    branch: Optional[str] = None,
    github_connected: bool = False,
    github_user: Optional[str] = None,
    compact: bool = False,
) -> None:
    """Renders the Forge startup header banner."""
    if compact:
        gh_status = f"[green]● {github_user or 'connected'}[/green]" if github_connected else "[dim]○ offline[/dim]"
        console.print(
            f"[{COLOR_ORANGE}]⟦>_⟧ FORGE[/] [bold white]v0.2.0[/] │ "
            f"Model: [{COLOR_ORANGE}]{model}[/] │ "
            f"Branch: [cyan]{branch or 'none'}[/] │ "
            f"GitHub: {gh_status}"
        )
        console.print(f"[{COLOR_ORANGE_DARK}]{'─' * 64}[/]")
        return

    # Full header
    gh_icon = f"[bold {COLOR_SUCCESS}]● connected[/] as {github_user}" if github_connected else f"[{COLOR_MUTED}]○ disconnected[/]"

    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="center")
    grid.add_column(justify="left")

    mascot_text = Text(MASCOT_ART, style=COLOR_ORANGE)
    info_lines = (
        f"[bold {COLOR_ORANGE}]FORGE AGENT v0.2.0[/]\n"
        f"[dim]Autonomous Terminal Engineer (Python Core)[/]\n\n"
        f"[{COLOR_MUTED}]Model:[/]     [{COLOR_ORANGE}]{model}[/]\n"
        f"[{COLOR_MUTED}]Workspace:[/] [white]{workspace}[/]\n"
        f"[{COLOR_MUTED}]Branch:[/]    [cyan]{branch or 'detached'}[/]\n"
        f"[{COLOR_MUTED}]GitHub:[/]    {gh_icon}"
    )

    grid.add_row(mascot_text, info_lines)

    panel = Panel(
        grid,
        border_style=COLOR_ORANGE_DARK,
        title=f"[bold {COLOR_ORANGE}]⟦>_⟧ FORGE[/]",
        title_align="left",
    )
    console.print(panel)


def render_tool_start(tool_name: str, arguments: dict) -> None:
    """Renders start of a tool invocation."""
    args_summary = ", ".join(f"{k}={repr(v)[:40]}" for k, v in arguments.items())
    console.print(f"  [{COLOR_ORANGE}]●[/] [{COLOR_ORANGE_LIGHT}]{tool_name}[/] [dim]({args_summary})[/dim]")


def render_tool_result(tool_name: str, output: str, success: bool = True, duration_ms: int = 0) -> None:
    """Renders tool completion result."""
    icon = f"[{COLOR_SUCCESS}]✓[/]" if success else f"[{COLOR_ERROR}]✗[/]"
    first_line = output.strip().splitlines()[0] if output.strip() else "done"
    if len(first_line) > 100:
        first_line = first_line[:97] + "..."
    console.print(f"  {icon} [dim]{tool_name} ({duration_ms}ms):[/] [white]{first_line}[/]")


def render_diff(diff_text: str) -> None:
    """Renders formatted syntax-highlighted diff."""
    if not diff_text or diff_text == "No changes detected.":
        console.print(f"[{COLOR_MUTED}]No changes detected.[/]")
        return
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
    console.print(syntax)


def render_error(message: str) -> None:
    console.print(f"[{COLOR_ERROR}]ERROR:[/] {message}")


def render_success(message: str) -> None:
    console.print(f"[{COLOR_SUCCESS}]✓[/] {message}")


def render_warning(message: str) -> None:
    console.print(f"[{COLOR_WARNING}]WARNING:[/] {message}")
