# xAI Integration Architecture - Visual Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CCLL RESEARCH METHODOLOGY                            │
│              Comprehensive Continuous Learning Loop                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   User Topic    │
│ "Rust Macros"   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Query Expansion (expand_queries_with_sources)                  │
│ - Generates ~20 diverse search queries                                   │
│ - 8 Google-style queries                                                 │
│ - 6 GitHub queries                                                       │
│ - 6 Official source queries                                              │
└────────┬────────────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────────────────────────────┐
         │                                                                 │
         ▼                                                                 ▼
┌──────────────────┐                                          ┌──────────────────┐
│ Phase 2a: Gemini │                                          │ Phase 2b: MiniMax│
│  (20 queries)    │                                          │  (20 queries)    │
└────────┬─────────┘                                          └────────┬─────────┘
         │                                                           │
         │                                                           │
         ▼                                                           ▼
┌──────────────────┐                                          ┌──────────────────┐
│ Phase 2c: xAI    │                                          │ Phase 2d: xAI    │
│ Web Search       │                                          │ X Search         │
│  (20 queries)    │                                          │  (20 queries)    │
└────────┬─────────┘                                          └────────┬─────────┘
         │                                                           │
         └───────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ Background: push_zvec   │
                        │ (Vector DB Storage)     │
                        └─────────────────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ Phase 3: Synthesis      │
                        │ (LLM Report Generation) │
                        └─────────────────────────┘
```

## xAI Integration Architecture

### Component Breakdown

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      xAI (Grok) Integration                              │
│                   grok-4-1-fast-reasoning Model                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PYTHON LAYER (xai_search.py) - xAI SDK Bridge                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ search_xai(query, limit, use_x_search)                            │  │
│  │                                                                   │  │
│  │  1. Load XAI_API_KEY from env                                     │  │
│  │  2. Create xAI Client                                             │  │
│  │  3. Select tool: web_search() or x_search()                       │  │
│  │  4. Create chat with grok-4-1-fast-reasoning                      │  │
│  │  5. Stream response with citations                                │  │
│  │  6. Extract citations → JSON [{title, url, snippet}]              │  │
│  │  7. Print to stdout                                               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Tools:                                                                  │
│  - web_search(): Standard web search                                     │
│  - x_search(): X platform social search                                  │
│                                                                          │
│  Output Format:                                                          │
│  [{"title": "...", "url": "...", "snippet": "..."}]                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ (stdout JSON)
                                     │
┌────────────────────────────────────┼─────────────────────────────────────┐
│         RUST LAYER (search.rs)     │                                     │
├────────────────────────────────────┼─────────────────────────────────────┤
│                                    │                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────┐  │
│  │ search_xai(query, limit)        │                                  │  │
│  │                                 │                                  │  │
│  │  1. Check XAI_API_KEY exists    │                                  │  │
│  │  2. Spawn blocking task         │                                  │  │
│  │  3. Execute: python3 xai_search.py <query> --limit <limit>         │  │
│  │  4. Parse stdout JSON           │                                  │  │
│  │  5. Return Vec<SearchResult>    │                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────┘  │
│                                    │                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────┐  │
│  │ xai_x_search(query, limit)      │                                  │  │
│  │                                 │                                  │  │
│  │  Same as above, but adds        │                                  │  │
│  │  --x-search flag                │                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────┘  │
│                                    │                                     │
│  ┌─────────────────────────────────┼──────────────────────────────────┐  │
│  │ search_with_fallback(...)       │                                  │  │
│  │                                 │                                  │  │
│  │  Concurrent fallback strategy:  │                                  │  │
│  │  - Try Gemini (if key set)      │                                  │  │
│  │  - Try MiniMax (if key set)     │                                  │  │
│  │  - Try xAI web (if key set)     │                                  │  │
│  │  - Try xAI X (if key set)       │                                  │  │
│  │  - Timeout: 66 minutes          │                                  │  │
│  └─────────────────────────────────┼──────────────────────────────────┘  │
│                                    │                                     │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│       ORCHESTRATION (research.rs) - Concurrent Execution                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 2c: xAI Web Search (20 queries)                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ for query in queries:                                             │  │
│  │   spawn(search_xai(query, 10))                                    │  │
│  │                                                                   │  │
│  │ join_all!(futures)  ← Execute all 20 concurrently                 │  │
│  │                                                                   │  │
│  │ for result in results:                                            │  │
│  │   spawn(push_zvec.py title url snippet topic)  ← Background      │  │
│  │   all_results.extend(result)                                      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Phase 2d: xAI X Search (20 queries)                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ for query in queries:                                             │  │
│  │   spawn(xai_x_search(query, 10))                                  │  │
│  │                                                                   │  │
│  │ join_all!(futures)  ← Execute all 20 concurrently                 │  │
│  │                                                                   │  │
│  │ for result in results:                                            │  │
│  │   spawn(push_zvec.py ...)  ← Background                          │  │
│  │   all_results.extend(result)                                      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Concurrency Model:                                                      │
│  - tokio::join! for parallel execution                                   │
│  - futures::future::join_all for batch processing                        │
│  - Non-blocking spawn for zvec pushes                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
User Request
    │
    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ research.rs (main)                                                   │
│ - Parse CLI args                                                     │
│ - Initialize reqwest::Client                                         │
│ - Expand queries (20 variations)                                     │
└──────────────────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────────────────────────────────────────────┐
    │                                                                  │
    ▼                                                                  ▼
┌──────────────────────┐                                  ┌──────────────────────┐
│ search_xai(query)    │                                  │ xai_x_search(query)  │
│ (Phase 2c)           │                                  │ (Phase 2d)           │
└──────────┬───────────┘                                  └──────────┬───────────┘
           │                                                         │
           │  tokio::task::spawn_blocking                            │
           │  python3 xai_search.py <query> --limit 10               │
           │                                                         │
           ▼                                                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ xai_search.py (Python Bridge)                                              │
│                                                                            │
│  1. Load XAI_API_KEY                                                       │
│  2. client = Client(api_key=api_key)                                       │
│  3. chat = client.chat.create(                                             │
│        model="grok-4-1-fast-reasoning",                                    │
│        tools=[web_search() OR x_search()],                                 │
│        include=["verbose_streaming"]                                       │
│     )                                                                      │
│  4. chat.append(user(f"Search for: {query}"))                              │
│  5. for response, chunk in chat.stream():                                  │
│        response_obj = response                                             │
│  6. Extract response_obj.citations                                         │
│  7. Format → JSON array                                                    │
│  8. print(json.dumps(results))                                             │
└────────────────────────────────────────────────────────────────────────────┘
           │                                                         │
           │  stdout: [{"title":"...", "url":"...", "snippet":"..."}]│
           │                                                         │
           ▼                                                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ search.rs (Rust Parser)                                                    │
│                                                                            │
│  let output = Command::new("python3")                                      │
│      .arg("xai_search.py")                                                 │
│      .arg(query)                                                           │
│      .arg("--limit").arg(limit.to_string())                                │
│      .output()                                                             │
│                                                                            │
│  let results: Vec<SearchResult> = serde_json::from_str(&stdout)            │
│                                                                            │
│  return Ok(results)                                                        │
└────────────────────────────────────────────────────────────────────────────┘
           │                                                         │
           │                                                         │
           ▼                                                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ research.rs (Result Processing)                                            │
│                                                                            │
│  for result in results:                                                    │
│      // Push to zvec in background (non-blocking)                          │
│      std::process::Command::new("python3")                                 │
│          .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &topic])    │
│          .spawn();                                                         │
│                                                                            │
│      all_results.extend(results)                                           │
└────────────────────────────────────────────────────────────────────────────┘
           │                                                         │
           └─────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ push_zvec.py (Vector Storage)                                              │
│                                                                            │
│  Option 1: zvec library (if available)                                     │
│      collection.insert([                                                   │
│          Doc(id=url, vectors={embedding}, payload={...})                   │
│      ])                                                                    │
│                                                                            │
│  Option 2: JSONL file fallback                                             │
│      {topic}_vectors.jsonl                                                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## API Integration Details

### xAI SDK Usage

```python
# xai_search.py - Core Integration
from xai_sdk import Client
from xai_sdk.tools import web_search, x_search

