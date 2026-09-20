use anyhow::Result;
use std::sync::Arc;
use tokio::sync::mpsc;

use crate::agent::state::{AgentEvent, AgentState, ConversationMessage, ToolCall, ToolResult};
use crate::llm::{LlmMessage, LlmProvider};
use crate::tools::ToolRegistry;
use crate::security::PermissionSystem;

pub struct AgentRuntime {
    provider: Arc<Box<dyn LlmProvider>>,
    tools: ToolRegistry,
    permissions: PermissionSystem,
    conversation: Vec<ConversationMessage>,
    workspace: String,
    auto_mode: bool,
}

impl AgentRuntime {
    pub fn new(
        provider: Arc<Box<dyn LlmProvider>>,
        workspace: String,
        auto_mode: bool,
    ) -> Self {
        Self {
            provider,
            tools: ToolRegistry::new(workspace.clone()),
            permissions: PermissionSystem::new(auto_mode),
            conversation: Vec::new(),
            workspace,
            auto_mode,
        }
    }

    pub async fn process(
        &mut self,
        user_input: String,
        event_tx: mpsc::UnboundedSender<AgentEvent>,
    ) -> Result<()> {
        // Add user message to history
        self.conversation.push(ConversationMessage::user(&user_input));

        // State: Thinking
        let _ = event_tx.send(AgentEvent::StateChanged(AgentState::Thinking));

        // Build system prompt
        let system = self.build_system_prompt().await;

        // Build LLM messages
        let mut messages = vec![LlmMessage::system(&system)];
        for msg in &self.conversation {
            match msg.role {
                crate::agent::state::MessageRole::User => {
                    messages.push(LlmMessage::user(&msg.content));
                }
                crate::agent::state::MessageRole::Agent => {
                    messages.push(LlmMessage::assistant(&msg.content));
                }
                _ => {}
            }
        }

        // Get LLM response
        let response = self.provider.complete(&messages).await?;

        // Parse response for tool calls
        let (text_parts, tool_calls) = parse_agent_response(&response);

        // Emit text output
        if !text_parts.is_empty() {
            let _ = event_tx.send(AgentEvent::TextOutput(text_parts.clone()));
        }

        // Execute tool calls
        if tool_calls.is_empty() {
            self.conversation.push(ConversationMessage::agent(&response));
            let _ = event_tx.send(AgentEvent::StateChanged(AgentState::Completed));
            let _ = event_tx.send(AgentEvent::Done);
            return Ok(());
        }

        let _ = event_tx.send(AgentEvent::StateChanged(AgentState::Executing));

        let mut all_tool_output = String::new();

        for tool_call in tool_calls {
            // Check permissions for dangerous operations
            if self.permissions.requires_approval(&tool_call.name, &tool_call.input) {
                let _ = event_tx.send(AgentEvent::ApprovalRequired {
                    command: tool_call.input.clone(),
                    description: format!("Execute: {}", tool_call.name),
                });
                // Wait is handled by UI; for now we skip
                continue;
            }

            let _ = event_tx.send(AgentEvent::ToolStarted(tool_call.clone()));

            let start = std::time::Instant::now();
            let result = self.tools.execute(&tool_call.name, &tool_call.input).await;
            let duration_ms = start.elapsed().as_millis() as u64;

            let tool_result = match result {
                Ok(output) => {
                    all_tool_output.push_str(&format!("\n[{}]: {}", tool_call.name, output));
                    ToolResult {
                        tool_name: tool_call.name.clone(),
                        success: true,
                        output,
                        duration_ms,
                    }
                }
                Err(e) => {
                    let err_msg = e.to_string();
                    all_tool_output.push_str(&format!("\n[{}] ERROR: {}", tool_call.name, err_msg));
                    ToolResult {
                        tool_name: tool_call.name.clone(),
                        success: false,
                        output: err_msg,
                        duration_ms,
                    }
                }
            };

            let _ = event_tx.send(AgentEvent::ToolCompleted(tool_result));
        }

        // Add to conversation
        let full_response = if all_tool_output.is_empty() {
            response
        } else {
            format!("{}\n\nTool results:{}", text_parts, all_tool_output)
        };

        self.conversation.push(ConversationMessage::agent(&full_response));

        let _ = event_tx.send(AgentEvent::StateChanged(AgentState::Completed));
        let _ = event_tx.send(AgentEvent::Done);

        Ok(())
    }

    async fn build_system_prompt(&self) -> String {
        let workspace = &self.workspace;

        // Gather context
        let git_branch = tokio::process::Command::new("git")
            .current_dir(workspace)
            .args(["branch", "--show-current"])
            .output()
            .await
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| "unknown".to_string());

        format!(
            r#"You are Forge, an autonomous terminal coding agent. You are working in workspace: {workspace}
Git branch: {git_branch}

You can use the following tools by responding with XML-style tool calls:

<tool name="filesystem.read" input="path/to/file"/>
<tool name="filesystem.write" input="path/to/file" content="file content here"/>
<tool name="filesystem.list" input="directory/path"/>
<tool name="shell.exec" input="command to run"/>
<tool name="git.status" input=""/>
<tool name="git.diff" input=""/>
<tool name="git.commit" input="commit message"/>
<tool name="git.push" input="branch-name"/>
<tool name="git.branch" input="new-branch-name"/>
<tool name="github.pr.create" input="PR title|||PR body"/>
<tool name="github.pr.list" input=""/>
<tool name="github.ci.status" input=""/>

Rules:
1. Plan before acting. Think step by step.
2. Read files before editing them.
3. Run tests after making changes.
4. Always check git status before committing.
5. Write clear commit messages.
6. Be concise but thorough in explanations.
7. If a task is ambiguous, ask for clarification.
8. Use proper error handling and follow existing code patterns.

You are in AUTO mode: {auto_mode}
When auto mode is off, ask for approval before: git push, creating PRs, deleting files.
"#,
            workspace = workspace,
            git_branch = git_branch,
            auto_mode = self.auto_mode,
        )
    }
}

/// Parse agent response into text and tool calls
fn parse_agent_response(response: &str) -> (String, Vec<ToolCall>) {
    use regex::Regex;

    let tool_re = Regex::new(
        r#"<tool\s+name="([^"]+)"\s+input="([^"]*)"(?:\s+content="([^"]*)")?\s*/>"#
    ).unwrap();

    let mut tool_calls = Vec::new();
    let mut text = response.to_string();

    for cap in tool_re.captures_iter(response) {
        let name = cap[1].to_string();
        let input = if let Some(content) = cap.get(3) {
            // For write operations, input = path, content = body
            format!("{}|||{}", &cap[2], content.as_str())
        } else {
            cap[2].to_string()
        };

        tool_calls.push(ToolCall {
            id: uuid::Uuid::new_v4().to_string(),
            name,
            input,
        });
    }

    // Remove tool call XML from text
    let clean_text = tool_re.replace_all(&text, "").trim().to_string();

    (clean_text, tool_calls)
}
