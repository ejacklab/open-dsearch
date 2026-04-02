# Open Dsearch - Quick Start Guide

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

Get up and running with Open Dsearch in 5 minutes.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Research Query](#first-research-query)
5. [Output Modes](#output-modes)
6. [API Server](#api-server)
7. [Next Steps](#next-steps)

---

## Prerequisites

### Required

- **Rust** (latest stable) - for the core search engine
- **Python 3.8+** - for CLI and API server
- **At least one API key** - we recommend Gemini (free)

### Check Your System

```bash
# Check Python
python3 --version  # Should be 3.8 or higher

# Check Rust (will install if missing)
rustc --version    # Should be 1.75 or higher
```

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch
```

### Step 2: Build the Rust Core

```bash
cd scripts/rust
cargo build --release
cd ../..
```

**Expected output:**
```
Compiling research v0.1.0
Finished release [optimized] target(s) in 45s
```

> **Note:** First build takes ~1-2 minutes. Subsequent builds are faster.

### Step 3: Verify Installation

```bash
# Check Rust binary
ls scripts/rust/target/release/research

# Should output: scripts/rust/target/release/research
```

---

## Configuration

### Step 1: Get API Keys

#### Option A: Gemini (Recommended - Free)

1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Copy your key

#### Option B: Other Providers (Paid)

- **MiniMax:** https://www.minimax.io
- **Kimi:** https://platform.moonshot.cn
- **xAI:** https://console.x.ai

### Step 2: Set Environment Variables

```bash
# Temporary (current session only)
export GEMINI_API_KEY="your-key-here"

# Or create .env file
echo "GEMINI_API_KEY=your-key-here" > .env
source .env
```

### Step 3: Verify Configuration

```bash
# Test API key
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"

# Should return list of available models
```

---

## First Research Query

### Basic Usage

```bash
# Simple research query
python3 scripts/research.py "AI agents 2026"
```

**Expected output:**
```
🔬 Open Dsearch Research Pipeline
═══════════════════════════════════

Topic: AI agents 2026
Mode: vectors
Providers: gemini, minimax, kimi, xai

Phase 1: Gemini (5 queries)...
  ✓ Gemini: 12 results

Phase 2: MiniMax (5 queries)...
  ✓ MiniMax: 8 results

Phase 3: xAI Web (5 queries)...
  ✓ xAI Web: 10 results

Phase 4: xAI X (5 queries)...
  ✓ xAI X: 7 results

Merging and ranking...
  Total unique sources: 37
  Top 5 selected

Fetching content...
  ✓ Fetched 5/5 sources

Pushing to ZVec...
  ✓ Indexed 5 vectors

═══════════════════════════════════
Research complete!
Time: 2.8s
```

### Save Output to File

```bash
# Markdown report
python3 scripts/research.py "Rust async patterns" --mode md --output report.md

# JSON data
python3 scripts/research.py "vector databases" --mode json --output data.json
```

---

## Output Modes

### 1. Vectors Mode (Default)

Best for: RAG pipelines, LLM context, semantic search

```bash
python3 scripts/research.py "machine learning" --mode vectors
```

**What it does:**
- Searches across all providers
- Generates embeddings for each result
- Stores in ZVec vector database
- Enables semantic search

**Output:**
- Console: Progress indicators
- Storage: Vectors in `./zvec_data/`

### 2. JSON Mode

Best for: Data processing, programmatic use

```bash
python3 scripts/research.py "API design" --mode json
```

**What it does:**
- Returns structured JSON data
- Includes metadata (source, score, URL)
- Easy to parse programmatically

**Output Example:**
```json
[
  {
    "title": "REST API Design Best Practices",
    "url": "https://example.com/api-design",
    "snippet": "...",
    "source": "gemini",
    "score": 0.95
  }
]
```

### 3. Markdown Mode

Best for: Human reading, reports

```bash
python3 scripts/research.py "Kubernetes" --mode md
```

**What it does:**
- Generates formatted markdown report
- Includes summaries and source links
- Ready to read or share

**Output Example:**
```markdown
# Research: Kubernetes

## Summary
Kubernetes is an open-source container orchestration platform...

## Sources

### [Kubernetes Documentation](https://kubernetes.io/docs/)
Official documentation for Kubernetes...
```

---

## API Server

### Start the Server

```bash
cd scripts
uvicorn api_server:app --reload --port 8000
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Research query
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI agents", "top": 5, "mode": "md"}'
```

### Interactive Documentation

Visit: http://localhost:8000/docs

Features:
- Interactive API testing
- Request/response schemas
- Auto-generated docs

---

## Common Options

### CLI Arguments

```bash
python3 scripts/research.py "topic" \
  --top 10 \        # Number of sources (1-50)
  --queries 10 \    # Query variations (1-20)
  --mode md \       # Output: vectors, json, md
  --timeout 600 \   # Timeout in seconds
  --output file.md  # Output file
```

### Examples

```bash
# Quick search (fewer sources)
python3 scripts/research.py "topic" --top 3 --queries 3

# Deep research (more sources)
python3 scripts/research.py "topic" --top 20 --queries 10

# Research with direct URLs
python3 scripts/research.py "topic" --urls "https://example.com/article"
```

---

## Troubleshooting

### "Rust binary not found"

```bash
# Rebuild Rust binary
cd scripts/rust
cargo build --release
cd ../..
```

### "API key not found"

```bash
# Check environment
echo $GEMINI_API_KEY

# Set if missing
export GEMINI_API_KEY="your-key"
```

### "No results"

- Check API key is valid
- Try a broader query
- Check network connection

### "Slow performance"

```bash
# Reduce query count
python3 scripts/research.py "topic" --queries 3 --top 3
```

---

## Next Steps

### Documentation

- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Usage Examples](USAGE_EXAMPLES.md) - Detailed examples
- [Configuration Guide](CONFIGURATION.md) - Advanced configuration
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
- [Architecture](ARCHITECTURE.md) - System design

### Integration

- **Python SDK:** `pip install open-dsearch` (coming soon)
- **REST API:** Use http://localhost:8000
- **Claude Code:** Use the built-in skill

### Community

- GitHub: https://github.com/ejacklab/open-dsearch
- Issues: https://github.com/ejacklab/open-dsearch/issues

---

## Quick Reference Card

```bash
# Install & Build
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch
cd scripts/rust && cargo build --release && cd ../..

# Configure
export GEMINI_API_KEY="your-key"

# Research
python3 scripts/research.py "topic" --mode md

# API Server
cd scripts && uvicorn api_server:app --port 8000
```

---

**You're all set!** Start researching with Open Dsearch. 🚀
