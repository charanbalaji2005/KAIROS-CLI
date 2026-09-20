from forge.config.schema import ForgeConfig
from forge.llm.base import LLMProvider, LLMResponse, ToolCall
from forge.llm.anthropic import AnthropicProvider
from forge.llm.openai import OpenAIProvider
from forge.llm.ollama import OllamaProvider
from forge.llm.gemini import GeminiProvider
from forge.llm.groq import GroqProvider


def get_provider(config: ForgeConfig) -> LLMProvider:
    """Instantiates the appropriate LLMProvider based on user configuration."""
    provider_name = (config.provider or "ollama").lower()
    model = config.model

    if provider_name == "groq":
        return GroqProvider(
            model=model or "qwen/qwen3.8-27b",
            api_key=config.groq_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider_name == "anthropic":
        # Resolve model shortcuts
        if model in ("claude", "claude-sonnet", "default"):
            model = "claude-3-5-sonnet-20241022"
        elif model == "claude-haiku":
            model = "claude-3-5-haiku-20241022"
        return AnthropicProvider(
            model=model,
            api_key=config.anthropic_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider_name == "openai":
        if model in ("gpt", "gpt-4o", "default"):
            model = "gpt-4o"
        elif model == "gpt-4o-mini":
            model = "gpt-4o-mini"
        return OpenAIProvider(
            model=model,
            api_key=config.openai_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider_name == "gemini":
        if model in ("gemini", "gemini-flash", "default"):
            model = "gemini-2.5-flash"
        elif model == "gemini-pro":
            model = "gemini-1.5-pro"
        return GeminiProvider(
            model=model,
            api_key=config.gemini_api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider_name == "groq":
        groq_model = model
        if not groq_model or groq_model in ("qwen-coder", "default", "qwen"):
            groq_model = "qwen/qwen3.8-27b"
        elif groq_model in ("llama", "llama-3.3"):
            groq_model = "llama-3.3-70b-versatile"
        return OpenAIProvider(
            model=groq_model,
            api_key=config.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    else:  # Default to ollama
        ollama_name = model
        if model == "qwen-coder":
            ollama_name = "qwen2.5-coder:3b"
        elif model == "deepseek-coder":
            ollama_name = "deepseek-coder:1.3b"
        elif model == "phi3-mini":
            ollama_name = "phi3:mini"
        return OllamaProvider(
            model=ollama_name,
            base_url=config.ollama_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ToolCall",
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "GeminiProvider",
    "GroqProvider",
    "get_provider",
]
