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
