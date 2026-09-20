use anyhow::Result;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LlmRole {
    System,
    User,
    Assistant,
}

impl std::fmt::Display for LlmRole {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LlmRole::System => write!(f, "system"),
            LlmRole::User => write!(f, "user"),
            LlmRole::Assistant => write!(f, "assistant"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmMessage {
    pub role: LlmRole,
    pub content: String,
}

impl LlmMessage {
    pub fn system(content: impl Into<String>) -> Self {
        Self { role: LlmRole::System, content: content.into() }
    }

    pub fn user(content: impl Into<String>) -> Self {
        Self { role: LlmRole::User, content: content.into() }
    }

    pub fn assistant(content: impl Into<String>) -> Self {
        Self { role: LlmRole::Assistant, content: content.into() }
    }
}

#[derive(Debug, Clone)]
pub struct StreamChunk {
    pub content: String,
    pub done: bool,
}

#[async_trait]
pub trait LlmProvider: Send + Sync {
    fn name(&self) -> &str;
    fn model(&self) -> &str;

    async fn complete(&self, messages: &[LlmMessage]) -> Result<String>;

    async fn stream(
        &self,
        messages: &[LlmMessage],
        tx: mpsc::UnboundedSender<StreamChunk>,
    ) -> Result<()>;
}

/// Create a provider from config
pub async fn create_provider(
    provider_name: &str,
    model_name: &str,
    config: &crate::config::ForgeConfig,
) -> Result<Box<dyn LlmProvider>> {
    match provider_name {
        "anthropic" => {
            let key = config.anthropic_api_key.clone()
                .unwrap_or_else(|| std::env::var("ANTHROPIC_API_KEY").unwrap_or_default());
            Ok(Box::new(crate::llm::anthropic::AnthropicProvider::new(key, model_name.to_string())))
        }
        "openai" => {
            let key = config.openai_api_key.clone()
                .unwrap_or_else(|| std::env::var("OPENAI_API_KEY").unwrap_or_default());
            Ok(Box::new(crate::llm::openai::OpenAiProvider::new(key, model_name.to_string())))
        }
        _ => {
            // Default: Ollama
            let ollama_model = resolve_ollama_model(model_name);
            let base_url = config.ollama_url.clone()
                .unwrap_or_else(|| "http://localhost:11434".to_string());
            Ok(Box::new(crate::llm::ollama::OllamaProvider::new(base_url, ollama_model)))
        }
    }
}

fn resolve_ollama_model(model_name: &str) -> String {
    match model_name {
        "qwen-coder" => "qwen2.5-coder:3b",
        "qwen-chat" => "qwen2.5:3b",
        "qwen-think" => "qwen2.5:3b",
        "deepseek-coder" => "deepseek-coder:1.3b",
        "phi3-mini" => "phi3:mini",
        "llama3-mini" => "llama3.2:3b",
        other => other,
    }
    .to_string()
}
