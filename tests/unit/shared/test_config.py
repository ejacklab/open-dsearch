"""Unit tests for configuration module."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.shared.config import (
    Config,
    ConfigValue,
    ConfigSource,
    ConfigError,
    get_config,
    reset_config,
    init_config,
)


class TestConfigValue:
    """Tests for ConfigValue dataclass."""
    
    def test_create(self):
        """Test creating a config value."""
        value = ConfigValue(
            value="test",
            source=ConfigSource.DEFAULT,
            key="test_key"
        )
        
        assert value.value == "test"
        assert value.source == ConfigSource.DEFAULT
        assert value.key == "test_key"
    
    def test_str(self):
        """Test string representation."""
        value = ConfigValue(value=123, source=ConfigSource.ENVIRONMENT, key="num")
        assert str(value) == "123"
    
    def test_repr(self):
        """Test repr."""
        value = ConfigValue(value="x", source=ConfigSource.FILE, key="y")
        repr_str = repr(value)
        assert "ConfigValue" in repr_str
        assert "FILE" in repr_str


class TestConfig:
    """Tests for Config class."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def teardown_method(self):
        """Reset config after each test."""
        reset_config()
    
    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.get("api_timeout") == 30.0
        assert config.get("api_max_retries") == 3
        assert config.get("default_output_format") == "json"
        assert config.get("log_level") == "INFO"
    
    def test_get_with_default(self):
        """Test get with default value."""
        config = Config()
        
        assert config.get("nonexistent", "default") == "default"
        assert config.get("nonexistent") is None
    
    def test_set_value(self):
        """Test setting a value."""
        config = Config()
        config.set("custom_key", "custom_value")
        
        assert config.get("custom_key") == "custom_value"
    
    def test_get_with_source(self):
        """Test getting value with source metadata."""
        config = Config()
        value = config.get_with_source("api_timeout")
        
        assert isinstance(value, ConfigValue)
        assert value.source == ConfigSource.DEFAULT
    
    def test_environment_override(self):
        """Test environment variable override."""
        with patch.dict(os.environ, {"DSEARCH_API_TIMEOUT": "60.0"}):
            config = Config()
            assert config.get("api_timeout") == 60.0
    
    def test_provider_api_key_from_env(self):
        """Test provider API key from environment."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}):
            config = Config()
            assert config.get("gemini_api_key") == "test-key-123"
    
    def test_get_provider_config(self):
        """Test getting provider-specific config."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}):
            config = Config()
            provider_config = config.get_provider_config("gemini")
            
            assert provider_config["api_key"] == "secret"
            assert provider_config["timeout_seconds"] == 30.0
            assert provider_config["enabled"] is True
    
    def test_get_provider_config_no_key(self):
        """Test provider config when no API key."""
        config = Config()
        provider_config = config.get_provider_config("unknown")
        
        assert provider_config["api_key"] is None
        assert provider_config["enabled"] is False
    
    def test_load_from_json_file(self):
        """Test loading from JSON config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text('{"custom_setting": "value123"}')
            
            config = Config(config_file=config_file)
            assert config.get("custom_setting") == "value123"
    
    def test_load_from_invalid_file(self):
        """Test loading from invalid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text("not valid json")
            
            # Should not raise, just skip file
            config = Config(config_file=config_file)
            assert config.get("api_timeout") == 30.0  # Default still works
    
    def test_ensure_config_dir(self):
        """Test ensuring config directory exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "test_config"
            config = Config(config_dir=config_dir)
            config.ensure_config_dir()
            
            assert config_dir.exists()
    
    def test_save_to_file(self):
        """Test saving config to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config = Config(config_file=config_file)
            config.set("test_key", "test_value", source=ConfigSource.CODE)
            config.save_to_file()
            
            assert config_file.exists()
            content = config_file.read_text()
            assert "test_key" in content
    
    def test_save_to_file_no_path(self):
        """Test saving without file path raises error."""
        config = Config(config_file=None)
        
        with pytest.raises(ConfigError, match="No config file path"):
            config.save_to_file()
    
    def test_type_conversion_bool(self):
        """Test boolean type conversion from env."""
        with patch.dict(os.environ, {"DSEARCH_CACHE_ENABLED": "true"}):
            config = Config()
            assert config.get("cache_enabled") is True
        
        with patch.dict(os.environ, {"DSEARCH_CACHE_ENABLED": "false"}):
            reset_config()
            config = Config()
            assert config.get("cache_enabled") is False
    
    def test_type_conversion_int(self):
        """Test integer type conversion from env."""
        with patch.dict(os.environ, {"DSEARCH_SERVER_PORT": "9090"}):
            config = Config()
            assert config.get("server_port") == 9090
    
    def test_type_conversion_float(self):
        """Test float type conversion from env."""
        with patch.dict(os.environ, {"DSEARCH_API_TIMEOUT": "45.5"}):
            config = Config()
            assert config.get("api_timeout") == 45.5
    
    def test_type_conversion_list(self):
        """Test list type conversion from env."""
        with patch.dict(os.environ, {"DSEARCH_DEFAULT_PROVIDERS": "gemini,kimi"}):
            config = Config()
            result = config.get("default_providers")
            assert result == ["gemini", "kimi"]
    
    def test_get_secret(self):
        """Test get_secret method."""
        with patch.dict(os.environ, {"KIMI_API_KEY": "secret-key"}):
            config = Config()
            assert config.get_secret("kimi") == "secret-key"
    
    def test_get_all(self):
        """Test getting all config values."""
        config = Config()
        all_config = config.get_all()
        
        assert "api_timeout" in all_config
        assert "log_level" in all_config
    
    def test_get_all_with_source(self):
        """Test getting all config with source."""
        config = Config()
        all_config = config.get_all_with_source()
        
        assert "api_timeout" in all_config
        assert isinstance(all_config["api_timeout"], ConfigValue)


class TestGlobalConfig:
    """Tests for global config functions."""
    
    def setup_method(self):
        """Reset before each test."""
        reset_config()
    
    def teardown_method(self):
        """Reset after each test."""
        reset_config()
    
    def test_get_config_creates_instance(self):
        """Test get_config creates global instance."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reset_config(self):
        """Test reset_config clears instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        
        assert config1 is not config2
    
    def test_init_config(self):
        """Test init_config with custom settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "custom"
            config = init_config(
                config_dir=config_dir,
                env_prefix="TEST"
            )
            
            assert config.config_dir == config_dir
            assert config.env_prefix == "TEST"
