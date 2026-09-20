"""Forge CLI implementation with subcommands."""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from forge.config.loader import load_config, save_config, set_config_value, get_config_path
from forge.terminal.renderer import (
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_SUCCESS,
    COLOR_WARNING,
    render_error,
    render_success,
)
from forge.terminal.ui import TerminalUI
from forge.tools.git import git_status
from forge.tools.github import gh_status

app = typer.Typer(
    help="Forge - Autonomous Terminal Coding Agent (Claude-Code Architecture in Python)",
    invoke_without_command=True,
)
console = Console(legacy_windows=False)


@app.callback()
def main(
    ctx: typer.Context,
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model override (e.g. qwen-coder, claude, gpt-4o)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Provider override (ollama, anthropic, openai, gemini)"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Run without confirmation prompts"),
    resume: Optional[str] = typer.Option(None, "--resume", "-r", help="Resume a previous session by ID"),
):
    """Start interactive Forge coding agent session if no subcommand is passed."""
    if ctx.invoked_subcommand is None:
        cfg = load_config()
        if model:
            cfg.model = model
        if provider:
            cfg.provider = provider
        if auto:
            cfg.auto_mode = True

        target_workspace = workspace or str(Path.cwd())
        ui = TerminalUI(config=cfg, workspace=target_workspace, session_id=resume)
        asyncio.run(ui.start())


