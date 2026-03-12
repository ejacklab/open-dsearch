# I Built a Deep Research Tool for AI Agents (80+ Sources in 2.8 Seconds)

*Why I stopped settling for 5-10 sources and built something better*

---

If you've ever used Perplexity, ChatGPT search, or any AI-powered search tool, you've probably noticed something frustrating: **they only give you 5–10 sources.**

For quick answers? Fine.

For deep research? Not even close.

I kept hitting this wall while working on AI agents. I'd ask about "multi-agent memory architectures" and get 5-10 papers, missing crucial discussions from Twitter/X, forum posts, or niche blogs.

So I built **open-dsearch** — a multi-provider deep research tool that runs **80+ concurrent queries** across **3 AI providers** in **2.8 seconds**.

And it's open source.

---

## The Problem: Shallow AI Search

Here's what happens when you search with existing tools:

**Perplexity:** 5–10 sources
**ChatGPT Search:** 3–5 sources
**Gemini Search:** 5–10 sources

That's **surface-level research**.

When I was researching AI agent architectures, I kept finding that crucial papers, GitHub discussions, and Twitter threads were missing. The algorithm would show me the top 5 results, but miss the nuance.

**Real research needs more sources.**

---

## The Solution: Multi-Provider Deep Search

**open-dsearch** takes a different approach:

1. **Multi-provider**: Gemini + MiniMax + xAI/Grok simultaneously
2. **Query expansion**: 20 variations per provider (industry terminology, different angles)
3. **Parallel execution**: 80 concurrent HTTP requests in Rust
4. **Ranked synthesis**: Deduplicated, relevance-scored results

**Result: 80+ sources in ~2.8 seconds**

---

## How It Works

### Architecture Overview

```
Research Query
     ↓
  Rust Engine (tokio async)
     ↓
  20 queries × Gemini     ┐
  20 queries × MiniMax    ├─→ 60+ parallel requests
  20 queries × xAI Web    │
  20 queries × xAI Twitter┘
     ↓
  Rank → Fetch → Synthesize
     ↓
  Markdown report / JSON / Vector DB
```

### Key Components

**1. Rust Core Engine**

Why Rust? **2.8x faster** than Python for concurrent HTTP bursts.

```rust
// From scripts/rust/src/main.rs
async fn execute_research(query: &str, providers: Vec<Provider>) -> Result<Vec<Source>> {
    let mut tasks = Vec::new();
    
    // Spawn 80 concurrent requests
    for provider in providers {
        for variant in generate_query_variants(query, 20) {
            tasks.spawn(async {
                provider.search(&variant).await
            });
        }
    }
    
    // Collect and rank results
    let results = futures::future::join_all(tasks).await;
    rank_and_deduplicate(results)
}
```

**2. Query Expansion**

We don't just search your exact query. We generate **20 variations** using industry terminology:

```
Query: "AI agent architectures"

Variations:
- "multi-agent systems 2026"
- "hierarchical AI agents"
- "orchestrator-worker pattern agents"
- "agent memory persistence patterns"
- ... (16 more)
```

This ensures we catch results that use different terminology.

**3. Multi-Provider Redundancy**

Three providers means:
- **No single point of failure**
- **Complementary coverage** (Gemini for comprehensive, MiniMax for coding, xAI for real-time)
- **X/Twitter search** (discussions, not just web pages)

---

## Performance Comparison

| Feature | open-dsearch | Perplexity | ChatGPT Search |
|---------|--------------|------------|----------------|
| **Sources per query** | 80+ | 5-10 | 3-5 |
| **Search providers** | 3 | 1 | 1 |
| **X/Twitter search** | ✅ | ❌ | ❌ |
| **Query expansion** | ✅ (20 variants) | ❌ | ❌ |
| **Local deployment** | ✅ | ❌ | ❌ |
| **Open source** | ✅ MIT | ❌ | ❌ |
| **Speed** | ~2.8s (Rust) | ~3s | ~4s |

---

## Use Cases

### 1. AI/ML Research

```bash
python scripts/research.py "multi-agent memory architectures 2026" --mode md

# Output: 80+ sources including papers, GitHub repos, Twitter discussions
```

### 2. Technical Architecture Research

```bash
python scripts/research.py "distributed systems patterns for AI" --mode vectors

# Output: Pushes to ZVec for RAG applications
```

