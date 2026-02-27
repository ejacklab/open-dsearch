# xAI Integration - At a Glance

## 🎯 What Is It?

The xAI integration adds **two powerful search capabilities** to the CCLL research pipeline:

| Feature | Description |
|---------|-------------|
| **xAI Web Search** | Standard web search using Grok's `grok-4-1-fast-reasoning` |
| **xAI X Search** | Social platform search for real-time discussions on X |

Both execute **20 concurrent queries** and push results to vector storage in the background.

---

## 🏗️ Architecture in One Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CCLL RESEARCH PIPELINE                           │
│              (4 Search Providers × 20 Queries Each)                  │
└─────────────────────────────────────────────────────────────────────┘

User Topic
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1: Expand to 20 queries                                       │
│ (8 Google + 6 GitHub + 6 Official)                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    ├──────────────┬──────────────┬──────────────┬──────────────┐
    │              │              │              │              │
    ▼              ▼              ▼              ▼              │
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│ Gemini   │  │ MiniMax  │  │ xAI Web  │  │ xAI X    │        │
│  20 reqs │  │  20 reqs │  │  20 reqs │  │  20 reqs │        │
└─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘        │
      │             │             │             │              │
      └─────────────┴─────────────┴─────────────┘              │
                                │                              │
                                ▼                              │
                   ┌─────────────────────────┐                 │
                   │ Background: push_zvec   │                 │
                   │ (Vector DB Storage)     │                 │
                   └─────────────────────────┘                 │
                                │                              │
                                ▼                              │
                   ┌─────────────────────────┐                 │
                   │ Output: vectors/json/md │                 │
                   └─────────────────────────┘                 │
                                                                │
Total: 80 concurrent requests across 4 providers ◄──────────────┘
Each provider is OPTIONAL - works with any combination
```

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| **Total Queries** | 80 (20 × 4 providers) |
| **Concurrent Execution** | ✅ All 20 per phase run in parallel |
| **Expected Results** | ~200-400 unique results |
| **Execution Time** | ~20-40 seconds (search only) |
| **Background Storage** | ✅ Non-blocking zvec pushes |
| **API Keys Required** | Optional (any combination works) |

---

## 🔧 How It Works (30 Seconds)

### 1. Python Bridge (`xai_search.py`)
```python
# Uses xAI SDK to search
client = Client(api_key=os.getenv("XAI_API_KEY"))
chat = client.chat.create(
    model="grok-4-1-fast-reasoning",
    tools=[web_search()],  # or x_search()
)
# Streams response, extracts citations
# Outputs: [{"title": "...", "url": "...", "snippet": "..."}]
```

### 2. Rust Wrapper (`search.rs`)
```rust
// Wraps Python script
pub async fn search_xai(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    // Spawn Python script
    let output = tokio::task::spawn_blocking(|| {
        Command::new("python3").arg("xai_search.py").arg(query)...
    }).await?;
    
    // Parse JSON output
    let results: Vec<SearchResult> = serde_json::from_str(&stdout)?;
    Ok(results)
}
```

### 3. Orchestration (`research.rs`)
```rust
// Phase 2c: xAI Web Search (20 queries)
let search_futures: Vec<_> = queries.iter().map(|q| {
    async move { search_xai(&q, 10).await }
}).collect();

// Execute all concurrently
let results = join_all(search_futures).await;

