# open-dsearch - Quick Start Guide

## ⚠️ API Keys Required

**You must provide your own API keys.** At least one is required:

- **Gemini** (FREE: 1000 requests/day) - Recommended for testing
- **MiniMax** (Paid)
- **Kimi/Moonshot** (Paid)
- **xAI/Grok** (Paid)

**Get your keys:**
- **Gemini (FREE)**: https://aistudio.google.com/app/apikey
- **MiniMax**: https://www.minimax.io
- **Kimi**: https://platform.moonshot.cn
- **xAI**: https://console.x.ai

---

## 🚀 Installation

### Prerequisites

- **Rust** (latest stable): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Python 3.8+**: `python3 --version`
- **API Keys** (at least one):
  - Gemini (free: 1000 requests/day)
  - MiniMax (paid)
  - Kimi/Moonshot (paid)
  - xAI/Grok (paid)

### Step 1: Clone & Build

```bash
# Clone
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch

# Build Rust core
cd scripts/rust
cargo build --release
cd ../..
```

### Step 2: Set API Keys

Create `.env` file in project root:

```bash
# Copy example
cp .env.example .env

# Edit with your keys
nano .env
```

**Required format:**
```bash
GEMINI_API_KEY=your_gemini_key_here
MINIMAX_API_KEY=your_minimax_key_here
KIMI_API_KEY=your_kimi_key_here
XAI_API_KEY=your_xai_key_here
```

**Get API Keys:**
- **Gemini**: https://aistudio.google.com/app/apikey (FREE)
- **MiniMax**: https://www.minimax.io (Paid)
- **Kimi**: https://platform.moonshot.cn (Paid)
- **xAI**: https://console.x.ai (Paid)

### Step 3: Test It

```bash
# Quick test with Gemini (free tier)
python3 scripts/research.py "AI agents 2026" --mode md --top 5

# Should see:
# 🔬 CCLL Autonomous Research Pipeline
# Phase: Gemini (1 queries)...
#   Gemini found X results
# Research: AI agents 2026
# Time: 2.8s
```

---

## 📖 Usage

### Basic Research

```bash
# Markdown report (default)
python3 scripts/research.py "your topic" --mode md

# JSON output (for programs)
python3 scripts/research.py "your topic" --mode json

# Vector storage (for RAG)
python3 scripts/research.py "your topic" --mode vectors
```

### Advanced Options

```bash
# More sources
python3 scripts/research.py "topic" --top 20 --queries 10

# Specific URLs (skip search)
python3 scripts/research.py "topic" --urls "https://example.com/article"

# Custom timeout
python3 scripts/research.py "topic" --timeout 600
```

### Output Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `md` | Markdown report | Human reading |
| `json` | Raw JSON data | Programmatic use |
| `vectors` | Push to ZVec | RAG/LLM queries |

---

## 🔧 Configuration

### Environment Variables

```bash
# API Keys
GEMINI_API_KEY=xxx
MINIMAX_API_KEY=xxx
KIMI_API_KEY=xxx
XAI_API_KEY=xxx

# Optional: Custom API hosts
MINIMAX_API_HOST=https://api.minimax.io
KIMI_API_HOST=https://api.moonshot.ai
```

### CLI Arguments

```bash
python3 scripts/research.py --help

Arguments:
  topic              Research topic
  --top, -n         Number of sources (default: 5)
  --queries, -q     Number of queries (default: 5)
  --mode, -m        Output: vectors, json, md (default: vectors)
  --output, -o      Output file path
  --timeout, -t     Timeout in seconds (default: 300)
  --urls, -u        Direct URLs (skip search)
```

---

## 🐛 Troubleshooting

### "Rust binary not found"

```bash
cd scripts/rust
cargo build --release
```

### "API key not found"

Check `.env` file exists and has correct keys:
```bash
cat .env | grep API_KEY
```

### "No results from Gemini"

- Check API key is valid
- Check you haven't hit rate limits (1000/day for free tier)
- Try a different query

### Slow performance

- Reduce `--queries` (default: 5)
- Reduce `--top` (default: 5)
- Check network connection

---

## 📚 Examples

### Research AI Agents

```bash
python3 scripts/research.py "multi-agent memory architectures 2026" --mode md --top 10
```

### Research for RAG

```bash
python3 scripts/research.py "vector databases comparison" --mode vectors
```

### Save to File

```bash
python3 scripts/research.py "rust async patterns" --mode md --output research.md
```

---

## 🤝 Support

- **Issues**: https://github.com/ejacklab/open-dsearch/issues
- **Docs**: See `docs/` folder
- **Examples**: See `examples/` folder

---

## 📄 License

MIT - Use freely, contribute back if you find it useful!

---

**Quick Start Checklist:**
- [ ] Install Rust
- [ ] Clone repo
- [ ] Build with `cargo build --release`
- [ ] Get Gemini API key (free)
- [ ] Create `.env` file
- [ ] Run first research query
- [ ] Star the repo! ⭐
