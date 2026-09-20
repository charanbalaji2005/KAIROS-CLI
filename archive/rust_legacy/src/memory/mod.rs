use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tokio::fs;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SessionMemory {
    pub workspace: String,
    pub files_indexed: Vec<String>,
    pub notes: Vec<String>,
}

impl SessionMemory {
    pub fn new(workspace: impl Into<String>) -> Self {
        Self {
            workspace: workspace.into(),
            files_indexed: Vec::new(),
            notes: Vec::new(),
        }
    }

    pub fn add_note(&mut self, note: impl Into<String>) {
        self.notes.push(note.into());
        if self.notes.len() > 100 {
            self.notes.remove(0);
        }
    }
}
