---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Tool Catalog

## research.py — Full Pipeline

**What:** Python CLI entry point for the complete deep research pipeline.
**Returns:** JSON / markdown report / vectors depending on `--mode`.
**Use when:** Running any research task end-to-end.
**Do NOT use for:** Quick single-URL fetch (use `web_fetch` binary directly).
**Limits:** 300s timeout default. API rate limits apply per provider.

```bash
python3 scripts/research.py "MCP protocol internals" --mode md      --top 8  --queries 5
python3 scripts/research.py "tokio async patterns"   --mode vectors --top 10 --queries 5
python3 scripts/research.py "xAI API rate limits"    --mode json    --top 5  --queries 3
```

## web_search binary — Single Provider Search

**What:** Standalone search against one provider, no fetch or rank pipeline.
**Returns:** Raw JSON search results.
**Use when:** Debugging a specific provider's output in isolation.

```bash
./scripts/rust/target/release/web_search "query" --provider gemini
./scripts/rust/target/release/web_search "query" --provider minimax
```

## web_fetch binary — Single URL Fetch

**What:** Fetch one URL, strip HTML, return markdown.
**Returns:** Markdown string with extracted title.
**Use when:** Inspecting a specific page manually.
**Limits:** Configurable `max_kb` truncation.

```bash
./scripts/rust/target/release/web_fetch "https://docs.rs/tokio"
```

## xai_search.py — xAI Bridge (direct)

**What:** Python bridge to xAI SDK. Web search and X/Twitter search.
**Returns:** List of `SearchResult` dataclasses (JSON to stdout).
**Use when:** Testing xAI integration in isolation, or when X/Twitter corpus is needed.

```bash
python3 scripts/xai_search.py "Rust async patterns"  --mode web
python3 scripts/xai_search.py "Claude MCP discussion" --mode x
```

## synthesize.py / synthesize binary — Report Generation

**What:** Reads saved findings directory, generates markdown synthesis report.
**Returns:** Markdown document to stdout or file.

```bash
python3 scripts/synthesize.py --title "MCP Deep Dive" --findings-dir ./findings/
```

## drift_scan.py — Harness Enforcement

**What:** Automated check of 7 golden principles. Read-only — never modifies files.
**Returns:** Exit 0 (clean) or Exit 1 (issues listed).
**Use when:** Before every commit. Non-negotiable.

```bash
python3 scripts/drift_scan.py
```

## test_xai.py / test_xai_citations.py — Connection Tests

**What:** Manual integration tests for xAI API connection and citation extraction.
**Use when:** After updating `XAI_API_KEY` or `xai_sdk` version.

```bash
python3 scripts/test_xai.py
python3 scripts/test_xai_citations.py
```
