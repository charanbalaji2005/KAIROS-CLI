"""Configuration schema for Forge."""

from typing import Optional
from pydantic import BaseModel, Field


class ForgeConfig(BaseModel):
    """Global configuration settings for Forge."""

    model: str = Field(default="qwen-coder", description="Active model identifier")
    provider: str = Field(default="ollama", description="Active LLM provider: ollama, anthropic, openai, gemini")
    auto_mode: bool = Field(default=False, description="Skip confirmation prompts for autonomous execution")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic Claude API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key")
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    max_tokens: int = Field(default=4096, description="Max generation tokens")
    temperature: float = Field(default=0.1, description="Sampling temperature")
    theme: str = Field(default="dark", description="Terminal theme: dark, orange, classic")
    compact_mode: bool = Field(default=False, description="Compact header view")
    max_iterations: int = Field(default=30, description="Maximum iterations in the agent loop")
    workspace: Optional[str] = Field(default=None, description="Default or active workspace directory")

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }
