#!/usr/bin/env python3
"""Configuration management for open-dsearch."""

import os
from pathlib import Path
from typing import Optional


def _load_dotenv():
    """Auto-load .env from project root."""
    for candidate in [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break

_load_dotenv()

CONFIG_DIR = Path.home() / ".config" / "dsearch"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_config_path() -> Path:
    """Get the configuration file path."""
    return CONFIG_FILE


def ensure_config_dir():
    """Ensure configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file."""
    config = {}
    
    if CONFIG_FILE.exists():
        try:
            import tomllib
            with open(CONFIG_FILE, "rb") as f:
                config = tomllib.load(f)
        except ImportError:
            # Python < 3.11, use tomli or simple parsing
            try:
                import tomli as tomllib
                with open(CONFIG_FILE, "rb") as f:
                    config = tomllib.load(f)
            except ImportError:
                # Fallback: simple key=value parsing
                with open(CONFIG_FILE, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            config[key.strip()] = value.strip().strip('"')
    
    return config


def get_secret(provider: str) -> Optional[str]:
    """
    Get API key for a provider.
    
    Priority:
    1. Environment variable
    2. Config file (~/.config/dsearch/config.toml)
    3. None
    """
    env_vars = {
        "gemini": "GEMINI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "kimi": "KIMI_API_KEY",
        "xai": "XAI_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "exa": "EXA_API_KEY",
        "brave": "BRAVE_API_KEY",
    }
    
    env_name = env_vars.get(provider)
    if not env_name:
        return None
    
    # 1. Check environment variable first
    secret = os.environ.get(env_name)
    if secret:
        return secret
    
    # 2. Check config file
    config = load_config()
    secret = config.get(env_name)
    if secret:
        return secret
    
    return None


def create_example_config():
    """Create an example configuration file."""
    ensure_config_dir()
    
    example = """# Open Dsearch Configuration
# Place your API keys here or set them as environment variables

# Google Gemini API (for web search)
# GEMINI_API_KEY = "your-key-here"

# MiniMax API (for coding-focused search)
# MINIMAX_API_KEY = "your-key-here"

# Kimi/Moonshot AI API (for web search)
# KIMI_API_KEY = "your-key-here"

# xAI API (for Grok search)
# XAI_API_KEY = "your-key-here"

# Optional: Custom API hosts
# MINIMAX_API_HOST = "https://api.minimax.io"
# KIMI_API_HOST = "https://api.moonshot.ai"
"""
    
    example_path = CONFIG_DIR / "config.toml.example"
    with open(example_path, "w") as f:
        f.write(example)
    
    return example_path


if __name__ == "__main__":
    example = create_example_config()
    print(f"Created example config: {example}")
    print(f"Config directory: {CONFIG_DIR}")
    print("\nTo configure:")
    print(f"1. Copy {example} to {CONFIG_FILE}")
    print("2. Edit and add your API keys")
    print("3. Or set environment variables directly")
