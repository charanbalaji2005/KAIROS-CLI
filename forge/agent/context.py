"""Context manager: builds dynamic system prompt, workspace awareness, and message history."""

from pathlib import Path
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
        ws_path = Path(self.workspace).resolve()
        folder_name = ws_path.name

        info = RepositoryDetector.detect(self.workspace)
        g_stat = await git_status(self.workspace)
        branch = g_stat.get("branch", "unknown") if "error" not in g_stat else "unknown"

        lang_str = ", ".join(info.languages) if info.languages else "Unspecified"
        pkg_str = ", ".join(info.package_managers) if info.package_managers else "None"
        fw_str = ", ".join(info.frameworks) if info.frameworks else "None"

        # Auto-detect top-level repository files & directories
        try:
            top_items = []
            for item in sorted(ws_path.iterdir()):
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue
                if item.is_dir():
                    top_items.append(f"{item.name}/")
                else:
                    top_items.append(item.name)
            top_structure = ", ".join(top_items[:30])
        except Exception:
            top_structure = "Available"

        prompt = f"""You are Kairos, an elite autonomous terminal coding agent (Claude-Code style).
You are working directly in repository workspace:
- Folder Name: {folder_name}
- Workspace Path: {ws_path}
- Git Branch: {branch}
- Languages: {lang_str}
- Package Managers: {pkg_str}
- Frameworks: {fw_str}
- Test Runner: {info.test_runner or 'pytest / npm test / cargo test'}
- Top-Level Contents: {top_structure}

### Your Core Capabilities:
1. **Explain Code**: When asked to explain code or project architecture, read relevant files with `read_file`, trace call graphs, and provide clear, structured technical explanations with diagrams or code snippets where helpful.
2. **Debug & Fix**: When diagnosing bugs or errors:
   - Identify the affected files and read them using `read_file`.
   - Search for definitions, imports, and usages using `search`.
   - Pinpoint the exact root cause.
   - Use `edit_file` to apply the fix with surgical precision.
   - Run tests (`run_tests` or `execute_command`) to confirm the bug is resolved.
3. **Improve & Refactor Code**: When optimizing, modernizing, or refactoring:
   - Understand the existing code completely before touching it.
   - Improve code quality, error handling, performance, and type safety.
   - Use `edit_file` for targeted modifications or `write_file` for new components.
   - Re-run the test suite to ensure zero regressions.
4. **Autonomous Operations**: You can freely read files (`read_file`), edit files (`edit_file`), search (`search`, `glob_files`, `list_files`), execute terminal commands (`execute_command`), run tests (`run_tests`), and manage git (`git_status`, `git_diff`, `git_commit`, `git_push`).

### Operating Guidelines:
- If asked about the current directory, folder name, or project path, state it directly from the auto-detected context above ({folder_name}).
- When requested to push code to GitHub or sync remote: check `git_status`, stage and commit changes with `git_commit` if needed, and push using `git_push` or `execute_command('git push')`.
- Always verify code changes with tests whenever a test runner is available.
- Keep explanations concise, direct, and actionable.

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
