"""Context manager: builds dynamic system prompt, workspace awareness, and message history."""

from typing import Any, Dict, List, Optional

from forge.agent.compaction import ContextCompactor
from forge.agent.memory import SessionMemory
from forge.agent.planner import TaskPlanner
from forge.repository.detector import RepositoryDetector
from forge.tools.filesystem import resolve_path
from forge.tools.git import git_status


class ContextManager:
    """Constructs prompt context with repository intelligence, git state, and history compaction."""

    def __init__(
        self,
        workspace: Optional[str] = None,
        auto_mode: bool = False,
        memory: Optional[SessionMemory] = None,
        planner: Optional[TaskPlanner] = None,
    ):
        self.workspace = str(resolve_path(".", workspace))
        self.auto_mode = auto_mode
        self.memory = memory or SessionMemory()
        self.planner = planner or TaskPlanner()
        self.compactor = ContextCompactor()

    async def build_system_prompt(self) -> str:
        """Assembles the full system instructions for the LLM."""
        info = RepositoryDetector.detect(self.workspace)
        g_stat = await git_status(self.workspace)
        branch = g_stat.get("branch", "unknown") if "error" not in g_stat else "unknown"

        lang_str = ", ".join(info.languages) if info.languages else "Unspecified"
        pkg_str = ", ".join(info.package_managers) if info.package_managers else "None"
        fw_str = ", ".join(info.frameworks) if info.frameworks else "None"

        prompt = f"""You are Forge, an elite autonomous terminal coding agent (Claude-Code style).
You are working directly in repository workspace: {self.workspace}
Git branch: {branch}
Languages: {lang_str}
Package Managers: {pkg_str}
Frameworks: {fw_str}
Test Runner: {info.test_runner or 'pytest / npm test / cargo test'}

### Core Operating Principles:
1. **Understand First**: Always read relevant files using `read_file` or search the repository before modifying code.
2. **Precision Editing**: Prefer `edit_file` with exact `old_text` and `new_text` for targeted changes, or `apply_patch` for diffs. Use `write_file` when creating new files.
3. **Verify and Test**: After making changes, ALWAYS execute tests or run checks (`run_tests` or `execute_command`) to confirm that your modifications work and didn't break existing functionality.
4. **Autonomous Test/Fix Loop**: If a test or build fails, read the error message carefully, locate the bug, edit the code, and re-run tests until they pass.
5. **Clean Version Control**: Use `git_status` and `git_diff` to review your modifications before making git commits.
6. **Be Direct & Concise**: Explain what you are doing in concise, technical language. Do not output unnecessary filler.

Auto mode: {self.auto_mode}
When auto mode is off, destructive operations (deleting files, git push, creating PRs) will ask the user for confirmation.
"""
        # Append planner step if active
        plan_md = self.planner.format_plan_markdown()
        if plan_md:
            prompt += f"\n{plan_md}\n"

        # Append scratchpad if populated
        if self.memory.scratchpad:
            prompt += f"\n### Agent Scratchpad:\n{self.memory.scratchpad}\n"

        return prompt

    async def build_messages(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combines system prompt with compacted conversation history."""
        system_prompt = await self.build_system_prompt()
        all_messages = [{"role": "system", "content": system_prompt}] + conversation
        return self.compactor.compact(all_messages)
