use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitHubStatus {
    pub connected: bool,
    pub username: Option<String>,
    pub repo: Option<String>,
    pub branch: Option<String>,
    pub ci_status: Option<String>,
}

impl Default for GitHubStatus {
    fn default() -> Self {
        Self {
            connected: false,
            username: None,
            repo: None,
            branch: None,
            ci_status: None,
        }
    }
}

pub struct GitHubClient;

impl GitHubClient {
    pub async fn detect() -> GitHubStatus {
        let mut status = GitHubStatus::default();

        // Check gh auth
        let auth_ok = tokio::process::Command::new("gh")
            .args(["auth", "status"])
            .output()
            .await
            .map(|o| o.status.success())
            .unwrap_or(false);

        if !auth_ok {
            return status;
        }

        status.connected = true;

        // Get username
        if let Ok(out) = tokio::process::Command::new("gh")
            .args(["api", "user", "--jq", ".login"])
            .output()
            .await
        {
            let username = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !username.is_empty() {
                status.username = Some(username);
            }
        }

        // Get current repo
        if let Ok(out) = tokio::process::Command::new("gh")
            .args(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
            .output()
            .await
        {
            let repo = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !repo.is_empty() && !repo.contains("error") {
                status.repo = Some(repo);
            }
        }

        // Get current branch
        if let Ok(out) = tokio::process::Command::new("git")
            .args(["branch", "--show-current"])
            .output()
            .await
        {
            let branch = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !branch.is_empty() {
                status.branch = Some(branch);
            }
        }

        status
    }

    /// Push the current branch to origin
    pub async fn push(branch: &str, force: bool) -> Result<String> {
        let mut args = vec!["push", "origin", branch];
        if force {
            args.push("--force-with-lease");
        }
        let out = tokio::process::Command::new("git")
            .args(&args)
            .output()
            .await?;

        if out.status.success() {
            Ok(format!("Pushed branch {} to origin", branch))
        } else {
            Err(anyhow::anyhow!(
                "Push failed: {}",
                String::from_utf8_lossy(&out.stderr)
            ))
        }
    }

    /// Create a pull request
    pub async fn create_pr(title: &str, body: &str) -> Result<String> {
        let out = tokio::process::Command::new("gh")
            .args(["pr", "create", "--title", title, "--body", body])
            .output()
            .await?;

        if out.status.success() {
            Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
        } else {
            Err(anyhow::anyhow!(
                "PR creation failed: {}",
                String::from_utf8_lossy(&out.stderr)
            ))
        }
    }

    /// List pull requests
    pub async fn list_prs() -> Result<String> {
        let out = tokio::process::Command::new("gh")
            .args(["pr", "list"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    }

    /// Get CI status
    pub async fn ci_status() -> Result<String> {
        let out = tokio::process::Command::new("gh")
            .args(["run", "list", "--limit", "1"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }

    /// Create and push a commit
    pub async fn commit_and_push(message: &str, branch: &str) -> Result<String> {
        // Stage all
        tokio::process::Command::new("git")
            .args(["add", "-A"])
            .output()
            .await?;

        // Commit
        let commit_out = tokio::process::Command::new("git")
            .args(["commit", "-m", message])
            .output()
            .await?;

        if !commit_out.status.success() {
            let err = String::from_utf8_lossy(&commit_out.stderr);
            if err.contains("nothing to commit") {
                return Ok("Nothing to commit".to_string());
            }
            return Err(anyhow::anyhow!("Commit failed: {}", err));
        }

        // Push
        Self::push(branch, false).await
    }

    /// Get diff stats
    pub async fn diff_stat() -> Result<String> {
        let out = tokio::process::Command::new("git")
            .args(["diff", "--stat"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }

    /// Get recent commits
    pub async fn log(n: u32) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .args(["log", &format!("--oneline -n {}", n)])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }

    /// Create a new branch
    pub async fn create_branch(name: &str) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .args(["checkout", "-b", name])
            .output()
            .await?;
        if out.status.success() {
            Ok(format!("Created and switched to branch: {}", name))
        } else {
            Err(anyhow::anyhow!(
                "Branch creation failed: {}",
                String::from_utf8_lossy(&out.stderr)
            ))
        }
    }

    /// Get current git status summary
    pub async fn git_status() -> Result<GitDiffStat> {
        let out = tokio::process::Command::new("git")
            .args(["status", "--porcelain"])
            .output()
            .await?;

        let lines = String::from_utf8_lossy(&out.stdout);
        let mut modified = 0u32;
        let mut added = 0u32;
        let mut deleted = 0u32;

        for line in lines.lines() {
            if line.starts_with("M") || line.starts_with(" M") {
                modified += 1;
            } else if line.starts_with("A") || line.starts_with("??") {
                added += 1;
            } else if line.starts_with("D") || line.starts_with(" D") {
                deleted += 1;
            }
        }

        // Get ahead/behind
        let sync_out = tokio::process::Command::new("git")
            .args(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
            .output()
            .await;

        let (ahead, behind) = if let Ok(out) = sync_out {
            let s = String::from_utf8_lossy(&out.stdout);
            let parts: Vec<&str> = s.trim().split_whitespace().collect();
            if parts.len() == 2 {
                (
                    parts[0].parse::<u32>().unwrap_or(0),
                    parts[1].parse::<u32>().unwrap_or(0),
                )
            } else {
                (0, 0)
            }
        } else {
            (0, 0)
        };

        Ok(GitDiffStat { modified, added, deleted, ahead, behind })
    }
}

#[derive(Debug, Clone, Default)]
pub struct GitDiffStat {
    pub modified: u32,
    pub added: u32,
    pub deleted: u32,
    pub ahead: u32,
    pub behind: u32,
}
