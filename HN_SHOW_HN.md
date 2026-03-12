# Hacker News - Show HN

## Title
**Show HN: I built a multi-provider deep research tool (80+ sources in 2.8s)**

## Body

Hi HN!

I built **open-dsearch** after getting frustrated with shallow AI search results.

---

### The Problem

Perplexity, ChatGPT search, etc. - they give you 5-10 sources max. For technical research, that's often not enough. I kept finding that crucial papers/threads/articles were missing from these shallow searches.

---

### The Solution

**open-dsearch** is a deep research tool that:

1. **Multi-provider search** - Gemini, MiniMax, xAI/Grok simultaneously
2. **Query expansion** - 20 variations per provider (industry terms, different angles)
3. **Parallel execution** - Rust + tokio for 80 concurrent requests
4. **Ranked results** - Relevance scoring and deduplication
5. **Optional synthesis** - Full research reports or raw JSON

**Result: 80+ sources in ~2.8 seconds**

---

### Architecture

```
Research Query
     ↓
  Rust Engine (tokio async)
     ↓
  20 queries × 3 providers = 60 parallel HTTP requests
     ↓
  Rank → Fetch → Synthesize
     ↓
  Markdown report / JSON / Vector DB
```

**Why Rust?** 2.8x faster than Python for concurrent HTTP bursts. No GIL, zero-cost async.

---

### Key Features

- **Multi-provider redundancy** - if one API is down, others work
- **X/Twitter search** - real-time discussions, not just web pages
- **Local deployment** - your API keys, your data
- **Claude Code skill** - works as a native research tool
- **Vector storage** - ZVec integration for downstream RAG

---

### Comparison

| | open-dsearch | Perplexity | ChatGPT |
|---|---|---|---|
| Sources | 80+ | 5-10 | 3-5 |
| Providers | 3 | 1 | 1 |
| Twitter/X | ✅ | ❌ | ❌ |
| Open Source | ✅ MIT | ❌ | ❌ |
| Local | ✅ | ❌ | ❌ |

---

### Tech Stack

- **Rust** - Core research engine (tokio, reqwest)
- **Python** - CLI wrappers, xAI bridge
- **ZVec** - Vector storage (optional)

---

### Use Cases

✅ AI/ML research (deep papers + discussions)
✅ Technical architecture research
✅ Competitive analysis (news + forums)
✅ Building knowledge bases for RAG

---

### Links

**GitHub:** https://github.com/ejacklab/open-dsearch

**Example output:** See `examples/research-ai-agents.md` in repo

---

### Why I Built This

I work on AI agents (building OpenClaw) and needed **real research capability**. Not just quick answers, but comprehensive source gathering that I can trust.

---

### What's Next

- Adding Perplexity API as 4th provider
- Web UI for non-terminal users
- Better ranking models

---

**Questions / feedback / contributions welcome!**

Trying to hit 10 GitHub stars this week. Every star helps! ⭐

---

**Tech details:** ADRs (Architecture Decision Records) in repo explain why Rust, why multi-provider, etc.

---

*Built in Rust + Python, MIT licensed, active development.*
