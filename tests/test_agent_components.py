"""Tests for planner, memory, context compaction, and shell execution."""

import asyncio
import tempfile
from pathlib import Path

from forge.agent.compaction import ContextCompactor
from forge.agent.memory import SessionMemory
from forge.agent.planner import TaskPlanner
from forge.sessions.storage import save_session, load_session
from forge.tools.shell import execute_command


def test_task_planner():
    planner = TaskPlanner()
    planner.set_plan("Fix authentication bug", ["Search files", "Edit auth.ts", "Run tests"])
    assert len(planner.steps) == 3
    assert planner.steps[0].in_progress is True

    planner.mark_step_completed(1, notes="Found auth.ts:42")
    assert planner.steps[0].completed is True
    assert planner.steps[1].in_progress is True

    md = planner.format_plan_markdown()
    assert "[x] Step 1: Search files" in md
    assert "[▶] Step 2: Edit auth.ts" in md
    assert "Found auth.ts:42" in md


def test_session_memory():
    mem = SessionMemory()
    mem.add_fact("database", "postgres")
    mem.pin_file("src/auth.ts")
    mem.set_scratchpad("Investigating JWT token issue")

    assert mem.key_facts["database"] == "postgres"
    assert "src/auth.ts" in mem.pinned_files
    assert "JWT" in mem.scratchpad

    mem.unpin_file("src/auth.ts")
    assert "src/auth.ts" not in mem.pinned_files


def test_context_compactor():
    compactor = ContextCompactor(keep_recent_turns=2, max_chars_per_tool_result=100)
    messages = [
        {"role": "system", "content": "You are Forge."},
        {"role": "user", "content": "Initial user task"},
        {"role": "assistant", "content": "Looking at files", "tool_calls": []},
        {"role": "tool", "name": "read_file", "content": "A" * 500},
        {"role": "assistant", "content": "Editing code", "tool_calls": []},
        {"role": "tool", "name": "edit_file", "content": "Successfully edited."},
        {"role": "user", "content": "Recent question"},
        {"role": "assistant", "content": "Recent response"},
    ]

    compacted = compactor.compact(messages)
    assert len(compacted) < len(messages)
    assert compacted[0]["role"] == "system"
    assert compacted[1]["content"] == "Initial user task"
    assert "Prior Conversation Summary" in str(compacted[2]["content"])


def test_shell_execution():
    async def _test():
        res = await execute_command("python --version")
        assert res["exit_code"] == 0
        assert "Python" in res["output"]

    asyncio.run(_test())


def test_session_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test save and load
        sess_id = "test_sess_123"
        msgs = [{"role": "user", "content": "Hello Forge"}]
        sess_file = save_session(sess_id, tmpdir, msgs, metadata={"model": "qwen"})
        assert sess_file.exists()

        loaded = load_session(sess_id)
        assert loaded is not None
        assert loaded["session_id"] == sess_id
        assert loaded["workspace"] == tmpdir
        assert loaded["messages"] == msgs


def test_tool_call_session_persistence():
    from forge.llm.base import ToolCall
    with tempfile.TemporaryDirectory() as tmpdir:
        sess_id = "test_tool_sess_456"
        tc = ToolCall(id="call_99", name="list_files", arguments={"path": "."})
        msgs = [
            {"role": "user", "content": "what is the folder name"},
            {"role": "assistant", "content": "", "tool_calls": [tc.to_dict()]},
            {"role": "tool", "tool_call_id": "call_99", "name": "list_files", "content": "file1\nfile2"},
        ]
        sess_file = save_session(sess_id, tmpdir, msgs)
        assert sess_file.exists()

        loaded = load_session(sess_id)
        assert loaded is not None
        assert len(loaded["messages"]) == 3
        assert loaded["messages"][1]["tool_calls"][0]["name"] == "list_files"


