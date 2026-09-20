"""Git tool: status, diffs, branches, commits, log, and push."""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from forge.tools.filesystem import resolve_path


def _run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    """Executes a git command synchronously."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        errors="replace",
    )


async def git_status(workspace: Optional[str] = None) -> Dict[str, Any]:
    """Returns detailed Git repository status including branch, staged, modified, and untracked files.

    Args:
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    if not (target_dir / ".git").exists() and not shutil.which("git"):
        return {"error": "Not a git repository or git not found."}

    # Branch
    b_res = _run_git(["branch", "--show-current"], target_dir)
    branch = b_res.stdout.strip() or "HEAD (detached)"

    # Porcelain status
    s_res = _run_git(["status", "--porcelain"], target_dir)
    raw = s_res.stdout

    modified = []
    staged = []
    untracked = []

    for line in raw.splitlines():
        if len(line) < 3:
            continue
        code = line[:2]
        filepath = line[3:].strip()
        if code.startswith("??"):
            untracked.append(filepath)
        else:
            if code[0] != " ":
                staged.append(filepath)
            if code[1] != " ":
                modified.append(filepath)

    # Ahead / Behind
    ahead = 0
    behind = 0
    rev_res = _run_git(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], target_dir)
    if rev_res.returncode == 0:
        parts = rev_res.stdout.strip().split()
        if len(parts) == 2:
            ahead = int(parts[0]) if parts[0].isdigit() else 0
            behind = int(parts[1]) if parts[1].isdigit() else 0

    return {
        "branch": branch,
        "is_clean": len(raw.strip()) == 0,
        "modified": modified,
        "staged": staged,
        "untracked": untracked,
        "ahead": ahead,
        "behind": behind,
        "raw_status": raw.strip(),
    }


async def git_diff(
    file_path: Optional[str] = None,
    staged: bool = False,
    workspace: Optional[str] = None,
) -> str:
    """Returns the git diff for uncommitted changes or a specific file.

    Args:
        file_path: Optional relative path to diff a single file.
        staged: Whether to view staged changes (--staged).
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    args = ["diff"]
    if staged:
        args.append("--staged")
    if file_path:
        args.extend(["--", file_path])

    res = _run_git(args, target_dir)
    if res.returncode != 0:
        return f"ERROR running git diff: {res.stderr.strip()}"

    output = res.stdout.strip()
    return output if output else "No changes detected."


async def git_commit(
    message: str,
    add_all: bool = True,
    workspace: Optional[str] = None,
) -> str:
    """Stages files and creates a Git commit.

    Args:
        message: Commit message.
        add_all: Whether to run `git add -A` prior to commit.
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    if add_all:
        add_res = _run_git(["add", "-A"], target_dir)
        if add_res.returncode != 0:
            return f"ERROR during git add: {add_res.stderr.strip()}"

    commit_res = _run_git(["commit", "-m", message], target_dir)
    if commit_res.returncode != 0:
        err = commit_res.stderr.strip() or commit_res.stdout.strip()
        if "nothing to commit" in err:
            return "Nothing to commit, working tree clean."
        return f"ERROR during git commit: {err}"

    return commit_res.stdout.strip()


async def git_push(
    branch: Optional[str] = None,
    force: bool = False,
    workspace: Optional[str] = None,
) -> str:
    """Pushes local commits to the remote repository.

    Args:
        branch: Branch to push. If None, pushes current branch.
        force: Whether to use --force-with-lease.
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    if not branch:
        status = await git_status(workspace)
        branch = status.get("branch", "main")

    args = ["push", "origin", branch]
    if force:
        args.append("--force-with-lease")

    push_res = _run_git(args, target_dir)
    if push_res.returncode != 0:
        return f"ERROR during git push: {push_res.stderr.strip() or push_res.stdout.strip()}"

    return f"Successfully pushed {branch} to origin.\n{push_res.stdout.strip()}"


async def git_branch(
    create: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """Lists branches or creates and checks out a new branch.

    Args:
        create: Name of new branch to create and checkout.
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    if create:
        res = _run_git(["checkout", "-b", create], target_dir)
        if res.returncode != 0:
            return f"ERROR creating branch: {res.stderr.strip()}"
        return f"Created and switched to branch '{create}'"

    res = _run_git(["branch", "-a"], target_dir)
    return res.stdout.strip()


async def git_log(
    n: int = 10,
    workspace: Optional[str] = None,
) -> str:
    """Shows the recent commit log.

    Args:
        n: Number of commits to show.
        workspace: Workspace root path.
    """
    target_dir = resolve_path(".", workspace)
    res = _run_git(["log", f"-n{n}", "--oneline", "--decorate"], target_dir)
    if res.returncode != 0:
        return f"ERROR fetching git log: {res.stderr.strip()}"
    return res.stdout.strip()
