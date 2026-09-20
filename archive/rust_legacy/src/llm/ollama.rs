use anyhow::Result;
use async_trait::async_trait;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

use super::provider::{LlmMessage, LlmProvider, LlmRole, StreamChunk};

pub struct OllamaProvider {
    base_url: String,
    model: String,
    client: reqwest::Client,
}

impl OllamaProvider {
    pub fn new(base_url: String, model: String) -> Self {
        Self {
            base_url,
            model,
            client: reqwest::Client::new(),
        }
    }
}

#[derive(Serialize)]
struct OllamaRequest {
    model: String,
    messages: Vec<OllamaMessage>,
    stream: bool,
    options: OllamaOptions,
}

#[derive(Serialize)]
struct OllamaOptions {
    temperature: f32,
    num_predict: i32,
}

#[derive(Serialize, Deserialize)]
struct OllamaMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct OllamaResponse {
    message: Option<OllamaMessage>,
    done: bool,
}

fn to_ollama_messages(messages: &[LlmMessage]) -> Vec<OllamaMessage> {
    messages
        .iter()
        .map(|m| OllamaMessage {
            role: m.role.to_string(),
            content: m.content.clone(),
        })
        .collect()
}

#[async_trait]
impl LlmProvider for OllamaProvider {
    fn name(&self) -> &str {
        "ollama"
    }

    fn model(&self) -> &str {
        &self.model
    }

    async fn complete(&self, messages: &[LlmMessage]) -> Result<String> {
        let req = OllamaRequest {
            model: self.model.clone(),
            messages: to_ollama_messages(messages),
            stream: false,
            options: OllamaOptions {
                temperature: 0.1,
                num_predict: 4096,
            },
        };

        let resp = self.client
            .post(format!("{}/api/chat", self.base_url))
            .json(&req)
            .send()
            .await?;

        let body: serde_json::Value = resp.json().await?;
        let content = body["message"]["content"]
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
        let req = OllamaRequest {
            model: self.model.clone(),
            messages: to_ollama_messages(messages),
            stream: true,
            options: OllamaOptions {
                temperature: 0.1,
                num_predict: 4096,
            },
        };

        let resp = self.client
            .post(format!("{}/api/chat", self.base_url))
            .json(&req)
            .send()
            .await?;

        let mut stream = resp.bytes_stream();

        while let Some(chunk) = stream.next().await {
            let chunk = chunk?;
            let text = String::from_utf8_lossy(&chunk);

            for line in text.lines() {
                if line.is_empty() {
                    continue;
                }
                if let Ok(resp) = serde_json::from_str::<OllamaResponse>(line) {
                    let content = resp.message
                        .as_ref()
                        .map(|m| m.content.clone())
                        .unwrap_or_default();

                    let _ = tx.send(StreamChunk {
                        content,
                        done: resp.done,
                    });

                    if resp.done {
                        break;
                    }
                }
            }
        }

        Ok(())
    }
}
