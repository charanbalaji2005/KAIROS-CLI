"""Search tools: ripgrep search, glob file finding, and directory listing."""

import fnmatch
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from forge.tools.filesystem import resolve_path

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "archive",
}


async def search(
    pattern: str,
    path: str = ".",
    case_sensitive: bool = False,
    file_pattern: Optional[str] = None,
    max_results: int = 50,
    workspace: Optional[str] = None,
) -> str:
    """Searches for a text pattern or regex across workspace files.

    Args:
        pattern: The string or regular expression to search for.
        path: Starting directory or file path.
        case_sensitive: Whether search should be case sensitive.
        file_pattern: Optional glob to filter filenames (e.g. '*.py' or '*.ts').
        max_results: Max lines to return.
        workspace: Workspace root path.
    """
    target_path = resolve_path(path, workspace)
    if not target_path.exists():
        return f"ERROR: Path does not exist: {path}"

    # Try ripgrep if installed
    rg_bin = shutil.which("rg")
    if rg_bin:
        cmd = [rg_bin, "--line-number", "--no-heading", "--color=never"]
        if not case_sensitive:
            cmd.append("-i")
        if file_pattern:
            cmd.extend(["-g", file_pattern])
        cmd.extend(["-m", str(max_results), pattern, str(target_path)])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=15)
            output = res.stdout.strip()
            if output:
                lines = output.splitlines()[:max_results]
                return "\n".join(lines)
            elif res.returncode == 1:
                return f"No matches found for '{pattern}' in {path}."
        except Exception:
            pass  # Fall back to pure Python

    # Pure Python fallback
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error:
        regex = re.compile(re.escape(pattern), flags)

    matches: List[str] = []
    base_dir = target_path if target_path.is_dir() else target_path.parent

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for file in files:
            if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                continue

            full_file = Path(root) / file
            rel_file = full_file.relative_to(target_path if target_path.is_dir() else target_path.parent)

            try:
                content = full_file.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        matches.append(f"{rel_file}:{line_idx}: {line.strip()[:160]}")
                        if len(matches) >= max_results:
                            break
            except Exception:
                continue

            if len(matches) >= max_results:
                break
        if len(matches) >= max_results:
            break

    if not matches:
        return f"No matches found for '{pattern}' in {path}."
    return "\n".join(matches)


async def glob_files(
    pattern: str = "*",
    path: str = ".",
    max_results: int = 100,
    workspace: Optional[str] = None,
) -> str:
    """Finds files matching a glob pattern (e.g. '**/*.py', 'src/**/*.rs').

    Args:
        pattern: Glob pattern to match.
        path: Root directory to search from.
        max_results: Maximum files to return.
        workspace: Workspace root path.
    """
    target_path = resolve_path(path, workspace)
    if not target_path.exists():
        return f"ERROR: Path does not exist: {path}"

    results: List[str] = []

    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for file in files:
            full_path = Path(root) / file
            try:
                rel_path = full_path.relative_to(target_path)
            except ValueError:
                rel_path = full_path

            posix_rel = str(rel_path).replace("\\", "/")
            if fnmatch.fnmatch(posix_rel, pattern) or fnmatch.fnmatch(file, pattern):
                results.append(posix_rel)
                if len(results) >= max_results:
                    break
        if len(results) >= max_results:
            break

    if not results:
        return f"No files matching '{pattern}' found in {path}."
    return "\n".join(results)


async def list_files(
    path: str = ".",
    max_depth: Optional[int] = 3,
    workspace: Optional[str] = None,
) -> str:
    """Lists files and directories in a structured tree up to max_depth.

    Args:
        path: Path to start listing from.
        max_depth: Maximum directory depth to traverse (default: 3).
        workspace: Workspace root path.
    """
    target_path = resolve_path(path, workspace)
    if not target_path.exists():
        return f"ERROR: Path does not exist: {path}"

    if not target_path.is_dir():
        return f"{path} is a file."

    tree_lines: List[str] = []
    base_level = len(target_path.parts)

    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        current_level = len(Path(root).parts) - base_level

        if max_depth is not None and current_level >= max_depth:
            dirs.clear()
            continue

        indent = "  " * current_level
        folder_name = os.path.basename(root)
        if current_level > 0:
            tree_lines.append(f"{indent}📁 {folder_name}/")

        file_indent = "  " * (current_level + 1)
        for f in sorted(files):
            if not f.startswith("."):
                tree_lines.append(f"{file_indent}📄 {f}")

        if len(tree_lines) > 200:
            tree_lines.append("  ... (truncated)")
            break

    return "\n".join(tree_lines) if tree_lines else f"Directory {path} is empty."
