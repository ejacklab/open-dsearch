# xAI Integration - Quick Reference

## What Was Built

The xAI (Grok) integration adds **two new search capabilities** to the CCLL research pipeline:

1. **xAI Web Search** - Standard web search using `grok-4-1-fast-reasoning` with `web_search()` tool
2. **xAI X Search** - Social platform search using `grok-4-1-fast-reasoning` with `x_search()` tool

## How It Works

### Architecture Flow

```
User Topic → Expand to 20 queries → 
    ├─ Gemini (20 concurrent)
    ├─ MiniMax (20 concurrent)
    ├─ xAI Web (20 concurrent) ← NEW
    └─ xAI X (20 concurrent)   ← NEW
         ↓
    Push to zvec (background)
         ↓
    Synthesis (optional)
```

### Key Files

| File | Purpose |
|------|---------|
| `xai_search.py` | Python bridge to xAI SDK |
| `search.rs` | Rust wrapper with `search_xai()` and `xai_x_search()` |
| `research.rs` | Orchestrates concurrent execution (Phases 2c & 2d) |
| `push_zvec.py` | Background vector storage |

## Usage

### 1. Set API Key

```bash
export XAI_API_KEY=your_xai_api_key_here
```

### 2. Run Research

```bash
# Using Rust binary (recommended)
./research --topic "Rust async patterns" --mode vectors

# Using Python wrapper
python research.py "Rust async patterns" --mode vectors
```

### 3. Output Modes

- **`--mode vectors`** (default): Push to zvec, save index
- **`--mode json`**: Save raw results to JSON
- **`--mode md`**: Full report with fetched content

## Technical Details

### Python Bridge (`xai_search.py`)

```python
def search_xai(query, limit, use_x_search):
    # 1. Load API key
    api_key = os.getenv("XAI_API_KEY")
    
    # 2. Create client
    client = Client(api_key=api_key)
    
    # 3. Select tool
    tools = [x_search()] if use_x_search else [web_search()]
    
    # 4. Create chat with grok-4-1-fast-reasoning
    chat = client.chat.create(
        model="grok-4-1-fast-reasoning",
        tools=tools,
        include=["verbose_streaming"]
    )
    
    # 5. Stream and extract citations
    for response, chunk in chat.stream():
        response_obj = response
    
    # 6. Format and return JSON
    return [{"title": "...", "url": "...", "snippet": "..."}]
```

### Rust Wrapper (`search.rs`)

```rust
pub async fn search_xai(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    // Spawn Python script
    let output = tokio::task::spawn_blocking(|| {
        Command::new("python3")
            .arg("xai_search.py")
            .arg(query)
            .arg("--limit").arg(limit.to_string())
            .output()
    }).await?;
    
    // Parse JSON output
    let results: Vec<SearchResult> = serde_json::from_str(&stdout)?;
    
    Ok(results)
}

pub async fn xai_x_search(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    // Same as above, but adds --x-search flag
    // ...
}
```

### Orchestration (`research.rs`)

```rust
// Phase 2c: xAI Web Search (20 queries)
if xai_key {
    println!("\nPhase 2c: xAI web search ({} queries)...", queries.len());
    let search_futures: Vec<_> = queries.iter().map(|q| {
        let q = q.clone();
        async move {
            dsearch::search_xai(&q, 10).await
        }
    }).collect();
    
    let results = join_all(search_futures).await;
    
    for result in results {
        if let Ok(results) = result {
            // Push to zvec in background
            for r in &results {
                std::process::Command::new("python3")
                    .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &topic])
                    .spawn();
            }
            all_results.extend(results);
        }
    }
}

// Phase 2d: xAI X Search (20 queries)
if xai_key {
    println!("\nPhase 2d: xAI X search ({} queries)...", queries.len());
    let search_futures: Vec<_> = queries.iter().map(|q| {
        let q = q.clone();
        async move {
            dsearch::xai_x_search(&q, 10).await
        }
    }).collect();
    
    // ... same pattern as above
}
```

## Performance

- **Total Queries**: ~20 per phase (80 total across all providers)
- **Concurrent Execution**: All 20 queries per phase run in parallel
- **Expected Results**: ~200-400 unique results total
- **Execution Time**: ~20-40 seconds for all search phases
- **Background Processing**: zvec pushes happen asynchronously

## Fallback Strategy

The system gracefully handles failures:

1. **Missing API Key**: Skips that provider entirely
2. **API Error**: Logs error, continues with other providers
3. **Timeout**: 66-minute timeout per search, logs and continues
4. **Empty Results**: Tries next provider

All providers are **optional** - the pipeline works with any combination.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | No | xAI API key for Grok searches |
| `GEMINI_API_KEY` | No | Gemini API key |
| `MINIMAX_API_KEY` | No | MiniMax API key |
| `MINIMAX_API_HOST` | No | MiniMax API host (default: https://api.minimax.io) |

## Testing

```bash
# Test xAI connection
python test_xai.py

# Test citation extraction
python test_xai_citations.py

# Test full integration
python xai_search.py "Rust macros" --limit 5
python xai_search.py "Rust macros" --limit 5 --x-search
```

## Design Highlights

1. **Hybrid Architecture**: Python for xAI SDK, Rust for orchestration
2. **Concurrent Execution**: All queries run in parallel via `tokio::join!`
3. **Non-blocking Storage**: zvec pushes happen in background processes
4. **Standardized Output**: All providers return `Vec<SearchResult>`
5. **Graceful Degradation**: Missing keys or failures don't stop the pipeline

## Comparison with Other Providers

| Provider | Web Search | Social Search | Model | Concurrent |
|----------|------------|---------------|-------|------------|
| Gemini | ✅ | ❌ | gemini-2.0-flash | ✅ |
| MiniMax | ✅ | ❌ | abab6.5s | ✅ |
| xAI | ✅ | ✅ | grok-4-1-fast-reasoning | ✅ |

xAI is unique in providing **both web and social platform search** in one integration.
