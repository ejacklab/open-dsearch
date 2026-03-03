---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Module Reference

## Rust — `scripts/rust/src/`

### `research.rs` (336 lines) — Orchestrator
Entry point binary. Owns the full execution sequence.
- Parses CLI args via `clap`
- Runs all search phases concurrently with `tokio::join!`
- Calls `score_and_rank()` then `fetch_url()` per result
- Formats and writes output (json / md / vectors)
- Spawns zvec push as background task (non-blocking)
- **Must not** contain search logic or fetch logic

### `search.rs` (620 lines) — Search Engine
All provider integrations and query expansion.
- `search_gemini()` — Gemini REST API
- `search_minimax()` — MiniMax REST API
- `search_xai()` — calls Python bridge via `spawn_blocking`
- `xai_x_search()` — X/Twitter search via Python bridge
- `expand_queries()` — generates 20 query variants from one input
- `synthesize_with_llm()` — LLM synthesis call
- **Must not** call `fetch_url()` or `score_and_rank()`

### `fetch.rs` (64 lines) — Web Fetcher
Single-URL HTML fetch and conversion.
- `fetch_url()` async — reqwest GET with timeout
- Strips `<script>`, `<style>`, `<noscript>` tags
- Extracts `<title>` text
- Converts HTML to markdown via `html2md`
- Truncates to `max_kb` (configurable)
- Returns `FetchedPage { title, markdown }`

### `rank.rs` (153 lines) — Result Ranker
Scores and filters search results by source quality.
- `score_and_rank()` — takes raw results, returns top N `ScoredResult`
- `SourceType` enum: `Docs | Blog | GitHub | Paper | Forum`
- Blocked domains filter: reddit.com, twitter.com, x.com, medium.com
- Scoring weights by source type (Docs highest, Forum lowest)

### `web_search.rs` (243 lines) — Standalone Search Binary
CLI binary for single-provider search without the full pipeline.
Useful for debugging individual provider output.

### `web_fetch.rs` (65 lines) — Standalone Fetch Binary
CLI binary for fetching a single URL.

### `synthesize.rs` (81 lines) — Standalone Synthesis Binary
Reads a findings directory, generates a markdown report template.

### `lib.rs` — Library Exports
Exposes modules for use across binaries.

---

## Python — `scripts/`

### `research.py` (77 lines) — CLI Wrapper
Thin wrapper around the Rust `research` binary.
Parses user args, invokes binary, handles timeout (default 300s).
Contains no business logic.

### `synthesize.py` (124 lines) — Synthesis Wrapper
Tries Rust `synthesize` binary first, falls back to Python implementation.
Reads findings from directory, generates markdown report.

### `xai_search.py` (417 lines) — xAI SDK Bridge
Python-side of the Rust-Python bridge for xAI/Grok.
- Wraps xAI SDK for web search and X/Twitter search
- Handles streaming responses, citation extraction, domain filtering
- Returns standardised `SearchResult` dataclass list

### `push_zvec.py` (148 lines) — Vector Storage
Pushes search results to zvec (local vector database).
Called by `research.rs` via `spawn_blocking` as background task.

### `test_xai.py` / `test_xai_citations.py`
Manual integration test scripts for xAI connection and citation parsing.
Not automated — run manually to validate xAI setup.