### 3. Building Knowledge Bases

The vector output mode (`--mode vectors`) stores results in ZVec, making them queryable by LLMs later.

---

## Real Example Output

Here's an actual research output from open-dsearch:

**Query:** "AI agent architectures 2026"

**Sources found:** 84

**Top findings:**

1. **Hierarchical Agent Systems** — Orchestrator agents coordinating specialist agents (Anthropic research)
2. **Memory Persistence** — Vector databases + state.md pattern for session continuity
3. **Tool-Using Agents** — MCP (Model Context Protocol) as first-class citizen
4. **Multi-Model Ensembles** — Routing queries to specialized models

*Full example in the repo: `examples/research-ai-agents.md`*

---

## Why I Built This

I work on **OpenClaw** — an AI agent platform — and I kept running into the same problem:

**My agents couldn't do real research.**

They'd search for something and get 5-10 shallow results. I needed 80+ sources to synthesize from.

So I built what I wished existed.

---

## Technical Deep Dive

### Why Rust (Not Python)?

**Performance benchmarks:**

```
Rust (tokio):    ~0.13s average per phase
Python (async):  ~0.37s average per phase
Speedup:         2.8x faster
```

For 80 concurrent HTTP requests, Rust's zero-cost async makes a difference.

### Why Multi-Provider?

APIs go down. Rate limits happen. Search quality varies.

With 3 providers:
- If Gemini is down → MiniMax + xAI still work
- If one misses something → others catch it
- Different providers = different indexing

### Why X/Twitter Search?

Because **discussions happen on X**.

Academic papers are great, but half the AI breakthroughs in 2026 were discussed on Twitter first. open-dsearch includes X/Twitter search via xAI/Grok to catch real-time conversations.

---

## Getting Started

### Installation

```bash
# Clone
git clone https://github.com/ejacklab/open-dsearch
cd open-dsearch

# Build Rust core
cd scripts/rust
cargo build --release

# Run research
cd ../..
python3 scripts/research.py "your research topic" --mode md --top 10
```

### Claude Code Integration

open-dsearch works as a Claude Code skill:

```bash
# Add to Claude Code
cp -r skills/dsearch ~/.claude/skills/
```

Then in Claude Code:

```
"Research multi-agent memory architectures using open-dsearch"
```

Claude will activate the skill and return 80+ synthesized sources.

---

## Architecture Decision Records (ADRs)

The repo includes full ADRs explaining every major decision:

- **ADR-001:** Why Rust core (concurrency + speed)
- **ADR-002:** Why Python bridge for xAI (SDK availability)
- **ADR-003:** Why multi-provider (redundancy + coverage)
- **ADR-004:** Why ZVec for vectors (no infrastructure)
- **ADR-005:** Domain blocklist (filtering low-quality sources)

---

## Open Source (MIT)

**GitHub:** https://github.com/ejacklab/open-dsearch

**License:** MIT (do whatever you want)

**Status:** Active development

---

## What's Next

- **Perplexity API** integration (4th provider)
- **Web UI** for non-terminal users
- **Better ranking models** (ML-based relevance scoring)

---

## Try It Yourself

1. Clone the repo
2. Add your API keys (Gemini, MiniMax, xAI)
3. Run your first deep research query
4. Get 80+ sources in ~3 seconds

```bash
git clone https://github.com/ejacklab/open-dsearch
cd open-dsearch
python3 scripts/research.py "AI agents 2026" --mode md
```

---

## Call to Action

If this sounds useful:

1. ⭐ **Star the repo** — helps with visibility
2. 🐛 **Report issues** — I'm actively developing
3. 🔀 **Contribute** — PRs welcome

**Goal:** Hit 10 stars this week! 🚀

---

## Final Thoughts

AI search is getting better, but it's still shallow. **5-10 sources isn't research — it's a preview.**

I built open-dsearch because I needed **real research capability** for my AI agents. Now I'm sharing it with you.

Try it out. Break it. Improve it.

And if you find it useful, drop a star. It helps more than you'd think.

---

**GitHub:** https://github.com/ejacklab/open-dsearch

**Questions?** Find me on Medium or open a GitHub issue.

---

*Built with Claude's assistance. The irony of using AI to build an AI research tool is not lost on me. 😄*
