"""
Configuration management for Open Dsearch.

Supports loading configuration from multiple sources:
- Environment variables
- Configuration files (YAML, JSON, TOML)
- Default values

Priority: Environment > Config File > Defaults
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path as _Path

# Auto-load .env file if present (project root or parent dirs)
def _load_dotenv():
    for candidate in [
        _Path.cwd() / ".env",
        _Path(__file__).resolve().parent.parent.parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ConfigSource(Enum):
    """Source of configuration value."""
    DEFAULT = auto()
    FILE = auto()
    ENVIRONMENT = auto()
    CODE = auto()


class ConfigError(Exception):
    """Configuration-related error."""
    pass


@dataclass
class ConfigValue:
    """A configuration value with metadata."""
    value: Any
    source: ConfigSource
    key: str
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"ConfigValue({self.key}={self.value}, source={self.source.name})"


@dataclass
class Config:
    """
    Configuration manager for Open Dsearch.
    
    Loads configuration from multiple sources with priority:
    1. Environment variables
    2. Configuration files
    3. Default values
    
    Attributes:
        config_dir: Directory for configuration files
        config_file: Path to main configuration file
        env_prefix: Prefix for environment variables
    """
    config_dir: Path = field(
        default_factory=lambda: Path.home() / ".config" / "dsearch"
    )
    config_file: Optional[Path] = None
    env_prefix: str = "DSEARCH"
    _values: Dict[str, ConfigValue] = field(default_factory=dict, init=False)
    _defaults: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """Initialize configuration."""
        if self.config_file is None:
            self.config_file = self.config_dir / "config.yaml"
        
        # Set default values
        self._set_defaults()
        
        # Load from file if exists
        self._load_from_file()
        
        # Override with environment
        self._load_from_env()
    
    def _set_defaults(self) -> None:
        """Set default configuration values."""
        self._defaults = {
            # API Settings
            "api_timeout": 30.0,
            "api_max_retries": 3,
            "api_retry_delay": 1.0,
            
            # Search Settings
            "default_providers": ["gemini", "minimax", "kimi", "xai"],
            "default_num_results": 10,
            "default_output_format": "json",
            "max_query_length": 500,
            
            # Rate Limiting
            "rate_limit_enabled": True,
            "rate_limit_strategy": "token_bucket",
            
            # Cache Settings
            "cache_enabled": False,
            "cache_ttl": 3600,
            "cache_backend": "memory",
            
            # Logging
            "log_level": "INFO",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            
            # Server Settings
            "server_host": "0.0.0.0",
            "server_port": 8080,
            
            # Vector Storage
            "vector_storage_enabled": False,
            "vector_storage_endpoint": None,
        }
        
        for key, value in self._defaults.items():
            self._values[key] = ConfigValue(
                value=value,
                source=ConfigSource.DEFAULT,
                key=key
            )
    
    def _load_from_file(self) -> None:
        """Load configuration from file."""
        if not self.config_file or not self.config_file.exists():
            return
        
        try:
            content = self.config_file.read_text()
            
            # Try YAML first
            data = None
            try:
                import yaml
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    data = parsed
            except (ImportError, yaml.YAMLError):
                pass

            # Fallback to JSON
            if data is None:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # Try TOML
                    try:
                        import tomllib
                        data = tomllib.loads(content)
                    except (ImportError, json.JSONDecodeError):
                        return

            if data and isinstance(data, dict):
                self._merge_config(data, ConfigSource.FILE)
        except Exception as e:
            raise ConfigError(f"Failed to load config file: {e}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            # API Keys (sensitive)
            "gemini_api_key": "GEMINI_API_KEY",
            "minimax_api_key": "MINIMAX_API_KEY",
            "kimi_api_key": "KIMI_API_KEY",
            "xai_api_key": "XAI_API_KEY",
            
            # General settings
            "api_timeout": f"{self.env_prefix}_API_TIMEOUT",
            "api_max_retries": f"{self.env_prefix}_API_MAX_RETRIES",
            "log_level": f"{self.env_prefix}_LOG_LEVEL",
            "server_host": f"{self.env_prefix}_SERVER_HOST",
            "server_port": f"{self.env_prefix}_SERVER_PORT",
            "cache_enabled": f"{self.env_prefix}_CACHE_ENABLED",
            "vector_storage_enabled": f"{self.env_prefix}_VECTOR_STORAGE_ENABLED",
            "vector_storage_endpoint": f"{self.env_prefix}_VECTOR_STORAGE_ENDPOINT",
        }
        
        for config_key, env_var in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert types
                current_value = self._values.get(config_key)
                if current_value:
                    value = self._convert_type(value, type(current_value.value))
                
                self._values[config_key] = ConfigValue(
                    value=value,
                    source=ConfigSource.ENVIRONMENT,
                    key=config_key
                )
    
    def _convert_type(self, value: str, target_type: type) -> Any:
        """Convert string value to target type."""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            # Try JSON parsing for lists
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(",")
        return value
    
    def _merge_config(self, data: Dict[str, Any], source: ConfigSource) -> None:
        """Merge configuration dictionary."""
        for key, value in data.items():
            # Convert key to lowercase with underscores
            config_key = key.lower().replace("-", "_")
            self._values[config_key] = ConfigValue(
                value=value,
                source=source,
                key=config_key
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config_value = self._values.get(key)
        if config_value is None:
            return default
        return config_value.value
    
    def get_with_source(self, key: str) -> Optional[ConfigValue]:
        """Get configuration value with source metadata."""
        return self._values.get(key)
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.CODE) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            source: Source of the value
        """
        self._values[key] = ConfigValue(
            value=value,
            source=source,
            key=key
        )
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider: Provider name (e.g., "gemini", "kimi")
            
        Returns:
            Provider-specific configuration
        """
        api_key = self.get(f"{provider}_api_key")
        
        return {
            "api_key": api_key,
            "timeout_seconds": self.get("api_timeout", 30.0),
            "max_retries": self.get("api_max_retries", 3),
            "enabled": api_key is not None,
        }
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return {
            key: config_value.value
            for key, config_value in self._values.items()
        }
    
    def get_all_with_source(self) -> Dict[str, ConfigValue]:
        """Get all configuration values with source."""
        return dict(self._values)
    
    def save_to_file(self, path: Optional[Path] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            path: Path to save to (default: config_file)
        """
        save_path = path or self.config_file
        if save_path is None:
            raise ConfigError("No config file path specified")
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Filter out sensitive values and environment overrides
        data = {}
        for key, config_value in self._values.items():
            if config_value.source in (ConfigSource.FILE, ConfigSource.DEFAULT):
                if "api_key" not in key:  # Don't save API keys
                    data[key] = config_value.value
        
        # Determine format from extension
        suffix = save_path.suffix.lower()
        
        if suffix in (".yaml", ".yml"):
            try:
                import yaml
                content = yaml.dump(data, default_flow_style=False)
            except ImportError:
                content = json.dumps(data, indent=2)
        elif suffix == ".toml":
            try:
                import tomli_w
                content = tomli_w.dumps(data)
            except ImportError:
                content = json.dumps(data, indent=2)
        else:
            content = json.dumps(data, indent=2)
        
        save_path.write_text(content)
    
    def ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_secret(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            API key or None
        """
        return self.get(f"{provider}_api_key")


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global configuration."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None


def init_config(
    config_dir: Optional[Path] = None,
    config_file: Optional[Path] = None,
    env_prefix: str = "DSEARCH"
) -> Config:
    """
    Initialize global configuration with custom settings.
    
    Args:
        config_dir: Configuration directory
        config_file: Configuration file path
        env_prefix: Environment variable prefix
        
    Returns:
        Configured Config instance
    """
    global _config
    _config = Config(
        config_dir=config_dir or Path.home() / ".config" / "dsearch",
        config_file=config_file,
        env_prefix=env_prefix
    )
    return _config