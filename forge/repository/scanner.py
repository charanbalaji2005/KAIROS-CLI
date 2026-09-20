"""Repository scanner: gathers structural overview and file statistics."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from forge.repository.detector import RepositoryDetector, ProjectInfo
from forge.tools.filesystem import resolve_path
from forge.tools.git import git_status
from forge.tools.search import IGNORED_DIRS


@dataclass
class WorkspaceSummary:
    path: str
    project_info: ProjectInfo
    total_files: int
    top_directories: List[str]
    readme_excerpt: Optional[str]
    git_branch: Optional[str]


class RepositoryScanner:
    """Scans and prepares a high-level summary of the workspace."""

    @staticmethod
    async def scan(workspace: Optional[str] = None) -> WorkspaceSummary:
        target_dir = resolve_path(".", workspace)
        info = RepositoryDetector.detect(str(target_dir))

        total_files = 0
        top_dirs: List[str] = []

        if target_dir.exists():
            for entry in target_dir.iterdir():
                if entry.is_dir() and entry.name not in IGNORED_DIRS and not entry.name.startswith("."):
                    top_dirs.append(entry.name)

            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                total_files += len(files)

        # Readme
        readme_excerpt = None
        for r_name in ("README.md", "readme.md", "README", "README.txt"):
            r_path = target_dir / r_name
            if r_path.exists():
                try:
                    text = r_path.read_text(encoding="utf-8", errors="replace")
                    lines = text.splitlines()[:25]
                    readme_excerpt = "\n".join(lines)
                    break
                except Exception:
                    pass

        # Git status
        g_stat = await git_status(str(target_dir))
        git_branch = g_stat.get("branch") if "error" not in g_stat else None

        return WorkspaceSummary(
            path=str(target_dir),
            project_info=info,
            total_files=total_files,
            top_directories=sorted(top_dirs),
            readme_excerpt=readme_excerpt,
            git_branch=git_branch,
        )
