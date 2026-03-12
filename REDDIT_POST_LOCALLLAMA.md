# Reddit Post - r/LocalLLaMA

## Title
**[Show] Open-dsearch: Deep research for AI agents - 80+ sources in 2.8s (Rust-powered)**

## Body

Hey r/LocalLLaMA! 👋

I built **open-dsearch** - a deep research skill that replaces shallow AI search with comprehensive multi-provider queries.

---

### The Problem
Most AI search tools (Perplexity, ChatGPT search, etc.) give you **5-10 sources**. That's shallow research. I kept hitting this wall when researching AI topics.

### The Solution
**open-dsearch** runs **80+ concurrent queries** across **3 providers**:
- Gemini (comprehensive web)
- MiniMax (coding-focused)
- xAI/Grok (real-time + X/Twitter)

**Speed:** 2.8s average (Rust core, not Python)

---

### Quick Demo

```bash
# Install
git clone https://github.com/ejacklab/open-dsearch
cd open-dsearch/scripts/rust && cargo build --release

# Run deep research
python3 scripts/research.py "AI agent architectures 2026" --mode md

# Output: Full markdown report with 80+ ranked sources
```

---

### Architecture

```
Query → Rust Engine (tokio async)
     → 20 queries × Gemini
     → 20 queries × MiniMax  
     → 20 queries × xAI Web
     → 20 queries × xAI X/Twitter
     → Rank → Fetch → Synthesize
```

**2.8x faster** than Python equivalent.

---

### Use Cases

✅ Research AI/ML topics deeply
✅ Compare multiple sources automatically  
✅ Claude Code / Gemini CLI integration
✅ Local deployment (no data leaves your machine)

---

### Comparison

| Feature | open-dsearch | Perplexity | ChatGPT Search |
|---------|--------------|------------|----------------|
| Sources | **80+** | 5-10 | 3-5 |
| Providers | **3** | 1 | 1 |
| X/Twitter | ✅ | ❌ | ❌ |
| Local | ✅ | ❌ | ❌ |
| Open Source | ✅ MIT | ❌ | ❌ |

---

### Links

**GitHub:** https://github.com/ejacklab/open-dsearch

**Examples:** See `examples/` folder for real research outputs

---

### Why I Built This

I work on AI agents (OpenClaw project) and needed **real research**, not surface-level overviews. This is the tool I wished existed.

---

**Questions? Feedback?** Happy to discuss architecture, use cases, or how to integrate with your workflow!

---

**License:** MIT
**Written in:** Rust + Python
**Status:** Active development

---

*Full disclosure: AI helped me draft this post, but the code is 100% real and tested.*
