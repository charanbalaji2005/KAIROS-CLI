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

# Robot Mascot Animation Frames (matching assets/mascot.png)
MASCOT_SLEEP = """
       ╭●╮      
     ╭─┴─┴─╮    
 ╭───┴─────┴───╮
╭┤  ─   ..  ─ ├╮
││    z Z z    ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
    ▟█ █ █ █▙   
""".strip("\n")

MASCOT_WAKE = """
       ╭●╮      
     ╭─┴─┴─╮    
 ╭───┴─────┴───╮
╭┤  •   ..  • ├╮
││    •   •    ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
    ▟█ █ █ █▙   
""".strip("\n")

MASCOT_LOOK_LEFT = """
     ╭●╯        
    ╭─┴───╮     
 ╭───┴─────┴───╮
╭┤ ●    ..     ├╮
││  ◖       ◖  ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
   ▟█ █ █ █▙    
""".strip("\n")

MASCOT_LOOK_RIGHT = """
        ╰●╮     
     ╭───┴─╮    
 ╭───┴─────┴───╮
╭┤     ..    ● ├╮
││  ◗       ◗  ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
     ▟█ █ █ █▙  
""".strip("\n")

MASCOT_WINK = """
       ╭●╮      
     ╭─┴─┴─╮    
 ╭───┴─────┴───╮
╭┤  ^   >_  - ├╮
││    ^   -    ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
    ▟█ █ █ █▙   
""".strip("\n")

MASCOT_GIGGLE_1 = """
     * ╭●╯ *    
    ╭─┴───╮     
 ╭───┴─────┴───╮
╭┤  >   ﹏  < ├╮
││  ( giggle ) ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
   ▟█ █ █ █▙    
""".strip("\n")

MASCOT_GIGGLE_2 = """
    *  ╰●╮  *   
     ╭───┴─╮    
 ╭───┴─────┴───╮
╭┤  ^   ▽   ^ ├╮
││   hehehe~   ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
     ▟█ █ █ █▙  
""".strip("\n")

MASCOT_IDLE = """
       ╭●╮      
     ╭─┴─┴─╮    
 ╭───┴─────┴───╮
╭┤  ▮   >_  ▮ ├╮
││             ││
╰┤  ╭───────╮  ├╯
 ╰──┴───────┴──╯
    ▟█ █ █ █▙   
""".strip("\n")

MASCOT_ART = MASCOT_IDLE


# Exact Claude Code pixel mascot (matching reference screenshot)
MASCOT_CLAUDE_IDLE = """
 ▄█████▄ 
 █ ███ █ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_CLAUDE_BLINK = """
 ▄█████▄ 
 █▀███▀█ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_CLAUDE_LOOK_LEFT = """
 ▄█████▄ 
 █•███ █ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_CLAUDE_LOOK_RIGHT = """
 ▄█████▄ 
 █ ███•█ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_CLAUDE_WINK = """
 ▄█████▄ 
 █^███-█ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_CLAUDE_GIGGLE_1 = """
 ▄█████▄ 
 █>███<█ 
█████████
 ▀█████▀ 
  ▀   ▀  
""".strip("\n")

MASCOT_CLAUDE_GIGGLE_2 = """
 ▄█████▄ 
 █^███^█ 
█████████
 ▀█████▀ 
  █   █  
""".strip("\n")

MASCOT_COMPACT_IDLE = MASCOT_CLAUDE_IDLE
MASCOT_COMPACT_SLEEP = MASCOT_CLAUDE_BLINK
MASCOT_COMPACT_WAKE = MASCOT_CLAUDE_IDLE
MASCOT_COMPACT_LOOK_LEFT = MASCOT_CLAUDE_LOOK_LEFT
MASCOT_COMPACT_LOOK_RIGHT = MASCOT_CLAUDE_LOOK_RIGHT
MASCOT_COMPACT_WINK = MASCOT_CLAUDE_WINK
MASCOT_COMPACT_GIGGLE_1 = MASCOT_CLAUDE_GIGGLE_1
MASCOT_COMPACT_GIGGLE_2 = MASCOT_CLAUDE_GIGGLE_2

COLOR_CLAUDE = "#D97757"  # Claude Code signature terracotta orange
COLOR_SEPARATOR = "#333333"


def _build_claude_header(
    mascot_art: str,
    workspace: str,
    model: str,
    branch: Optional[str] = None,
    github_connected: bool = False,
    github_user: Optional[str] = None,
    mood_badge: Optional[str] = None,
) -> Table:
    """Builds a borderless Claude Code-style header grid with mascot and metadata."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="left")

    gh_suffix = f" · {github_user}" if (github_connected and github_user) else ""
    clean_model = model.replace("groq:", "").replace("openai:", "")
    if "context" not in clean_model:
        clean_model = f"{clean_model} (128k context)"

    mascot_text = Text(mascot_art, style=COLOR_CLAUDE)
    info_lines = (
        f"[bold white]Kairos Code[/] [dim]v0.2.0[/]\n"
        f"[dim]{clean_model}{gh_suffix}[/]\n"
        f"[dim]{workspace}[/]"
    )

    grid.add_row(mascot_text, info_lines)
    return grid


