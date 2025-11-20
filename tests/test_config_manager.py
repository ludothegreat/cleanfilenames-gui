"""Tests for config_manager module."""

import json
from pathlib import Path

import pytest

from config_manager import (
    AppConfig,
    ConfigLoadError,
    DEFAULT_PATTERN,
    DEFAULT_TOKENS,
    build_regex,
    load_preset_tokens,
)


class TestBuildRegex:
    """Tests for build_regex function."""

    def test_single_token(self):
        """Test regex building with single token."""
        tokens = ["USA"]
        pattern = build_regex(tokens)
        assert pattern == r"\s*\((?:USA)\)\s*"

    def test_multiple_tokens(self):
        """Test regex building with multiple tokens."""
        tokens = ["USA", "EU", "JP"]
        pattern = build_regex(tokens)
        assert pattern == r"\s*\((?:USA|EU|JP)\)\s*"

    def test_empty_tokens(self):
        """Test regex building with empty token list."""
        tokens = []
        pattern = build_regex(tokens)
        assert pattern == r"\s*\((?:)\)\s*"

    def test_filters_none_values(self):
        """Test that None values are filtered out."""
        tokens = ["USA", None, "EU"]
        pattern = build_regex(tokens)
        assert pattern == r"\s*\((?:USA|EU)\)\s*"


class TestLoadPresetTokens:
    """Tests for load_preset_tokens function."""

    def test_loads_default_preset(self):
        """Test loading default preset."""
        tokens = load_preset_tokens("default")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_loads_minimal_preset(self):
        """Test loading minimal preset."""
        tokens = load_preset_tokens("minimal")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_nonexistent_preset_returns_empty(self):
        """Test that nonexistent preset returns empty list."""
        tokens = load_preset_tokens("nonexistent")
        assert tokens == []


class TestAppConfig:
    """Tests for AppConfig class."""

    def test_default_values(self):
        """Test that default config has expected values."""
        config = AppConfig()
        assert config.regex == DEFAULT_PATTERN
        assert config.rename_directories is True
        assert config.rename_root is True
        assert config.stop_on_error is False
        assert config.auto_resolve_conflicts is False
        assert config.tokens == DEFAULT_TOKENS

    def test_save_and_load(self, temp_dir):
        """Test saving and loading config."""
        config_path = temp_dir / "config.json"

        config = AppConfig()
        config.rename_directories = False
        config.save(config_path)

        loaded = AppConfig.load(config_path)
        assert loaded.rename_directories is False

    def test_load_creates_default_if_missing(self):
        """Test that loading creates default config if file doesn't exist."""
        # When no path is specified, it should create default at default location
        config = AppConfig.load()

        # Just verify we got a valid config object with expected fields
        assert config is not None
        assert config.regex is not None
        assert isinstance(config.tokens, list)

    def test_load_with_custom_path_missing_raises_error(self, temp_dir):
        """Test that loading with explicit path raises error if missing."""
        config_path = temp_dir / "missing.json"
        with pytest.raises(FileNotFoundError):
            AppConfig.load(config_path)

    def test_save_creates_parent_directories(self, temp_dir):
        """Test that save creates parent directories."""
        config_path = temp_dir / "nested" / "dir" / "config.json"
        config = AppConfig()
        config.save(config_path)

        assert config_path.exists()

    def test_load_invalid_json_raises_error(self, temp_dir):
        """Test that invalid JSON raises ConfigLoadError."""
        config_path = temp_dir / "bad.json"
        config_path.write_text("not valid json {")

        with pytest.raises(ConfigLoadError):
            AppConfig.load(config_path)

    def test_load_with_custom_tokens(self, temp_dir):
        """Test loading config with custom tokens."""
        config_path = temp_dir / "config.json"
        custom_tokens = ["CUSTOM1", "CUSTOM2"]

        config = AppConfig()
        config.tokens = custom_tokens
        config.save(config_path)

        loaded = AppConfig.load(config_path)
        assert loaded.tokens == custom_tokens

    def test_load_rebuilds_regex_from_tokens(self, temp_dir):
        """Test that regex is rebuilt from tokens on load."""
        config_path = temp_dir / "config.json"
        custom_tokens = ["CUSTOM1", "CUSTOM2"]

        config = AppConfig()
        config.tokens = custom_tokens
        config.save(config_path)

        loaded = AppConfig.load(config_path)
        expected_regex = build_regex(custom_tokens)
        assert loaded.regex == expected_regex

    def test_load_with_none_tokens(self, temp_dir):
        """Test loading config with None tokens."""
        config_path = temp_dir / "config.json"
        data = {
            "regex": DEFAULT_PATTERN,
            "tokens": None,
            "rename_directories": True,
            "rename_root": True,
            "stop_on_error": False,
            "auto_resolve_conflicts": False,
        }
        config_path.write_text(json.dumps(data))

        loaded = AppConfig.load(config_path)
        assert loaded.tokens is None

    def test_auto_resolve_conflicts_setting(self, temp_dir):
        """Test auto_resolve_conflicts setting persists."""
        config_path = temp_dir / "config.json"

        config = AppConfig()
        config.auto_resolve_conflicts = True
        config.save(config_path)

        loaded = AppConfig.load(config_path)
        assert loaded.auto_resolve_conflicts is True