@app.command("doctor")
def run_doctor():
    """Check environment dependencies (Git, gh, Ollama, API keys)."""
    console.print(f"\n[bold {COLOR_ORANGE}]╔══════════════════════════════════════════════════════════╗[/]")
    console.print(f"[bold {COLOR_ORANGE}]║              FORGE DOCTOR v0.2.0 (Python)                ║[/]")
    console.print(f"[bold {COLOR_ORANGE}]╚══════════════════════════════════════════════════════════╝[/]\n")

    table = Table(show_header=True, header_style=f"bold {COLOR_ORANGE}")
    table.add_column("Component", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    # 1. Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python", f"[{COLOR_SUCCESS}]✓[/]", f"Python {py_ver}")

    # 2. Git
    git_bin = shutil.which("git")
    if git_bin:
        table.add_row("Git", f"[{COLOR_SUCCESS}]✓[/]", git_bin)
    else:
        table.add_row("Git", "[red]✗[/]", "git not found in PATH")

    # 3. GitHub CLI
    gh = asyncio.run(gh_status())
    if gh.get("connected"):
        table.add_row("GitHub CLI", f"[{COLOR_SUCCESS}]✓[/]", f"Authenticated as {gh.get('username')}")
    elif shutil.which("gh"):
        table.add_row("GitHub CLI", f"[{COLOR_WARNING}]◆[/]", "Installed but not logged in (run 'gh auth login')")
    else:
        table.add_row("GitHub CLI", f"[{COLOR_MUTED}]○[/]", "Not installed")

    # 4. Ollama
    cfg = load_config()
    import httpx
    try:
        r = httpx.get(f"{cfg.ollama_url.rstrip('/')}/api/tags", timeout=2.0)
        if r.status_code == 200:
            models = [m.get("name") for m in r.json().get("models", [])]
            model_summary = f"{len(models)} model(s) available" if models else "No models installed"
            table.add_row("Ollama", f"[{COLOR_SUCCESS}]✓[/]", f"Connected ({model_summary})")
        else:
            table.add_row("Ollama", "[red]✗[/]", f"HTTP {r.status_code}")
    except Exception:
        table.add_row("Ollama", f"[{COLOR_MUTED}]○[/]", f"Not reachable at {cfg.ollama_url}")

    # 5. Groq & Cloud API Keys
    if cfg.groq_api_key or os.getenv("GROQ_API_KEY"):
        try:
            gr_key = cfg.groq_api_key or os.getenv("GROQ_API_KEY")
            gr_resp = httpx.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {gr_key}"}, timeout=3.0)
            if gr_resp.status_code == 200:
                gr_models = len(gr_resp.json().get("data", []))
                table.add_row("Groq", f"[{COLOR_SUCCESS}]✓[/]", f"Connected ({gr_models} models ready: Qwen 27B, GPT-OSS 120B, etc.)")
            else:
                table.add_row("Groq", "[red]✗[/]", f"Auth failed (HTTP {gr_resp.status_code})")
        except Exception:
            table.add_row("Groq", f"[{COLOR_WARNING}]◆[/]", "Key configured, network check failed")
    else:
        table.add_row("Groq", f"[{COLOR_MUTED}]○[/]", "Not configured (set with 'forge config groq_api_key <key>')")

    api_status = []
    if cfg.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"):
        api_status.append("Anthropic")
    if cfg.openai_api_key or os.getenv("OPENAI_API_KEY"):
        api_status.append("OpenAI")
    if cfg.gemini_api_key or os.getenv("GEMINI_API_KEY"):
        api_status.append("Gemini")

    if api_status:
        table.add_row("Other Cloud APIs", f"[{COLOR_SUCCESS}]✓[/]", f"Configured: {', '.join(api_status)}")

    console.print(table)
    console.print(f"\n[{COLOR_MUTED}]Run [bold {COLOR_ORANGE}]python forge.py[/] to launch Forge.[/]\n")


@app.command("status")
def run_status():
    """Display active workspace, git branch, and configuration."""
    cfg = load_config()
    g_stat = asyncio.run(git_status())
    gh = asyncio.run(gh_status())

    console.print(f"\n[bold {COLOR_ORANGE}]FORGE STATUS[/]\n")
    console.print(f"  Provider:  [{COLOR_ORANGE}]{cfg.provider}[/]")
    console.print(f"  Model:     [{COLOR_ORANGE}]{cfg.model}[/]")
    console.print(f"  Workspace: [white]{Path.cwd()}[/]")
    console.print(f"  Branch:    [cyan]{g_stat.get('branch', 'unknown')}[/]")
    console.print(f"  Auto Mode: [{'green' if cfg.auto_mode else 'dim'}]{cfg.auto_mode}[/]")
    if gh.get("connected"):
        console.print(f"  GitHub:    [{COLOR_SUCCESS}]● connected[/] as {gh.get('username')}")
    else:
        console.print(f"  GitHub:    [{COLOR_MUTED}]○ disconnected[/]")
    console.print()


@app.command("model")
def run_model(
    action: str = typer.Argument("list", help="list, set, or status"),
    name: Optional[str] = typer.Argument(None, help="Model name (when setting)"),
):
    """Manage active and available models across Groq, Ollama, and Cloud."""
    if action == "list":
        console.print(f"\n[bold {COLOR_ORANGE}]FORGE MODELS[/]\n")
        console.print(f"[{COLOR_ORANGE}]Groq LPUs (Ultra-Fast):[/]")
        console.print("  ● qwen/qwen3.8-27b             Qwen 27B [green](active default)[/]")
        console.print("  ○ openai/gpt-oss-120b          OpenAI GPT-OSS 120B")
        console.print("  ○ openai/gpt-oss-20b           OpenAI GPT-OSS 20B")
        console.print("  ○ groq/compound                Groq Compound Engine")
        console.print("  ○ groq/compound-mini           Groq Compound Mini")
        console.print("  ○ llama-3.3-70b-versatile      Llama 3.3 70B")
        console.print("  ○ llama-3.1-8b-instant         Llama 3.1 8B Instant")
        console.print()
        console.print(f"[{COLOR_MUTED}]Local Models (Ollama):[/]")
        console.print("  ○ qwen-coder                   Qwen2.5-Coder 3B")
        console.print("  ○ deepseek-coder               DeepSeek-Coder 1.3B")
        console.print("  ○ phi3-mini                    Phi-3 Mini 3.8B")
        console.print()
        console.print(f"[{COLOR_MUTED}]Cloud Providers:[/]")
        console.print("  ○ claude-sonnet                Anthropic Claude 3.5 Sonnet")
        console.print("  ○ gpt-4o                       OpenAI GPT-4o")
        console.print("  ○ gemini-flash                 Google Gemini 2.5 Flash\n")
        console.print("Set Groq model: [bold white]forge model set qwen/qwen3.8-27b[/]")
        console.print("Switch provider: [bold white]forge config provider groq[/]\n")
    elif action == "set" and name:
        cfg = load_config()
        # Auto-switch provider if user selects a Groq model
        if any(g in name.lower() for g in ("qwen", "gpt-oss", "compound", "groq")):
            cfg.provider = "groq"
        elif any(c in name.lower() for c in ("claude", "sonnet", "haiku")):
            cfg.provider = "anthropic"
        elif any(o in name.lower() for o in ("gpt-4", "gpt-3")):
            cfg.provider = "openai"
        elif "gemini" in name.lower():
            cfg.provider = "gemini"

        cfg.model = name
        save_config(cfg)
        render_success(f"Model set to [{COLOR_ORANGE}]{cfg.model}[/] on [{COLOR_ORANGE}]{cfg.provider}[/]")
    else:
        cfg = load_config()
        console.print(f"Active: [{COLOR_ORANGE}]{cfg.provider}:{cfg.model}[/]")


@app.command("config")
def run_config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
):
    """Inspect or update ~/.forge/config.json."""
    if key and value:
        set_config_value(key, value)
        render_success(f"Set {key} = {value}")
    elif key:
        cfg = load_config()
        val = getattr(cfg, key, None)
        console.print(f"{key}: {val}")
    else:
        cfg = load_config()
        console.print(f"\n[bold {COLOR_ORANGE}]FORGE CONFIG[/]")
        console.print(f"Path: {get_config_path()}\n")
        console.print(cfg.model_dump_json(indent=2))
        console.print()


@app.command("version")
def run_version():
    """Print Forge version."""
    console.print(f"\n[bold {COLOR_ORANGE}]Forge Agent[/] v0.2.0 (Claude-Code Python Architecture)\n")


def cli_main():
    app()
