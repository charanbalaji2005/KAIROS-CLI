use anyhow::Result;
use std::path::{Path, PathBuf};

pub struct ToolRegistry {
    workspace: String,
}

impl ToolRegistry {
    pub fn new(workspace: String) -> Self {
        Self { workspace }
    }

    pub async fn execute(&self, tool_name: &str, input: &str) -> Result<String> {
        match tool_name {
            "filesystem.read" => self.fs_read(input).await,
            "filesystem.write" => self.fs_write(input).await,
            "filesystem.list" => self.fs_list(input).await,
            "filesystem.delete" => self.fs_delete(input).await,
            "shell.exec" => self.shell_exec(input).await,
            "git.status" => self.git_status().await,
            "git.diff" => self.git_diff().await,
            "git.commit" => self.git_commit(input).await,
            "git.push" => self.git_push(input).await,
            "git.branch" => self.git_branch(input).await,
            "github.pr.create" => self.gh_pr_create(input).await,
            "github.pr.list" => self.gh_pr_list().await,
            "github.ci.status" => self.gh_ci_status().await,
            other => Err(anyhow::anyhow!("Unknown tool: {}", other)),
        }
    }

    fn resolve_path(&self, path: &str) -> PathBuf {
        let p = Path::new(path);
        if p.is_absolute() {
            p.to_path_buf()
        } else {
            Path::new(&self.workspace).join(path)
        }
    }

    async fn fs_read(&self, path: &str) -> Result<String> {
        let full = self.resolve_path(path.trim());
        let content = tokio::fs::read_to_string(&full).await
            .map_err(|e| anyhow::anyhow!("Cannot read {}: {}", path, e))?;
        let lines: Vec<&str> = content.lines().collect();
        Ok(format!("Read {} lines from {}", lines.len(), path))
    }

    async fn fs_write(&self, input: &str) -> Result<String> {
        // input format: "path|||content"
        let parts: Vec<&str> = input.splitn(2, "|||").collect();
        if parts.len() != 2 {
            return Err(anyhow::anyhow!("fs_write requires 'path|||content' format"));
        }
        let path = parts[0].trim();
        let content = parts[1];
        let full = self.resolve_path(path);

        if let Some(parent) = full.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }

        tokio::fs::write(&full, content).await?;
        Ok(format!("Written {} bytes to {}", content.len(), path))
    }

    async fn fs_list(&self, dir: &str) -> Result<String> {
        let full = if dir.is_empty() {
            PathBuf::from(&self.workspace)
        } else {
            self.resolve_path(dir.trim())
        };

        let mut entries = tokio::fs::read_dir(&full).await?;
        let mut names = Vec::new();

        while let Some(entry) = entries.next_entry().await? {
            let name = entry.file_name().to_string_lossy().to_string();
            if !name.starts_with('.') {
                names.push(name);
            }
        }
        names.sort();

        Ok(names.join("\n"))
    }

    async fn fs_delete(&self, path: &str) -> Result<String> {
        let full = self.resolve_path(path.trim());
        if full.is_dir() {
            tokio::fs::remove_dir_all(&full).await?;
        } else {
            tokio::fs::remove_file(&full).await?;
        }
        Ok(format!("Deleted: {}", path))
    }

    async fn shell_exec(&self, cmd: &str) -> Result<String> {
        let output = tokio::process::Command::new("sh")
            .arg("-c")
            .arg(cmd)
            .current_dir(&self.workspace)
            .output()
            .await?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if output.status.success() {
            Ok(if stdout.is_empty() { "Command completed".to_string() } else { stdout })
        } else {
            Err(anyhow::anyhow!("{}", if stderr.is_empty() { stdout } else { stderr }))
        }
    }

    async fn git_status(&self) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["status", "--short"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    }

    async fn git_diff(&self) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["diff", "--stat"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    }

    async fn git_commit(&self, message: &str) -> Result<String> {
        // Stage all changes
        tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["add", "-A"])
            .output()
            .await?;

        let out = tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["commit", "-m", message.trim()])
            .output()
            .await?;

        if out.status.success() {
            Ok(format!("Committed: {}", message.trim()))
        } else {
            let err = String::from_utf8_lossy(&out.stderr).to_string();
            if err.contains("nothing to commit") {
                Ok("Nothing to commit".to_string())
            } else {
                Err(anyhow::anyhow!("{}", err))
            }
        }
    }

    async fn git_push(&self, branch: &str) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["push", "origin", branch.trim()])
            .output()
            .await?;

        if out.status.success() {
            Ok(format!("Pushed branch {} to origin", branch.trim()))
        } else {
            Err(anyhow::anyhow!(
                "{}",
                String::from_utf8_lossy(&out.stderr)
            ))
        }
    }

    async fn git_branch(&self, name: &str) -> Result<String> {
        let out = tokio::process::Command::new("git")
            .current_dir(&self.workspace)
            .args(["checkout", "-b", name.trim()])
            .output()
            .await?;

        if out.status.success() {
            Ok(format!("Created branch: {}", name.trim()))
        } else {
            Err(anyhow::anyhow!(
                "{}",
                String::from_utf8_lossy(&out.stderr)
            ))
        }
    }

    async fn gh_pr_create(&self, input: &str) -> Result<String> {
        let parts: Vec<&str> = input.splitn(2, "|||").collect();
        let title = parts.get(0).copied().unwrap_or("Forge PR").trim();
        let body = parts.get(1).copied().unwrap_or("Created by Forge Agent").trim();

        let out = tokio::process::Command::new("gh")
            .current_dir(&self.workspace)
            .args(["pr", "create", "--title", title, "--body", body])
            .output()
            .await?;

        if out.status.success() {
            Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
        } else {
            Err(anyhow::anyhow!("{}", String::from_utf8_lossy(&out.stderr)))
        }
    }

    async fn gh_pr_list(&self) -> Result<String> {
        let out = tokio::process::Command::new("gh")
            .current_dir(&self.workspace)
            .args(["pr", "list"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).to_string())
    }

    async fn gh_ci_status(&self) -> Result<String> {
        let out = tokio::process::Command::new("gh")
            .current_dir(&self.workspace)
            .args(["run", "list", "--limit", "3"])
            .output()
            .await?;
        Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
    }
}
