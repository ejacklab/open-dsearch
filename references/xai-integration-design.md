# xAI Integration Design & Architecture

## Overview
This document outlines the architectural design and integration plan for adding **xAI (Grok) Web Search** and **xAI X Search** into the CCLL (Comprehensive Continuous Learning Loop) research methodology.

The goal is to expand the existing research orchestration (which previously relied on Gemini and MiniMax) to also leverage the powerful reasoning and real-time social data access provided by xAI's `grok-4-1-fast-reasoning` model via the `xai_sdk`.

## Core Requirements
1.  **Multiple Search Frontends**: Support both standard web search (`web_search` tool) and X platform search (`x_search` tool) via the xAI API.
2.  **Concurrency (The "20 Queries" Rule)**: The system must fan out a single research topic into multiple (up to 20) specific sub-queries (e.g., "topic tutorial", "topic site:github.com") and execute them concurrently to maximize search diversity and speed.
3.  **Background Vector Storage**: As search results arrive, they must be immediately pushed to the background `zvec` storage using the existing `push_zvec.py` pipeline.
4.  **Graceful Fallbacks**: The xAI integration must be opt-in via the `XAI_API_KEY` environment variable and fail gracefully without interrupting Gemini or MiniMax searches.

## Architecture

The integration spans both Python (for SDK access) and Rust (for high-performance orchestration and concurrency).

### 1. Python Bridge (`xai_search.py`)
Because the official xAI SDK is written in Python, we created a bridge script that handles the direct API communication.
*   **Tools Used**: Imports `web_search` and `x_search` from `xai_sdk.tools`.
*   **Model**: Uses `grok-4-1-fast-reasoning`.
*   **Behavior**: Accepts a `--query` and an optional `--x-search` flag. It streams the chat response, extracts the `citations` metadata from the response object, formats them into a standard JSON array `[{"title": "...", "url": "...", "snippet": "..."}]`, and prints to stdout.

### 2. Rust Search Client (`search.rs` & `lib.rs`)
The Rust layer wraps the Python script to expose strongly-typed, asynchronous search functions.
*   **`search_xai(query, limit)`**: Spawns a blocking task that runs `python3 xai_search.py "query" --limit [limit]`. It parses the JSON output into `SearchResult` structs.
*   **`xai_x_search(query, limit)`**: Similar to the above, but appends the `--x-search` flag to trigger the X platform search.
*   **Fallback Logic**: The `search_with_fallback` function (used for single queries) was updated to attempt both xAI web and X searches concurrently (via `tokio::time::timeout` and `tokio::join!`) if the `XAI_API_KEY` is present.

### 3. Orchestration & Concurrency (`research.rs`)
The primary research pipeline leverages `tokio` to execute massive concurrent searches. The architecture mirrors the existing Gemini and MiniMax implementations:

*   **Query Expansion**: The user's root topic is expanded via `expand_queries_with_sources` into ~20 diverse queries (covering Google-style basics, GitHub repositories, and official documentation).
*   **Phase 2c (xAI Web Search)**:
    *   Iterates over the 20 expanded queries.
    *   Maps each query to a `search_xai` future.
    *   Uses `futures::future::join_all` to execute all 20 web searches simultaneously.
    *   Upon completion, iterates over the results and spawns a non-blocking `push_zvec.py` process for each citation.
*   **Phase 2d (xAI X Search)**:
    *   Iterates over the same 20 expanded queries.
    *   Maps each query to an `xai_x_search` future.
    *   Uses `join_all` to execute all 20 X platform searches simultaneously.
    *   Pushes results to `zvec`.

## Execution Flow Diagram

```mermaid
graph TD
    A[User Topic: 'Rust Macros'] --> B(expand_queries)
    B --> C['Rust Macros basics', 'Rust Macros github', ...] (20 Queries)
    
    C -->|join_all| D(Phase 2a: Gemini)
    C -->|join_all| E(Phase 2b: MiniMax)
    C -->|join_all| F(Phase 2c: xAI Web)
    C -->|join_all| G(Phase 2d: xAI X Search)
    
    F -->|Spawn Python| H[xai_search.py]
    G -->|Spawn Python| I[xai_search.py --x-search]
    
    H -->|Extract Citations| J[JSON Results]
    I -->|Extract Citations| J
    
    J -->|spawn| K(push_zvec.py)
    K --> L[(zvec Vector DB)]
```

## Setup & Configuration
Users must export the API key to enable this pipeline:
```bash
export XAI_API_KEY=your_xai_api_key
```
If the key is missing, Phases 2c and 2d are safely skipped.
