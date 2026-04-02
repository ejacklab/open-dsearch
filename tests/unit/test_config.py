"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

import config


class TestConfigValidation:
    """Tests for configuration loading and validation."""
    
    def test_load_config_nonexistent_returns_empty(self, tmp_path, monkeypatch):
        """Config loading should return empty dict for missing file."""
        monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "nonexistent.toml")
        result = config.load_config()
        assert result == {}
    
    def test_load_config_valid_toml(self, tmp_path, monkeypatch):
        """Should parse valid TOML configuration."""
        toml_content = """
GEMINI_API_KEY = "test-key-123"
MINIMAX_API_KEY = "minimax-test"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml_content)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        
        result = config.load_config()
        assert result["GEMINI_API_KEY"] == "test-key-123"
        assert result["MINIMAX_API_KEY"] == "minimax-test"
    
    def test_get_secret_priority_env_over_config(self, monkeypatch, tmp_path):
        """Environment variables should override config file."""
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        
        toml_content = 'GEMINI_API_KEY = "config-key"'
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml_content)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        
        secret = config.get_secret("gemini")
        assert secret == "env-key"
    
    def test_get_secret_fallback_to_config(self, tmp_path, monkeypatch):
        """Should fallback to config when env var not set."""
        # Ensure env var is not set
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        toml_content = 'GEMINI_API_KEY = "config-key"'
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml_content)
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        
        secret = config.get_secret("gemini")
        assert secret == "config-key"
    
    def test_get_secret_unknown_provider_returns_none(self):
        """Unknown providers should return None."""
        assert config.get_secret("unknown_provider") is None
    
    def test_ensure_config_dir_creates_directory(self, tmp_path, monkeypatch):
        """Should create config directory if missing."""
        config_dir = tmp_path / ".config" / "dsearch"
        monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
        
        config.ensure_config_dir()
        assert config_dir.exists()
    
    def test_get_secret_all_providers(self, monkeypatch):
        """Test all supported providers."""
        providers = {
            "gemini": "GEMINI_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "kimi": "KIMI_API_KEY",
            "xai": "XAI_API_KEY",
            "tavily": "TAVILY_API_KEY",
            "exa": "EXA_API_KEY",
            "brave": "BRAVE_API_KEY",
        }
        
        for provider, env_name in providers.items():
            monkeypatch.setenv(env_name, f"test-{provider}-key")
            secret = config.get_secret(provider)
            assert secret == f"test-{provider}-key"
            monkeypatch.delenv(env_name)


class TestConfigSecurity:
    """Security-focused configuration tests."""
    
    def test_no_hardcoded_secrets_in_config(self):
        """Verify no hardcoded secrets in config module."""
        config_source = Path(config.__file__).read_text()
        # Check for common secret patterns
        # Only scan actual code lines (not comments) for hardcoded secrets
        code_lines = [
            line for line in config_source.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        code_text = "\n".join(code_lines)
        suspicious_patterns = [
            "sk-",  # OpenAI-style key pattern
            "api_key = \"",  # Hardcoded key (in actual code, not comments)
            "password = \"",
            "secret = \"",
        ]
        for pattern in suspicious_patterns:
            assert pattern not in code_text.lower(), f"Found suspicious pattern: {pattern}"
    
    def test_config_path_uses_home_directory(self):
        """Config should be in user's home directory."""
        assert str(Path.home()) in str(config.CONFIG_DIR)
    
    def test_create_example_config_no_secrets(self, tmp_path, monkeypatch):
        """Example config should not contain real secrets."""
        monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
        
        example_path = config.create_example_config()
        content = example_path.read_text()
        
        # Should contain placeholder text
        assert "your-key-here" in content or "your" in content.lower()
        # Should have commented out keys
        assert "# GEMINI_API_KEY" in content


class TestConfigPath:
    """Tests for configuration paths."""
    
    def test_get_config_path_returns_path_object(self):
        """get_config_path should return a Path."""
        path = config.get_config_path()
        assert isinstance(path, Path)
    
    def test_config_dir_is_path_object(self):
        """CONFIG_DIR should be a Path object."""
        assert isinstance(config.CONFIG_DIR, Path)
    
    def test_config_file_is_path_object(self):
        """CONFIG_FILE should be a Path object."""
        assert isinstance(config.CONFIG_FILE, Path)
