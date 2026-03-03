---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 90d
---

# ADR-002: xAI via Python Bridge

## Context

The xAI SDK (for Grok web search and X/Twitter search) is Python-only. The core engine
is Rust. These need to interoperate.

## Decision

`research.rs` calls `xai_search.py` via `tokio::task::spawn_blocking`. The Python
process handles all xAI SDK interaction and returns JSON to Rust.

## Why

- Avoids maintaining an unofficial Rust HTTP client for xAI
- xAI SDK handles streaming, tool use, and citation extraction — re-implementing is
  high cost and high maintenance
- Bridge is isolated: changes to xAI API only touch `xai_search.py`, not the Rust core
- `spawn_blocking` integrates cleanly with tokio's async runtime

## Why NOT rewrite xAI in Rust

No official xAI Rust SDK. Reverse-engineering the streaming API protocol is fragile
and would break on any SDK update.

## When to Revisit

If an official xAI Rust SDK ships, migrate to eliminate the Python subprocess overhead.
