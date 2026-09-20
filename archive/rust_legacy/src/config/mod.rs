use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tokio::fs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForgeConfig {
    pub model: Option<String>,
    pub provider: Option<String>,
    pub auto_mode: Option<bool>,
    pub anthropic_api_key: Option<String>,
    pub openai_api_key: Option<String>,
    pub gemini_api_key: Option<String>,
    pub ollama_url: Option<String>,
    pub max_tokens: Option<u32>,
    pub temperature: Option<f32>,
    pub theme: Option<String>,
    pub compact_mode: Option<bool>,
}

impl Default for ForgeConfig {
    fn default() -> Self {
        Self {
            model: Some("qwen-coder".to_string()),
            provider: Some("ollama".to_string()),
            auto_mode: Some(false),
            anthropic_api_key: None,
            openai_api_key: None,
            gemini_api_key: None,
            ollama_url: Some("http://localhost:11434".to_string()),
            max_tokens: Some(4096),
            temperature: Some(0.1),
            theme: Some("dark".to_string()),
            compact_mode: Some(false),
        }
    }
}

impl ForgeConfig {
    pub fn config_path() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".forge")
            .join("config.json")
    }

    pub async fn load() -> Result<Self> {
        let path = Self::config_path();
        if path.exists() {
            let content = fs::read_to_string(&path).await?;
            let cfg: ForgeConfig = serde_json::from_str(&content)?;
            Ok(cfg)
        } else {
            let cfg = ForgeConfig::default();
            cfg.save().await?;
            Ok(cfg)
        }
    }

    pub async fn save(&self) -> Result<()> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).await?;
        }
        let content = serde_json::to_string_pretty(self)?;
        fs::write(&path, content).await?;
        Ok(())
    }

    pub async fn set(&mut self, key: &str, value: &str) -> Result<()> {
        match key {
            "model" => self.model = Some(value.to_string()),
            "provider" => self.provider = Some(value.to_string()),
            "auto_mode" => self.auto_mode = Some(value == "true"),
            "anthropic_api_key" => self.anthropic_api_key = Some(value.to_string()),
            "openai_api_key" => self.openai_api_key = Some(value.to_string()),
            "gemini_api_key" => self.gemini_api_key = Some(value.to_string()),
            "ollama_url" => self.ollama_url = Some(value.to_string()),
            "max_tokens" => self.max_tokens = Some(value.parse()?),
            "temperature" => self.temperature = Some(value.parse()?),
            _ => return Err(anyhow::anyhow!("Unknown config key: {}", key)),
        }
        self.save().await?;
        Ok(())
    }

    pub fn get_provider(&self) -> &str {
        self.provider.as_deref().unwrap_or("ollama")
    }

    pub fn get_model(&self) -> &str {
        self.model.as_deref().unwrap_or("qwen-coder")
    }
}