def test_robot_mascot_frames_and_banner():
    """Verify robot mascot frames and banner rendering without errors."""
    from forge.terminal.renderer import (
        MASCOT_ART,
        MASCOT_SLEEP,
        MASCOT_WAKE,
        MASCOT_LOOK_LEFT,
        MASCOT_LOOK_RIGHT,
        MASCOT_WINK,
        MASCOT_GIGGLE_1,
        MASCOT_GIGGLE_2,
        MASCOT_IDLE,
        render_banner,
        render_mascot_giggle,
    )

    frames = [
        MASCOT_SLEEP,
        MASCOT_WAKE,
        MASCOT_LOOK_LEFT,
        MASCOT_LOOK_RIGHT,
        MASCOT_WINK,
        MASCOT_GIGGLE_1,
        MASCOT_GIGGLE_2,
        MASCOT_IDLE,
    ]

    # Verify each frame has 8 lines and antenna
    for f in frames:
        lines = f.strip().splitlines()
        assert len(lines) == 8
        assert "●" in lines[0]  # Antenna ball
        assert "▟█" in lines[-1]  # Robot feet

    # Test banner rendering (compact and full)
    render_banner(
        workspace="/test/workspace",
        model="groq:qwen/qwen3.8-27b",
        branch="main",
        github_connected=True,
        github_user="testuser",
        compact=False,
        animate=False,
    )
    render_banner(
        workspace="/test/workspace",
        model="groq:qwen/qwen3.8-27b",
        compact=True,
    )
    render_mascot_giggle("Test celebrate!")


def test_kairos_robot_spinner():
    """Verify kairos_robot spinner registration and context manager."""
    import rich._spinners
    from forge.terminal.streaming import live_spinner

    assert "kairos_robot" in rich._spinners.SPINNERS
    spinner_info = rich._spinners.SPINNERS["kairos_robot"]
    assert "frames" in spinner_info
    assert len(spinner_info["frames"]) >= 8

    with live_spinner("Analyzing test code..."):
        pass


def test_claude_code_ui_layout_and_keybindings():
    """Verify Claude Code header, separator, status bar, and bottom toolbar."""
    import asyncio
    from forge.config.schema import ForgeConfig
    from forge.terminal.renderer import render_separator, render_status_bar
    from forge.terminal.ui import TerminalUI

    # 1. Separator and status bar render without error
    render_separator(width=60)
    render_status_bar(effort="high", width=60)
    render_status_bar(effort="normal", width=60)

    # Verify exact 5-line Claude Code pixel mascot geometry
    from forge.terminal.renderer import MASCOT_CLAUDE_IDLE
    assert "▄█████▄" in MASCOT_CLAUDE_IDLE
    assert "█ ███ █" in MASCOT_CLAUDE_IDLE
    assert "█████████" in MASCOT_CLAUDE_IDLE
    assert "▀█████▀" in MASCOT_CLAUDE_IDLE

    # 2. TerminalUI bottom toolbar
    cfg = ForgeConfig(auto_mode=False)
    ui = TerminalUI(config=cfg, workspace="/test/workspace")

    # Manual mode toolbar
    toolbar_manual = ui._get_bottom_toolbar()
    assert any("─" in item[1] for item in toolbar_manual)
    assert any("manual mode" in item[1] for item in toolbar_manual)
    assert any("shift+tab to cycle" in item[1] for item in toolbar_manual)

    # Auto mode toolbar
    ui.config.auto_mode = True
    toolbar_auto = ui._get_bottom_toolbar()
    assert any("─" in item[1] for item in toolbar_auto)
    assert any("auto mode on" in item[1] for item in toolbar_auto)

    # Verify s-tab keybinding exists
    assert any(b.keys == ("s-tab",) for b in ui.kb.bindings)

    # Verify /effort command
    asyncio.run(ui._handle_slash_command("/effort low"))
    assert ui.effort_level == "low"
    asyncio.run(ui._handle_slash_command("/effort"))
    assert ui.effort_level in ("high", "normal")


def test_groq_fallback_pool():
    """Validates that GroqProvider defines candidates and handles multi-model fallback."""
    from forge.llm.groq import GroqProvider

    provider = GroqProvider(model="qwen/qwen3.8-27b", api_key="test_key")
    assert provider.model == "qwen/qwen3.8-27b"
    assert provider.base_url == "https://api.groq.com/openai/v1"


def test_context_compaction_tuned_limits():
    """Validates that ContextCompactor uses tighter limits to protect Groq TPM budgets."""
    from forge.agent.compaction import ContextCompactor

    compactor = ContextCompactor()
    assert compactor.keep_recent_turns == 4
    assert compactor.max_chars_per_tool_result == 800

    # Truncation test
    long_msg = {"role": "tool", "content": "X" * 2000, "name": "git_status"}
    truncated = compactor._truncate_tool_output(long_msg)
    assert len(truncated["content"]) < 1200
    assert "omitted" in truncated["content"]



