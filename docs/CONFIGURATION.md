# Open Dsearch Configuration Guide

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

Complete guide to configuring Open Dsearch for different environments and use cases.

---

## Table of Contents

1. [Configuration Methods](#configuration-methods)
2. [API Keys](#api-keys)
3. [Configuration File](#configuration-file)
4. [Environment Variables](#environment-variables)
5. [Provider Configuration](#provider-configuration)
6. [Advanced Configuration](#advanced-configuration)
7. [Configuration Examples](#configuration-examples)

---

## Configuration Methods

Open Dsearch uses a hierarchical configuration system:

```
Priority (highest to lowest):
1. Environment variables
2. Config file (~/.config/dsearch/config.toml)
3. Default values
```

### Quick Setup

```bash
# 1. Create config directory
mkdir -p ~/.config/dsearch

# 2. Create config file
cp .env.example ~/.config/dsearch/config.toml

# 3. Edit and add your API keys
nano ~/.config/dsearch/config.toml
```

---

## API Keys

### Required Keys

At least one API key is required. We recommend starting with **Gemini** (free tier).

| Provider | Cost | Rate Limit | Best For |
|----------|------|------------|----------|
| **Gemini** | Free (1000/day) | 1000 req/day | General web search |
| **MiniMax** | Paid | Varies by plan | Coding/technical |
| **Kimi** | Paid | Varies by plan | Web search |
| **xAI/Grok** | Paid | Varies by plan | Real-time + X/Twitter |

### Getting API Keys

#### Gemini (Free)

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

```bash
export GEMINI_API_KEY="your-key-here"
```

#### MiniMax

1. Visit: https://www.minimax.io
2. Create account and apply for API access
3. Generate API key in dashboard

```bash
export MINIMAX_API_KEY="your-key-here"
```

#### Kimi/Moonshot

1. Visit: https://platform.moonshot.cn
2. Register and verify account
3. Create API key in console

```bash
export KIMI_API_KEY="your-key-here"
```

#### xAI/Grok

1. Visit: https://console.x.ai
2. Create account
3. Generate API key

```bash
export XAI_API_KEY="your-key-here"
```

---

## Configuration File

### Location

```
~/.config/dsearch/config.toml
```

### Format

```toml
# Open Dsearch Configuration
# Place your API keys here or set them as environment variables

# === API KEYS ===
# Google Gemini API (for web search)
GEMINI_API_KEY = "your-gemini-key-here"

# MiniMax API (for coding-focused search)
MINIMAX_API_KEY = "your-minimax-key-here"

# Kimi/Moonshot AI API (for web search)
KIMI_API_KEY = "your-kimi-key-here"

# xAI API (for Grok search)
XAI_API_KEY = "your-xai-key-here"

# === PROVIDER SETTINGS ===
[providers.gemini]
model = "gemini-1.5-flash"
temperature = 0.0
max_output_tokens = 1024

[providers.minimax]
model = "coding-plan"
host = "https://api.minimax.io"

[providers.kimi]
model = "moonshot-v1-8k"
host = "https://api.moonshot.ai"

[providers.xai]
model = "grok-4-1-fast-reasoning"
include_twitter = true

# === SEARCH SETTINGS ===
[search]
default_top = 5
default_queries = 5
default_mode = "vectors"
timeout = 300

# === OUTPUT SETTINGS ===
[output]
vector_storage_path = "./zvec_data"
json_output_dir = "./output/json"
md_output_dir = "./output/md"

# === RATE LIMITING ===
[rate_limits]
gemini = { rate = 2.0, burst = 5 }
minimax = { rate = 2.0, burst = 5 }
kimi = { rate = 1.0, burst = 3 }
xai = { rate = 2.0, burst = 5 }

# === LOGGING ===
[logging]
level = "info"  # debug, info, warn, error
format = "json"  # json, text
```

### Creating Example Config

```python
# Generate example config
python scripts/config.py

# Output:
# Created example config: ~/.config/dsearch/config.toml.example
# Config directory: ~/.config/dsearch
```

---

## Environment Variables

### API Key Variables

```bash
# Required (at least one)
export GEMINI_API_KEY="your-key"
export MINIMAX_API_KEY="your-key"
export KIMI_API_KEY="your-key"
export XAI_API_KEY="your-key"
```

### Optional Variables

```bash
# Custom API hosts
export MINIMAX_API_HOST="https://api.minimax.io"
export KIMI_API_HOST="https://api.moonshot.ai"

# Vector storage
export ZVEC_ENDPOINT="http://localhost:8000"

# Logging
export RUST_LOG=info  # debug, info, warn, error
export PYTHON_LOG_LEVEL=INFO

# Performance
export DSEARCH_TIMEOUT=300
export DSEARCH_MAX_CONCURRENT=20
```

### .env File

Create `.env` in project root:

```bash
# API Keys
GEMINI_API_KEY=your-gemini-key
MINIMAX_API_KEY=your-minimax-key
KIMI_API_KEY=your-kimi-key
XAI_API_KEY=your-xai-key

# Optional
RUST_LOG=info
DSEARCH_TIMEOUT=300
```

Load with:
```bash
# Using python-dotenv
from dotenv import load_dotenv
load_dotenv()

# Or export manually
export $(cat .env | xargs)
```

---

## Provider Configuration

### Provider Priority

Providers are used in order of availability. Configure priority:

```toml
[providers]
priority = ["gemini", "minimax", "kimi", "xai"]
```

### Provider-Specific Settings

#### Gemini

```toml
[providers.gemini]
model = "gemini-1.5-flash"  # or gemini-1.5-pro
search_tool = "googleSearch"  # or "googleSearchRetrieval"
temperature = 0.0
max_output_tokens = 1024
```

#### MiniMax

```toml
[providers.minimax]
model = "coding-plan"
host = "https://api.minimax.io"
version = "v1"
```

#### Kimi

```toml
[providers.kimi]
model = "moonshot-v1-8k"  # or moonshot-v1-32k
host = "https://api.moonshot.ai"
```

#### xAI

```toml
[providers.xai]
model = "grok-4-1-fast-reasoning"
include_twitter = true
include_web = true
temperature = 0.0
```

### Disabling Providers

```toml
[providers.minimax]
enabled = false
```

Or via environment:
```bash
export MINIMAX_ENABLED=false
```

---

## Advanced Configuration

### Rate Limiting

```toml
[rate_limits]
# Token bucket settings
# rate: tokens per second
# burst: maximum bucket size

gemini = { rate = 2.0, burst = 5 }
minimax = { rate = 2.0, burst = 5 }
kimi = { rate = 1.0, burst = 3 }
xai = { rate = 2.0, burst = 5 }
```

### Retry Configuration

```toml
[retry]
max_retries = 3
base_delay = 1.0  # seconds
max_delay = 60.0  # seconds
exponential_base = 2.0
```

### Vector Storage

```toml
[vector_storage]
backend = "zvec"  # zvec, chroma, qdrant, sqlite
path = "./zvec_data"
embedding_model = "gemini-embedding-001"
embedding_dimensions = 768

# For remote vector stores
[vector_storage.remote]
endpoint = "http://localhost:8000"
api_key = "optional-key"
```

### Output Formats

```toml
[output.formats]
markdown_template = "default"  # default, minimal, detailed
json_pretty = true
include_metadata = true
include_scores = true
```

### Caching (Future)

```toml
[cache]
enabled = true
backend = "sqlite"  # sqlite, redis, memory
ttl = 3600  # seconds
path = "./cache"
```

---

## Configuration Examples

### Minimal Config (Gemini Only)

```toml
# ~/.config/dsearch/config.toml
GEMINI_API_KEY = "your-free-key-here"
```

### Full Production Config

```toml
# ~/.config/dsearch/config.toml

# All providers
GEMINI_API_KEY = "gemini-key"
MINIMAX_API_KEY = "minimax-key"
KIMI_API_KEY = "kimi-key"
XAI_API_KEY = "xai-key"

# Provider settings
[providers]
priority = ["gemini", "kimi", "minimax", "xai"]

[providers.gemini]
model = "gemini-1.5-flash"

[providers.xai]
include_twitter = true

# Search defaults
[search]
default_top = 10
default_queries = 10
timeout = 300

# Rate limiting
[rate_limits]
gemini = { rate = 2.0, burst = 5 }
minimax = { rate = 2.0, burst = 5 }
kimi = { rate = 1.0, burst = 3 }
xai = { rate = 2.0, burst = 5 }

# Vector storage
[vector_storage]
backend = "zvec