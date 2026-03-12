# Comparison: Open-Dsearch vs Other AI Search Tools

| Feature | Open-Dsearch | Perplexity | ChatGPT Search | Gemini Search |
|---------|--------------|------------|----------------|---------------|
| **Sources per query** | 80+ | 5-10 | 3-5 | 5-10 |
| **Search providers** | 3 (Gemini, MiniMax, xAI) | 1 | 1 | 1 |
| **X/Twitter search** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Vector storage** | ✅ ZVec | ❌ No | ❌ No | ❌ No |
| **Local deployment** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Claude Code integration** | ✅ Native | ❌ No | ❌ No | ❌ No |
| **CLI access** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Open source** | ✅ MIT | ❌ No | ❌ No | ❌ No |
| **Cost** | API keys only | $20/mo | $20/mo | Free tier |
| **Speed** | ~2s (Rust) | ~3s | ~4s | ~2s |

## Why Open-Dsearch?

### For Researchers
- **80+ sources** means you don't miss important papers
- **Multi-provider** = redundancy + complementary coverage
- **Vector storage** enables LLM synthesis without extra infrastructure

### For Developers
- **Claude Code skill** - works out of the box
- **Open source** - customize for your needs
- **CLI-first** - script it, automate it

### For Teams
- **Local deployment** - no data leaves your machine
- **Multiple AI terminals** - Claude, Gemini CLI, Qwen CLI
- **ZVec integration** - shared research knowledge base

---

## Quick Start

```bash
# Install
git clone https://github.com/ejacklab/open-dsearch
cd open-dsearch/scripts/rust && cargo build --release

# Run research
python3 scripts/research.py "AI agent architectures" --mode md --top 10

# Output: Full markdown report with 80+ sources
```

---

*Comparison made with open-dsearch*
