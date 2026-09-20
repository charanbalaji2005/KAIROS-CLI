use anyhow::Result;
use std::path::Path;
use tokio::fs;

/// Repository scanner — lazily indexes workspace files
pub struct RepositoryScanner {
    workspace: String,
}

impl RepositoryScanner {
    pub fn new(workspace: impl Into<String>) -> Self {
        Self { workspace: workspace.into() }
    }

    /// Scan top-level structure of the workspace
    pub async fn scan_summary(&self) -> Result<String> {
        let mut entries = fs::read_dir(&self.workspace).await?;
        let mut names = Vec::new();

        while let Some(entry) = entries.next_entry().await? {
            let name = entry.file_name().to_string_lossy().to_string();
            if !name.starts_with('.') {
                names.push(name);
            }
        }
        names.sort();

        let mut result = format!("Workspace: {}\n", self.workspace);
        for name in &names {
            result.push_str(&format!("  {}\n", name));
        }
        result.push_str(&format!("\n{} top-level entries", names.len()));

        Ok(result)
    }
}