// Push to zvec in background
for r in &results {
    Command::new("python3")
        .args(&["push_zvec.py", &r.title, &r.url, ...])
        .spawn();  // Non-blocking
}
```

---

## 🚀 Usage (3 Steps)

### Step 1: Set API Key
```bash
export XAI_API_KEY=your_xai_api_key_here
```

### Step 2: Build
```bash
cd .agents/skills/dsearch/scripts/rust
cargo build --release
```

### Step 3: Run
```bash
cd .agents/skills/dsearch/scripts
./rust/target/release/research --topic "Rust async" --mode vectors
```

**Output modes**:
- `--mode vectors` → Push to zvec (default, fastest)
- `--mode json` → Save raw results
- `--mode md` → Full report with fetched content

---

## 📁 Key Files

| File | Purpose | Language |
|------|---------|----------|
| `xai_search.py` | Python bridge to xAI SDK | Python |
| `search.rs` | Rust wrapper functions | Rust |
| `research.rs` | Orchestration (Phases 2c & 2d) | Rust |
| `push_zvec.py` | Vector storage handler | Python |
| `test_xai.py` | Connection test | Python |

---

## ✨ Unique Features

### 1. **Dual Search Capabilities**
- **Web Search**: Traditional web results
- **X Search**: Social platform insights (unique to xAI)

### 2. **Concurrent Execution**
- All 20 queries per phase run in parallel
- ~20x faster than sequential

### 3. **Non-blocking Storage**
- zvec pushes happen in background
- Doesn't slow down search

### 4. **Graceful Fallbacks**
- Missing API key? Skips that provider
- API error? Logs and continues
- All providers optional

### 5. **Standardized Output**
- All providers return same `SearchResult` structure
- Easy to merge and deduplicate

---

## 🆚 Provider Comparison

| Provider | Web Search | Social Search | Model | Concurrent |
|----------|------------|---------------|-------|------------|
| **Gemini** | ✅ | ❌ | gemini-2.0-flash | ✅ |
| **MiniMax** | ✅ | ❌ | abab6.5s | ✅ |
| **xAI** | ✅ | ✅ | grok-4-1-fast-reasoning | ✅ |

**xAI's Advantage**: Only provider with **both web and social search**

---

## 🎯 Use Case Examples

### Technical Research
```bash
./research --topic "Rust async runtime comparison" --mode vectors
```
- **Gemini**: Official docs
- **MiniMax**: GitHub repos
- **xAI Web**: Blog posts
- **xAI X**: Community discussions

### Market Research
```bash
./research --topic "AI agent frameworks 2026" --mode md
```
- **Gemini**: Industry reports
- **MiniMax**: GitHub trends
- **xAI Web**: News articles
- **xAI X**: Developer sentiment

### Competitive Analysis
```bash
./research --topic "Claude vs GPT-5 features" --mode json
```
- **Gemini**: Official comparisons
- **MiniMax**: Technical deep-dives
- **xAI Web**: Analysis articles
- **xAI X**: User experiences

---

## 🔍 Testing

```bash
# Test xAI connection
python test_xai.py

# Test citation extraction
python test_xai_citations.py

# Test Python bridge
python xai_search.py "Rust macros" --limit 5
python xai_search.py "Rust macros" --limit 5 --x-search
```

---

## 📚 Documentation

| Document | When to Use |
|----------|-------------|
| **xai-integration-summary.md** | Quick reference, getting started |
| **xai-architecture-visual.md** | Visual architecture understanding |
| **xAI-integration-complete-overview.md** | Complete technical documentation |
| **xai-data-flow-diagrams.md** | Visual data flow diagrams |
| **xai-integration-design.md** | Original design intent |
| **README.md** | Documentation index |

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | No | xAI API key (enables xAI searches) |
| `GEMINI_API_KEY` | No | Gemini API key |
| `MINIMAX_API_KEY` | No | MiniMax API key |
| `MINIMAX_API_HOST` | No | MiniMax API host |

**Note**: All providers are optional. Pipeline works with any combination.

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| xAI searches not running | Check `echo $XAI_API_KEY` is set |
| Python script not found | Rust has fallback paths built-in |
| No results from xAI | Test with `python xai_search.py "test"` |
| zvec not available | Falls back to JSONL files (expected) |

---

## 🎓 Learning Path

1. **Quick Start**: Read this file + run test scripts
2. **Architecture**: `xai-architecture-visual.md`
3. **Technical Details**: `xAI-integration-complete-overview.md`
4. **Data Flows**: `xai-data-flow-diagrams.md`
5. **Design Intent**: `xai-integration-design.md`

---

## ✅ Summary

The xAI integration adds **two search capabilities** (web + social) to the CCLL pipeline:

- ✅ **20 concurrent queries** per phase
- ✅ **Background vector storage** (non-blocking)
- ✅ **Graceful fallbacks** (optional providers)
- ✅ **Standardized output** (easy to merge)
- ✅ **Hybrid architecture** (Python + Rust)

**Result**: Comprehensive research with access to both traditional web results and real-time social insights.

---

**Next Steps**: 
1. Set `XAI_API_KEY`
2. Run `cargo build --release`
3. Try `./research --topic "test" --mode vectors`
4. Read `xai-integration-summary.md` for details

**Happy researching! 🚀**
