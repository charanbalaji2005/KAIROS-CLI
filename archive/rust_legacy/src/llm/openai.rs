use anyhow::Result;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

use super::provider::{LlmMessage, LlmProvider, LlmRole, StreamChunk};

pub struct OpenAiProvider {
    api_key: String,
    model: String,
    client: reqwest::Client,
}

impl OpenAiProvider {
    pub fn new(api_key: String, model: String) -> Self {
        let openai_model = match model.as_str() {
            "gpt-4o" => "gpt-4o",
            "gpt-4o-mini" => "gpt-4o-mini",
            other => other,
        };
        Self {
            api_key,
            model: openai_model.to_string(),
            client: reqwest::Client::new(),
        }
    }
}

#[derive(Serialize)]
struct OpenAiRequest {
    model: String,
    messages: Vec<OpenAiMessage>,
    max_tokens: u32,
    temperature: f32,
}

#[derive(Serialize, Deserialize)]
struct OpenAiMessage {
    role: String,
    content: String,
}

#[async_trait]
impl LlmProvider for OpenAiProvider {
    fn name(&self) -> &str {
        "openai"
    }

    fn model(&self) -> &str {
        &self.model
    }

    async fn complete(&self, messages: &[LlmMessage]) -> Result<String> {
        let msgs: Vec<OpenAiMessage> = messages.iter()
            .map(|m| OpenAiMessage {
                role: m.role.to_string(),
                content: m.content.clone(),
            })
            .collect();

        let req = OpenAiRequest {
            model: self.model.clone(),
            messages: msgs,
            max_tokens: 4096,
            temperature: 0.1,
        };

        let resp = self.client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&req)
            .send()
            .await?;

        let body: serde_json::Value = resp.json().await?;
        let content = body["choices"][0]["message"]["content"]
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
        let content = self.complete(messages).await?;
        let _ = tx.send(StreamChunk { content, done: true });
        Ok(())
    }
}