client = Client(api_key=os.getenv("XAI_API_KEY"))

# Web Search
chat = client.chat.create(
    model="grok-4-1-fast-reasoning",
    tools=[web_search()],  # Standard web search
    include=["verbose_streaming"],
)

# X Search
chat = client.chat.create(
    model="grok-4-1-fast-reasoning",
    tools=[x_search()],  # X platform search
    include=["verbose_streaming"],
)

# Stream and extract citations
for response, chunk in chat.stream():
    response_obj = response

# Citations structure:
# response_obj.citations = [
#     Citation(title="...", url="...", snippet="..."),
#     ...
# ]
```

### Environment Configuration

```bash
# Required for xAI integration
export XAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional (for other search providers)
export GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export MINIMAX_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export MINIMAX_API_HOST=https://api.minimax.io
```

## Execution Modes

```
┌─────────────────────────────────────────────────────────────────────┐
│ research.py / research (Rust binary)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Mode: "vectors" (DEFAULT)                                          │
│  ├─ Execute all 4 search phases (Gemini, MiniMax, xAI web, xAI X)  │
│  ├─ Push results to zvec in background                              │
│  ├─ Save index.json with URLs                                       │
│  └─ Fast, async, ideal for LLM synthesis                            │
│                                                                     │
│  Mode: "json"                                                       │
│  ├─ Execute all search phases                                       │
│  ├─ Save raw results to {topic}_raw.json                            │
│  └─ No zvec, no fetching                                            │
│                                                                     │
│  Mode: "md"                                                         │
│  ├─ Execute all search phases                                       │
│  ├─ Save raw results to JSON                                        │
│  ├─ Rank & deduplicate results                                      │
│  ├─ Fetch top N pages (web scraping)                                │
│  ├─ Synthesize with LLM (Gemini/MiniMax)                            │
│  └─ Generate full markdown report                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────────────┐
│ Concurrent Execution Strategy                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Total Queries: ~20 (expand_queries_with_sources)                   │
│                                                                     │
│  Phase 2a: Gemini (20 queries)                                      │
│    ├─ 20 concurrent futures (join_all)                              │
│    ├─ Each: search_gemini(query, 10)                                │
│    └─ Results: ~200 total                                           │
│                                                                     │
│  Phase 2b: MiniMax (20 queries)                                     │
│    ├─ 20 concurrent futures (join_all)                              │
│    ├─ Each: search_minimax(query, 10)                               │
│    └─ Results: ~200 total                                           │
│                                                                     │
│  Phase 2c: xAI Web (20 queries)                                     │
│    ├─ 20 concurrent futures (join_all)                              │
│    ├─ Each: search_xai(query, 10)                                   │
│    └─ Results: ~200 total                                           │
│                                                                     │
│  Phase 2d: xAI X (20 queries)                                       │
│    ├─ 20 concurrent futures (join_all)                              │
│    ├─ Each: xai_x_search(query, 10)                                 │
│    └─ Results: ~200 total                                           │
│                                                                     │
│  Total Potential Results: ~800                                      │
│  Actual Deduplicated: ~300-500                                      │
│                                                                     │
│  Time:                                                              │
│    ├─ Query expansion: <100ms                                       │
│    ├─ Each search phase: 5-15 seconds (concurrent)                  │
│    ├─ Total search time: ~20-40 seconds                             │
│    ├─ zvec push: background (non-blocking)                          │
│    └─ Full pipeline: ~1-2 minutes                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Error Handling & Fallbacks

