use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum AgentState {
    Idle,
    Thinking,
    Planning,
    Reading,
    Executing,
    Testing,
    WaitingApproval,
    Completed,
    Failed(String),
}

impl AgentState {
    pub fn symbol(&self) -> &str {
        match self {
            AgentState::Idle => "●",
            AgentState::Thinking => "◉",
            AgentState::Planning => "◉",
            AgentState::Reading => "◉",
            AgentState::Executing => "▶",
            AgentState::Testing => "◉",
            AgentState::WaitingApproval => "◆",
            AgentState::Completed => "✓",
            AgentState::Failed(_) => "✗",
        }
    }

    pub fn label(&self) -> String {
        match self {
            AgentState::Idle => "Ready".to_string(),
            AgentState::Thinking => "Thinking...".to_string(),
            AgentState::Planning => "Planning...".to_string(),
            AgentState::Reading => "Reading repository...".to_string(),
            AgentState::Executing => "Executing...".to_string(),
            AgentState::Testing => "Running tests...".to_string(),
            AgentState::WaitingApproval => "Waiting for approval".to_string(),
            AgentState::Completed => "Completed".to_string(),
            AgentState::Failed(msg) => format!("Failed: {}", msg),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    pub name: String,
    pub input: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub tool_name: String,
    pub success: bool,
    pub output: String,
    pub duration_ms: u64,
}

#[derive(Debug, Clone)]
pub enum AgentEvent {
    StateChanged(AgentState),
    TextOutput(String),
    ToolStarted(ToolCall),
    ToolCompleted(ToolResult),
    ApprovalRequired { command: String, description: String },
    Error(String),
    Done,
}

/// A message in the conversation history
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationMessage {
    pub role: MessageRole,
    pub content: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MessageRole {
    User,
    Agent,
    Tool,
    System,
}

impl ConversationMessage {
    pub fn user(content: impl Into<String>) -> Self {
        Self {
            role: MessageRole::User,
            content: content.into(),
            timestamp: chrono::Utc::now(),
        }
    }

    pub fn agent(content: impl Into<String>) -> Self {
        Self {
            role: MessageRole::Agent,
            content: content.into(),
            timestamp: chrono::Utc::now(),
        }
    }

    pub fn tool(content: impl Into<String>) -> Self {
        Self {
            role: MessageRole::Tool,
            content: content.into(),
            timestamp: chrono::Utc::now(),
        }
    }
}