def render_banner(
    workspace: str,
    model: str,
    branch: Optional[str] = None,
    github_connected: bool = False,
    github_user: Optional[str] = None,
    compact: bool = False,
    animate: bool = True,
) -> None:
    """Renders the borderless Claude Code-style startup header."""
    if compact:
        gh_status = f"[green]● {github_user or 'connected'}[/green]" if github_connected else "[dim]○ offline[/dim]"
        console.print(
            f"[{COLOR_CLAUDE}]Kairos Code[/] [dim]v0.2.0[/] · [{COLOR_CLAUDE}]{model}[/] · {gh_status}"
        )
        return

    is_interactive = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    should_animate = animate and is_interactive and not os.environ.get("PYTEST_CURRENT_TEST")

    if should_animate:
        import time
        from rich.live import Live

        animation_sequence = [
            (MASCOT_COMPACT_SLEEP, "⟦ zZz ⟧", 0.10),
            (MASCOT_COMPACT_WAKE, "⟦ •_• ⟧", 0.08),
            (MASCOT_COMPACT_LOOK_LEFT, "⟦ •_  ⟧", 0.08),
            (MASCOT_COMPACT_LOOK_RIGHT, "⟦  _• ⟧", 0.08),
            (MASCOT_COMPACT_WINK, "⟦ ^_- ⟧", 0.08),
            (MASCOT_COMPACT_GIGGLE_1, "⟦ >_< ⟧", 0.10),
            (MASCOT_COMPACT_GIGGLE_2, "⟦ ^o^ ⟧", 0.10),
        ]

        try:
            with Live(
                _build_claude_header(MASCOT_COMPACT_SLEEP, workspace, model, branch, github_connected, github_user, "⟦ zZz ⟧"),
                console=console,
                refresh_per_second=20,
                transient=True,
            ) as live:
                for frame, mood, dur in animation_sequence:
                    live.update(_build_claude_header(frame, workspace, model, branch, github_connected, github_user, mood))
                    time.sleep(dur)
        except Exception:
            pass

    console.print()
    header = _build_claude_header(MASCOT_COMPACT_IDLE, workspace, model, branch, github_connected, github_user)
    console.print(header)
    console.print()


def render_separator(width: Optional[int] = None) -> None:
    """Renders Claude Code's horizontal rule divider across terminal width."""
    term_width = width or (console.width or 80)
    console.print(f"[{COLOR_SEPARATOR}]{'─' * term_width}[/]")


def render_status_bar(effort: str = "high", width: Optional[int] = None) -> None:
    """Renders Claude Code's right-aligned '● high · /effort' status line."""
    term_width = width or (console.width or 80)
    text = f"● {effort}  ·  /effort"
    pad = max(0, term_width - len(text) - 2)
    console.print(f"[dim]{' ' * pad}{text}[/]")


def render_mascot_giggle(message: str = "Hehehe! Task complete!") -> None:
    """Plays a quick giggling animation for celebratory moments."""
    is_interactive = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    if is_interactive and not os.environ.get("PYTEST_CURRENT_TEST"):
        import time
        from rich.live import Live
        frames = [
            (MASCOT_GIGGLE_1, 0.10),
            (MASCOT_GIGGLE_2, 0.12),
            (MASCOT_GIGGLE_1, 0.10),
            (MASCOT_IDLE, 0.05),
        ]
        try:
            with Live(Text(MASCOT_GIGGLE_1, style=COLOR_ORANGE), console=console, transient=True) as live:
                for f, dur in frames:
                    live.update(Text(f, style=COLOR_ORANGE))
                    time.sleep(dur)
        except Exception:
            pass
    console.print(f"[{COLOR_ORANGE}]⟦>_<⟧[/] [bold {COLOR_ORANGE_LIGHT}]{message}[/]")


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