```
┌─────────────────────────────────────────────────────────────────────┐
│ search_with_fallback(client, query, limit)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Check API Keys:                                                    │
│    ├─ GEMINI_API_KEY? → Try Gemini                                  │
│    ├─ MINIMAX_API_KEY? → Try MiniMax                                │
│    └─ XAI_API_KEY? → Try xAI (both web and X)                       │
│                                                                     │
│  Timeout Strategy:                                                  │
│    ├─ Each search: 66 minutes timeout                               │
│    ├─ tokio::time::timeout(duration, future)                        │
│    └─ If timeout → log error, continue                              │
│                                                                     │
│  Concurrent Execution:                                              │
│    ├─ tokio::join!(gemini_fut, minimax_fut)                         │
│    ├─ Collect all successful results                                │
│    └─ If all fail → return error                                    │
│                                                                     │
│  Graceful Degradation:                                              │
│    ├─ Missing key? → Skip that provider                             │
│    ├─ API error? → Log and continue                                 │
│    ├─ Empty results? → Try next provider                            │
│    └─ All fail? → Return "No results from any search API"           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
.agents/skills/dsearch/
├── references/
│   └── xai-integration-design.md  ← This design document
│
├── scripts/
│   ├── xai_search.py              ← Python bridge to xAI SDK
│   ├── test_xai.py                ← Test script for xAI
│   ├── test_xai_citations.py      ← Citation extraction test
│   ├── push_zvec.py               ← Vector storage handler
│   ├── research.py                ← Python wrapper for Rust binary
│   │
│   └── rust/
│       ├── Cargo.toml
│       ├── src/
│       │   ├── lib.rs             ← Public API exports
│       │   ├── search.rs          ← Search implementations (Gemini, MiniMax, xAI)
│       │   ├── research.rs        ← Main orchestration logic
│       │   ├── fetch.rs           ← Web scraping
│       │   ├── rank.rs            ← Result scoring & deduplication
│       │   └── synthesize.rs      ← LLM report generation
│       │
│       └── target/release/
│           └── research            ← Compiled binary
│
└── SKILL.md                       ← Usage documentation
```

## Key Design Decisions

1. **Python Bridge for xAI SDK**
   - xAI SDK is Python-only → created xai_search.py bridge
   - Returns standardized JSON for Rust parsing
   - Handles citation extraction and formatting

2. **Concurrent Execution**
   - All 20 queries per phase run in parallel (join_all)
   - Non-blocking zvec pushes (spawn background process)
   - Maximizes throughput and minimizes latency

3. **Graceful Fallbacks**
   - Each provider is optional (check env vars)
   - Failures don't stop the pipeline
   - Multiple providers = redundancy and diversity

4. **Background Vector Storage**
   - push_zvec.py runs as separate process
   - Doesn't block search execution
   - Enables async LLM synthesis later

5. **Standardized Output**
   - All search providers return Vec<SearchResult>
   - Uniform structure: {title, url, snippet}
   - Easy to merge and deduplicate

## Summary

The xAI integration adds two powerful search capabilities to the CCLL methodology:

1. **xAI Web Search**: Standard web search via grok-4-1-fast-reasoning
2. **xAI X Search**: Social platform search for real-time discussions

Both execute concurrently across 20 expanded queries, pushing results to vector storage in the background. The architecture is fault-tolerant, supports graceful fallbacks, and integrates seamlessly with existing Gemini and MiniMax pipelines.
