"""Configuration loader for Forge with environment variable overrides."""

import json
import os
from pathlib import Path
from typing import Optional

from forge.config.schema import ForgeConfig


def get_forge_dir() -> Path:
    """Returns ~/.forge directory, ensuring it exists."""
    home = Path.home()
    forge_dir = home / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    return forge_dir


def get_config_path() -> Path:
    """Returns the full path to ~/.forge/config.json."""
    return get_forge_dir() / "config.json"


def load_config(config_file: Optional[Path] = None) -> ForgeConfig:
    """Loads configuration from JSON file and applies environment variable overrides."""
    target_path = config_file or get_config_path()
    cfg_data = {}

    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
        except Exception:
            cfg_data = {}

    config = ForgeConfig(**cfg_data)

    # Environment variable overrides
    if os.getenv("FORGE_MODEL"):
        config.model = os.getenv("FORGE_MODEL")
    if os.getenv("FORGE_PROVIDER"):
        config.provider = os.getenv("FORGE_PROVIDER")
    if os.getenv("FORGE_AUTO"):
        config.auto_mode = os.getenv("FORGE_AUTO", "").lower() in ("1", "true", "yes")
    if os.getenv("ANTHROPIC_API_KEY"):
        config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if os.getenv("OPENAI_API_KEY"):
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        config.gemini_api_key = os.getenv("GEMINI_API_KEY")
    if os.getenv("GROQ_API_KEY"):
        config.groq_api_key = os.getenv("GROQ_API_KEY")
    if os.getenv("OLLAMA_URL"):
        config.ollama_url = os.getenv("OLLAMA_URL")

    return config


def save_config(config: ForgeConfig, config_file: Optional[Path] = None) -> Path:
    """Persists configuration to ~/.forge/config.json."""
    target_path = config_file or get_config_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(config.model_dump_json(indent=2))
    return target_path


def set_config_value(key: str, value: str, config_file: Optional[Path] = None) -> ForgeConfig:
    """Sets a single config key, persists to disk, and returns the updated config."""
    cfg = load_config(config_file)
    key_clean = key.strip()

    if key_clean == "auto_mode":
        val_bool = value.lower() in ("1", "true", "yes", "y")
        setattr(cfg, key_clean, val_bool)
    elif key_clean in ("max_tokens", "max_iterations"):
        setattr(cfg, key_clean, int(value))
    elif key_clean in ("temperature",):
        setattr(cfg, key_clean, float(value))
    elif key_clean == "compact_mode":
        setattr(cfg, key_clean, value.lower() in ("1", "true", "yes", "y"))
    elif hasattr(cfg, key_clean):
        setattr(cfg, key_clean, value)
    else:
        raise ValueError(f"Unknown configuration key: {key}")

    save_config(cfg, config_file)
    return cfg
