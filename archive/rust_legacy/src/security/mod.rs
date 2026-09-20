/// Determines which operations require user approval
pub struct PermissionSystem {
    auto_mode: bool,
    always_allow: Vec<String>,
}

impl PermissionSystem {
    pub fn new(auto_mode: bool) -> Self {
        Self {
            auto_mode,
            always_allow: Vec::new(),
        }
    }

    /// Returns true if the operation requires human approval
    pub fn requires_approval(&self, tool_name: &str, input: &str) -> bool {
        if self.auto_mode {
            return false; // Auto mode skips approvals
        }

        // Always require approval for these operations
        matches!(tool_name,
            "git.push" |
            "github.pr.create" |
            "filesystem.delete"
        )
    }

    pub fn always_allow(&mut self, tool_name: String) {
        self.always_allow.push(tool_name);
    }
}

/// Dangerous commands that need extra scrutiny
pub const DANGEROUS_PATTERNS: &[&str] = &[
    "rm -rf",
    "sudo",
    "chmod 777",
    "dd if=",
    "> /dev/",
    "mkfs",
];

pub fn is_dangerous_command(cmd: &str) -> bool {
    let lower = cmd.to_lowercase();
    DANGEROUS_PATTERNS.iter().any(|p| lower.contains(p))
}
