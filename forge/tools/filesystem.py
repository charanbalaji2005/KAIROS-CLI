"""Filesystem tools: read with line numbering, write, edit, patch, and delete."""

import os
from pathlib import Path
from typing import Optional


def resolve_path(path: str, workspace: Optional[str] = None) -> Path:
    """Resolves a path relative to workspace or current working directory."""
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    base = Path(workspace) if workspace else Path.cwd()
    return (base / p).resolve()


async def read_file(
    path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    workspace: Optional[str] = None,
) -> str:
    """Reads a file with 1-indexed line numbers.

    Args:
        path: Path to the file.
        start_line: Starting line number (1-indexed). Defaults to 1.
        end_line: Ending line number (inclusive). If None, reads to the end.
        workspace: Workspace root path.
    """
    file_path = resolve_path(path, workspace)
    if not file_path.exists():
        return f"ERROR: File not found: {path}"
    if file_path.is_dir():
        return f"ERROR: Path is a directory, not a file: {path}"

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: Failed to read {path}: {str(e)}"

    lines = content.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return f"File {path} is empty."

    start = max(1, start_line)
    if start > total_lines:
        return f"ERROR: start_line ({start}) exceeds total line count ({total_lines}) of {path}."

    if end_line is not None:
        end = min(end_line, total_lines)
        selected_lines = lines[start - 1 : end]
    else:
        selected_lines = lines[start - 1 :]

    header = f"--- {path} (lines {start}-{start + len(selected_lines) - 1} of {total_lines}) ---\n"
    formatted = "\n".join(
        f"{i + start:>5} | {line}"
        for i, line in enumerate(selected_lines)
    )
    return header + formatted


async def write_file(
    path: str,
    content: str,
    workspace: Optional[str] = None,
) -> str:
    """Writes full content to a file, creating parent directories if needed.

    Args:
        path: Path to the target file.
        content: The text content to write.
        workspace: Workspace root path.
    """
    file_path = resolve_path(path, workspace)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        line_count = len(content.splitlines())
        return f"Successfully wrote {len(content)} bytes ({line_count} lines) to {path}"
    except Exception as e:
        return f"ERROR: Failed to write {path}: {str(e)}"


async def edit_file(
    path: str,
    old_text: str,
    new_text: str,
    workspace: Optional[str] = None,
) -> str:
    """Replaces an exact section of text in a file.

    Args:
        path: Path to the target file.
        old_text: The exact block of text to replace.
        new_text: The replacement text.
        workspace: Workspace root path.
    """
    file_path = resolve_path(path, workspace)
    if not file_path.exists():
        return f"ERROR: File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: Could not read {path}: {str(e)}"

    # Normalize line endings for reliable matching
    normalized_content = content.replace("\r\n", "\n")
    normalized_old = old_text.replace("\r\n", "\n")
    normalized_new = new_text.replace("\r\n", "\n")

    occurrences = normalized_content.count(normalized_old)
    if occurrences == 0:
        return f"ERROR: Target old_text not found in {path}. Make sure whitespace and formatting match exactly."
    if occurrences > 1:
        return f"ERROR: Target old_text appears {occurrences} times in {path}. Please provide more surrounding context to make it unique."

    updated_content = normalized_content.replace(normalized_old, normalized_new, 1)

    # Restore CRLF if original file used Windows endings
    if "\r\n" in content:
        updated_content = updated_content.replace("\n", "\r\n")

    try:
        file_path.write_text(updated_content, encoding="utf-8")
        return f"Successfully edited {path}"
    except Exception as e:
        return f"ERROR: Failed to save edits to {path}: {str(e)}"


async def apply_patch(
    path: str,
    patch_text: str,
    workspace: Optional[str] = None,
) -> str:
    """Applies a unified diff patch to a file.

    Args:
        path: Path to the target file.
        patch_text: Unified diff patch text.
        workspace: Workspace root path.
    """
    file_path = resolve_path(path, workspace)
    if not file_path.exists():
        return f"ERROR: File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: Could not read {path}: {str(e)}"

    lines = content.splitlines()
    patch_lines = patch_text.strip().splitlines()

    # Simple & robust hunk parser for diffs
    hunks = []
    current_hunk = None

    for line in patch_lines:
        if line.startswith("@@"):
            current_hunk = {"header": line, "lines": []}
            hunks.append(current_hunk)
        elif current_hunk is not None:
            if line.startswith(("+", "-", " ", "\\")):
                current_hunk["lines"].append(line)

    if not hunks:
        return "ERROR: No valid unified diff hunks (starting with @@) found in patch_text."

    new_lines = list(lines)
    offset = 0

    for hunk in hunks:
        hunk_lines = hunk["lines"]
        old_block = [l[1:] for l in hunk_lines if l.startswith((" ", "-"))]
        new_block = [l[1:] for l in hunk_lines if l.startswith((" ", "+"))]

        # Find match for old_block in new_lines
        matched_idx = None
        for i in range(len(new_lines) - len(old_block) + 1):
            if new_lines[i : i + len(old_block)] == old_block:
                matched_idx = i
                break

        if matched_idx is None:
            return f"ERROR: Patch hunk failed to match file context: {hunk['header']}"

        # Replace slice
        new_lines[matched_idx : matched_idx + len(old_block)] = new_block

    final_content = "\n".join(new_lines)
    if content.endswith("\n"):
        final_content += "\n"

    try:
        file_path.write_text(final_content, encoding="utf-8")
        return f"Successfully applied patch to {path} ({len(hunks)} hunk(s) applied)"
    except Exception as e:
        return f"ERROR: Failed to save patched content to {path}: {str(e)}"


async def delete_file(
    path: str,
    workspace: Optional[str] = None,
) -> str:
    """Deletes a file or directory.

    Args:
        path: Path to delete.
        workspace: Workspace root path.
    """
    file_path = resolve_path(path, workspace)
    if not file_path.exists():
        return f"ERROR: Path does not exist: {path}"

    try:
        if file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
            return f"Successfully removed directory: {path}"
        else:
            file_path.unlink()
            return f"Successfully removed file: {path}"
    except Exception as e:
        return f"ERROR: Failed to delete {path}: {str(e)}"
