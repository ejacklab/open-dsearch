# Open Dsearch Architecture

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

System architecture, component diagrams, and design patterns.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Component Breakdown](#component-breakdown)
4. [Data Flow](#data-flow)
5. [Design Patterns](#design-patterns)
6. [Technology Stack](#technology-stack)
7. [Scalability](#scalability)

---

## System Overview

Open Dsearch is a multi-provider autonomous research pipeline built for AI agents. It performs deep research by querying multiple search providers simultaneously, fetching and ranking results, and outputting in multiple formats.

### Key Characteristics

- **Multi-Provider:** Uses 4 search providers (Gemini, MiniMax, Kimi, xAI)
- **Concurrent:** 80+ requests in ~2.8 seconds
- **Multi-Output:** Vectors, JSON, or Markdown
- **Hybrid:** Rust core for performance, Python for flexibility
- **Agent-First:** Built by agents, for agents

---

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    CLI       │  │  REST API    │  │ Claude Code  │  │   Python     │    │
│  │  research.py │  │   Server     │  │    Skill     │  │    SDK       │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          └─────────────────┴─────────────────┴─────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PYTHON LAYER (scripts/)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      research.py (Entry Point)                      │   │
│  │  • CLI argument parsing    • Input validation    • Binary dispatch  │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────────┐   │
│  │                  research_python.py (Fallback)                      │   │
│  │  • Pure-Python search      • Rate limiting       • Retry logic      │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────────┐   │
│  │                    Supporting Modules                               │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │  config.py │ │push_zvec.py│ │xai_search.py│ │web_fetch.py│       │   │
│  │  │ Config mgmt│ │Vector store│ │ xAI bridge │ │URL fetcher │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RUST CORE (scripts/rust/)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        research.rs (Orchestrator)                   │   │
│  │  • Phase coordination      • Concurrent execution  • Output format  │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│  ┌──────────────────┬─────────────┼─────────────┬──────────────────────┐   │
│  │                  │             │             │                      │   │
│  ▼                  ▼             ▼             ▼                      │   │
│┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
││ search.rs│  │ fetch.rs │  │ rank.rs  │  │synthesize│  │ push_zvec│   │   │
││  Search  │  │   Fetch  │  │   Rank   │  │  Report  │  │  (spawn) │   │   │
│└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
└────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│    SEARCH APIs      │ │   VECTOR STORAGE    │ │   OUTPUT FORMATS    │
│                     │ │                     │ │                     │
│ ┌───────┬─────────┐ │ │ ┌─────────────────┐ │ │ ┌─────────────────┐ │
│ │Gemini │ MiniMax │ │ │ │      ZVec       │ │ │ │     JSON        │ │
│ │       │         │ │ │ │  (Semantic DB)  │ │ │ │                 │ │
│ ├───────┼─────────┤ │ │ └─────────────────┘ │ │ ├─────────────────┤ │
│ │ Kimi  │  xAI    │ │ │                     │ │ │ │    Markdown     │ │
│ │       │ (Grok)  │ │ │                     │ │ │ │   (Reports)     │ │
│ └───────┴─────────┘ │ │                     │ │ └─────────────────┘ │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

### Request Flow Diagram

```
┌────────┐     ┌──────────────┐     ┌──────────────────┐     ┌────────────┐
│  User  │────▶│ research.py  │────▶│ research.rs      │────▶│  expand_   │
│        │     │   (Python)   │     │   (Rust)         │     │  queries() │
└────────┘     └──────────────┘     └──────────────────┘     └─────┬──────┘
                                                                    │
                                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           QUERY EXPANSION                               │
│                    1 topic → 20 query variations                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  Gemini   │   │  MiniMax  │   │   xAI     │
            │  (20 q)   │   │  (20 q)   │   │  (20 q)   │
            └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                  │               │               │
                  └───────────────┼───────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MERGE & RANK                                    │
│              score_and_rank() → top N results                           │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FETCH & PARSE                                   │
│              fetch_url() × N (concurrent)                               │
│              HTML → Markdown conversion                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  Vectors  │ │   JSON    │ │ Markdown  │
            │  (ZVec)   │ │  (File)   │ │  (Report) │
            └───────────┘ └───────────┘ └───────────┘
```

### Provider Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PROVIDER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│  trait SearchProvider {                                         │
│      async fn search(&self, query: &str) -> Result<Vec<...>>;   │
│      fn capabilities(&self) -> ProviderCapabilities;             │
│      fn health_status(&self) -> HealthStatus;                   │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Gemini Provider │ │ MiniMax Provider│ │  xAI Provider   │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ • REST API      │ │ • REST API      │ │ • Python SDK    │
│ • Google Search │ │ • Coding Plan   │ │ • Web Search    │
│ • Free tier     │ │ • Paid          │ │ • X/Twitter     │
│ • 1000/day      │ │ • Rate limited  │ │ • Rate limited  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Kimi Provider  │
                    ├─────────────────┤
                    │ • REST API      │
                    │ • Web Search    │
                    │ • Paid          │
                    │ • Rate limited  │
                    └─────────────────┘
```

---

## Component Breakdown

### 1. Entry Points

#### research.py (Python CLI)
- **Lines:** ~100
- **Purpose:** CLI wrapper, argument parsing, binary dispatch
- **Key Functions:**
  - `validate_topic()` - Input validation
  - `get_rust_binary()` - Binary detection
  - `research()` - Main execution

#### api_server.py (REST API)
- **Lines:** ~150
- **Purpose:** FastAPI server for HTTP access
- **Endpoints:**
  - `GET /health` - Health check
  - `POST /research` - Research execution
  - `GET /research/sync` - Synchronous research

### 2. Core Modules

#### research.rs (Rust Orchestrator)
- **Lines:** ~340
- **Purpose:** Main orchestration, phase management
- **Key Functions:**
  - `main()` - Entry point
  - `run_search_phases()` - Concurrent execution
  - `format_output()` - Output formatting

#### search.rs (Search Engine)
- **Lines:** ~620
- **Purpose:** Provider integrations, query expansion
- **Key Functions:**
  - `search_gemini()` - Gemini search
  - `search_minimax()` - MiniMax search
  - `search_xai()` - xAI search (via Python bridge)
  - `expand_queries()` - Query variation generation

#### fetch.rs (Web Fetcher)
- **Lines:** ~65
- **Purpose:** HTTP fetching, HTML parsing
- **Key Functions:**
  - `fetch_url()` - Async HTTP GET
  - HTML → Markdown conversion
  - Content extraction

#### rank.rs (Result Ranker)
- **Lines:** ~155
- **Purpose:** Result scoring and deduplication
- **Key Functions:**
  - `score_and_rank()` - Main ranking
  - Domain classification
  - Source quality scoring

### 3. Supporting Modules

#### config.py
- **Purpose:** Configuration management
- **Features:**
  - Environment variable loading
  - Config file parsing (TOML)
  - Secret management

#### research_python.py
- **Lines:** ~400
- **Purpose:** Pure-Python fallback
- **Features:**
  - Rate limiting (token bucket)
  - Retry logic
  - All provider implementations

#### push_zvec.py
- **Lines:** ~150
- **Purpose:** Vector storage integration
- **Features:**
  - ZVec integration
  - Embedding generation
  - Fallback to JSONL

#### xai_search.py
- **Lines:** ~420
- **Purpose:** xAI SDK bridge
- **Features:**
  - Web search
  - X/Twitter search
  - Citation extraction

---

## Data Flow

### Input Processing

```
User Input
    │
    ▼
┌─────────────────┐
│ Input Validation│
│ • Non-empty     │
│ • Length < 500  │
│ • Sanitization  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Expansion │
│ • 20 variations │
│ • Templates     │
│ • Synonyms      │
└────────┬────────┘
         │
         ▼
   Provider APIs
```

### Result Processing

```
Raw Results (80+)
    │
    ▼
┌─────────────────┐
│  Deduplication  │
│ • URL-based     │
│ • Domain limit  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Scoring     │
│ • Source type   │
│ • Domain quality│
│ • Query match   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Ranking     │
│ • Sort by score │
│ • Top N select  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Content Fetch   │
│ • Async fetch   │
│ • HTML→MD       │
│ • Truncate      │
└────────┬────────┘
         │
         ▼
   Output Format
```

### Vector Storage Flow

```
Fetched Content
    │
    ▼
┌─────────────────┐
│ Text Extraction │
│ • Title         │
│ • Snippet       │
│ • URL           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedding Gen  │
│ • Gemini API    │
│ • 768 dims      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ZVec Insert    │
│ • Background    │
│ • Non-blocking  │
└────────┬────────┘
         │
         ▼
   Vector DB
```

---

## Design Patterns

### 1. Fallback Pattern

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Primary   │────▶│  Fallback   │────▶│   Error     │
│  (Rust)     │     │  (Python)   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

- Try Rust binary first
- Fall back to Python if unavailable
- Graceful error handling

### 2. Circuit Breaker (Planned)

```
┌─────────────┐
│   CLOSED    │── Normal operation
│  (working)  │
└──────┬──────┘
       │ Failure threshold
       ▼
┌─────────────┐
│    OPEN     │── Reject requests
│   (failed)  │
└──────┬──────┘
       │ Timeout
       ▼
┌─────────────┐
│  HALF-OPEN  │── Test request
│  (testing)  │
└─────────────┘
```

### 3. Token Bucket Rate Limiting

```
Bucket (capacity: 5)
┌─────┐
│ ○ ○ │── Tokens available
│ ○ ○ │
│  ○  │
└─────┘
   │
   │ Request consumes 1 token
   ▼
Refill rate: 2/sec
```

### 4. Concurrent Execution

```rust
// tokio::join! for parallel execution
let (gemini, minimax, kimi, xai) = tokio::join!(
    search_gemini(queries),
    search_minimax(queries),
    search_kimi(queries),
    search_xai(queries),
);
```

### 5. Background Tasks

```rust
// Vector push as background task
tokio::spawn(async move {
    push_to_zvec(results).await;
});
// Continue without waiting
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Core Engine | Rust | 1.75+ | Performance-critical code |
| Async Runtime | Tokio | 1.0+ | Async execution |
| HTTP Client | reqwest | 0.11+ | API calls |
| CLI/Wrapper | Python | 3.8+ | User interface |
| API Server | FastAPI | 0.100+ | REST API |
| Data Validation | Pydantic | 2.0+ | Schema validation |

### Search Providers

| Provider | API Type | Auth | Rate Limit |
|----------|----------|------|------------|
| Gemini | REST | API Key | 1000/day |
| MiniMax | REST | Bearer | Varies |
| Kimi | REST | Bearer | Varies |
| xAI | Python SDK | API Key | Varies |

### Storage

| Type | Technology | Use Case |
|------|------------|----------|
| Vector | ZVec | Semantic search |
| Cache | SQLite/Redis (planned) | Query caching |
| Config | TOML | User settings |

---

## Scalability

### Horizontal Scaling

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Load      │────▶│  Dsearch    │────▶│   Redis     │
│  Balancer   │     │   Node 1    │     │   (Cache)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       └────────▶   ┌─────────────┐
                   │  Dsearch    │
                   │   Node 2    │
                   └─────────────┘
```

### Vertical Scaling

| Resource | Current | Target |
|----------|---------|--------|
| Concurrent requests | 80 | 200+ |
| Response time | 2.8s | <2s |
| Memory usage | ~100MB | <200MB |
| CPU usage | 1 core | Multi-core |

### Bottlenecks

1. **API Rate Limits** - Provider-imposed
2. **Network Latency** - External APIs
3. **Embedding Generation** - Sequential

### Optimization Strategies

1. **Connection Pooling** - Reuse HTTP connections
2. **Caching** - Cache query results
3. **Batch Processing** - Batch embedding requests
4. **CDN** - Cache fetched content

---

*See also: docs/architecture/modules.md for detailed module documentation*
