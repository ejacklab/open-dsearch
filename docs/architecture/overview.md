---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Architecture Overview

## What It Is

open-dsearch is a deep research skill for AI agent terminals (Claude Code, Gemini CLI,
Qwen CLI, OpenCode, and others). It replaces the shallow default search — which issues
a single query and returns a handful of results — with a deep pipeline: multiple providers,
20 concurrent query variants, ranked web fetching, and optional synthesis into a report.

Developed at `/home/wnej/dev/open-dsearch`. Deployed as a skill to `~/.agents/skills/dsearch/`.

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| Core engine | Rust + tokio | Async concurrency for parallel multi-provider search |
| CLI wrapper | Python 3 | Ease of use; required for xAI SDK (Python-only) |
| Search: Gemini | Gemini API (REST) | Free tier (1000 req/day), good web coverage |
| Search: MiniMax | MiniMax API (REST) | Paid; complementary result coverage |
| Search: xAI/Grok | xAI SDK (Python) | Web search + X/Twitter corpus access |
| Ranking | Custom Rust (`rank.rs`) | Domain-quality scoring, blocked domain filter |
| Vector storage | zvec (optional) | LLM synthesis without extra infrastructure |

## System Diagram

```
Agent terminal (any: Claude Code, Gemini CLI, Qwen CLI, OpenCode...)
    ↓ invokes
scripts/research.py (Python CLI)
    ↓
research binary (Rust, tokio)
    ↓
expand_queries() → 20 variants
    ↓ tokio::join! (all phases concurrent)
┌─────────────┬───────────────┬────────────────┬──────────────┐
│ Gemini 20q  │ MiniMax 20q   │ xAI web 20q    │ xAI X 20q    │
└─────────────┴───────────────┴────────────────┴──────────────┘
    ↓ merge + score_and_rank() → top N
    ↓ fetch_url() × N (concurrent) → HTML → markdown
    ↓
Output: json | md | vectors → zvec
```

## Module Responsibilities

| Module | Owns | Does NOT own |
|---|---|---|
| `research.rs` | Orchestration, phase sequencing, output formatting | Search logic, fetch logic |
| `search.rs` | All provider API calls, query expansion, LLM synthesis | Fetching, ranking, file I/O |
| `fetch.rs` | HTTP GET, HTML→markdown, title extraction | Search, ranking |
| `rank.rs` | URL scoring, domain classification, top-N selection | Fetching, search |
| `research.py` | CLI arg parsing, binary invocation | Any business logic |
| `xai_search.py` | xAI SDK bridge, X search, citation extraction | Other provider searches |

Full module detail → `docs/architecture/modules.md`
xAI design rationale → `references/xai-integration-design.md`
