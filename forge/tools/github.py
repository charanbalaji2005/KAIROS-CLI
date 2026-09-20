"""GitHub CLI (gh) integration for pull requests and CI status."""

import shutil
import subprocess
from typing import Dict, Any, Optional


def is_gh_available() -> bool:
    return shutil.which("gh") is not None


def _run_gh(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        errors="replace",
    )


async def gh_status() -> Dict[str, Any]:
    """Checks GitHub CLI authentication and repository connection."""
    if not is_gh_available():
        return {"connected": False, "error": "gh CLI not installed"}

    auth_res = _run_gh(["auth", "status"])
    is_auth = auth_res.returncode == 0

    user = None
    repo = None

    if is_auth:
        u_res = _run_gh(["api", "user", "--jq", ".login"])
        if u_res.returncode == 0:
            user = u_res.stdout.strip()

        r_res = _run_gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
        if r_res.returncode == 0:
            repo = r_res.stdout.strip()

    return {
        "connected": is_auth,
        "username": user,
        "repo": repo,
    }


async def gh_pr_create(
    title: str,
    body: str = "",
    draft: bool = False,
) -> str:
    """Creates a pull request on GitHub via gh CLI.

    Args:
        title: PR title.
        body: PR description.
        draft: Create PR as draft if True.
    """
    if not is_gh_available():
        return "ERROR: gh CLI not installed. Install gh and run 'gh auth login'."

    args = ["pr", "create", "--title", title, "--body", body]
    if draft:
        args.append("--draft")

    res = _run_gh(args)
    if res.returncode != 0:
        return f"ERROR creating PR: {res.stderr.strip() or res.stdout.strip()}"
    return res.stdout.strip()


async def gh_pr_list(limit: int = 5) -> str:
    """Lists open pull requests in the repository.

    Args:
        limit: Max PRs to show.
    """
    if not is_gh_available():
        return "ERROR: gh CLI not installed."

    res = _run_gh(["pr", "list", "--limit", str(limit)])
    if res.returncode != 0:
        return f"ERROR listing PRs: {res.stderr.strip()}"
    out = res.stdout.strip()
    return out if out else "No open pull requests found."


async def gh_ci_status() -> str:
    """Checks recent GitHub Actions CI workflow runs."""
    if not is_gh_available():
        return "ERROR: gh CLI not installed."

    res = _run_gh(["run", "list", "--limit", "3"])
    if res.returncode != 0:
        return f"ERROR fetching CI runs: {res.stderr.strip()}"
    out = res.stdout.strip()
    return out if out else "No workflow runs found."
