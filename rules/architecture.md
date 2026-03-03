---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
related_modules: [research, search, fetch, rank, synthesize]
---

# Architecture Rules

## Module Layer Model

Strict dependency direction — lower layers must not import higher:

```
Layer 4: CLI entry points   scripts/research.py, scripts/synthesize.py
Layer 3: Orchestration      scripts/rust/src/research.rs
Layer 2: Operations         scripts/rust/src/search.rs, fetch.rs, rank.rs
Layer 1: Primitives         scripts/rust/src/lib.rs
```

`search.rs` / `fetch.rs` / `rank.rs` must NOT call orchestration logic.
`research.rs` owns sequencing — calls down only, never sideways.

## Data Flow

```
User query
  → expand_queries() [search.rs]    → 20 query variants
  → tokio::join! [research.rs]:
      Phase 1:  Gemini (20 queries)
      Phase 2a: MiniMax (20 queries)
      Phase 2b: xAI web search (20 queries)
      Phase 2c: xAI X search (20 queries)
  → score_and_rank() [rank.rs]      → top N results
  → fetch_url() × N [fetch.rs]      → HTML → markdown
  → Output: vectors | json | md
```

## Python-Rust Bridge Rule

xAI SDK is Python-only. Rust calls Python via `spawn_blocking`.
All Python bridge scripts live in `scripts/`. No Python logic inside `scripts/rust/src/`.

## Output Naming Convention

`{topic_slug}_{suffix}.{ext}`
- Raw results:    `{slug}_raw.json`
- Vectors:        `{slug}_vectors.jsonl`
- Fetched report: `{slug}_fetched.md`
