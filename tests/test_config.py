"""Tests for configuration loader and schema."""

import tempfile
from pathlib import Path

from forge.config.schema import ForgeConfig
from forge.config.loader import load_config, save_config, set_config_value


def test_config_defaults_and_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = Path(tmpdir) / "config.json"

        # Defaults
        cfg = load_config(config_file=cfg_file)
        assert cfg.model == "qwen-coder"
        assert cfg.provider == "ollama"
        assert cfg.auto_mode is False

        # Set value
        updated = set_config_value("model", "claude-sonnet", config_file=cfg_file)
        assert updated.model == "claude-sonnet"

        # Re-load
        reloaded = load_config(config_file=cfg_file)
        assert reloaded.model == "claude-sonnet"
