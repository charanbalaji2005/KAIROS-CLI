use anyhow::Result;
use async_trait::async_trait;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

use super::provider::{LlmMessage, LlmProvider, LlmRole, StreamChunk};

pub struct AnthropicProvider {
    api_key: String,
    model: String,
    client: reqwest::Client,
}

impl AnthropicProvider {
    pub fn new(api_key: String, model: String) -> Self {
        let anthropic_model = match model.as_str() {
            "claude-sonnet" => "claude-sonnet-4-5",
            "claude-opus" => "claude-opus-4-5",
            "claude-haiku" => "claude-haiku-4-5-20251001",
            other => other,
        };
        Self {
            api_key,
            model: anthropic_model.to_string(),
            client: reqwest::Client::new(),
        }
    }
}

#[derive(Serialize)]
struct AnthropicRequest {
    model: String,
    max_tokens: u32,
    system: Option<String>,
    messages: Vec<AnthropicMessage>,
    stream: bool,
}

#[derive(Serialize, Deserialize)]
struct AnthropicMessage {
    role: String,
    content: String,
}

#[async_trait]
impl LlmProvider for AnthropicProvider {
    fn name(&self) -> &str {
        "anthropic"
    }

    fn model(&self) -> &str {
        &self.model
    }

    async fn complete(&self, messages: &[LlmMessage]) -> Result<String> {
        let system = messages.iter()
            .find(|m| m.role == LlmRole::System)
            .map(|m| m.content.clone());

        let chat_messages: Vec<AnthropicMessage> = messages.iter()
            .filter(|m| m.role != LlmRole::System)
            .map(|m| AnthropicMessage {
                role: m.role.to_string(),
                content: m.content.clone(),
            })
            .collect();

        let req = AnthropicRequest {
            model: self.model.clone(),
            max_tokens: 4096,
            system,
            messages: chat_messages,
            stream: false,
        };

        let resp = self.client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&req)
            .send()
            .await?;

        let body: serde_json::Value = resp.json().await?;
        let content = body["content"][0]["text"]
            .as_str()
            .unwrap_or("")
            .to_string();

        Ok(content)
    }

    async fn stream(
        &self,
        messages: &[LlmMessage],
        tx: mpsc::UnboundedSender<StreamChunk>,
    ) -> Result<()> {
        // For now, fall back to non-streaming
        let content = self.complete(messages).await?;
        let _ = tx.send(StreamChunk { content, done: true });
        Ok(())
    }
}
