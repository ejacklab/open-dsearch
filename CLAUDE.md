---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# open-dsearch — Agent Entry Point

Deep research skill for AI agent terminals. Replaces shallow default search with a
multi-provider pipeline: Gemini, MiniMax, and xAI/Grok — 20 concurrent query variants,
ranked web fetching, and optional synthesis. Works across Claude Code, Gemini CLI,
Qwen CLI, OpenCode, and any agent terminal that can invoke shell scripts.

---

> **MANDATORY FIRST ACTION — do this before reading any further:**
> Read the file `~/.agents/AGENTS.md` now. Its rules are active for this entire session.
> Do not proceed until that file has been read.

---

## Project Overview

| Field | Value |
|---|---|
| Purpose | Deep research skill for AI agent terminals — multi-provider search, ranked fetching, synthesis |
| Core engine | Rust + tokio (`scripts/rust/src/`) |
| CLI wrappers | Python (`scripts/research.py`, `scripts/synthesize.py`) |
| Search providers | Gemini (free 1k/day), MiniMax (paid), xAI/Grok (web + X) |
| Output modes | `vectors` (zvec), `json` (raw), `md` (full report) |
| ZVec collection | `~/.open-dsearch/zvec_data/` — shared across all pipelines via `fcntl.flock` |
| Deployed to | `~/.agents/skills/dsearch/` |

---

## Key Decisions

| Decision | Rationale | ADR |
|---|---|---|
| Rust core, not Python | Concurrency + speed for parallel multi-phase search | `docs/decisions/adr-001-rust-core.md` |
| xAI via Python bridge | xAI SDK is Python-only; Rust spawns blocking Python tasks | `docs/decisions/adr-002-xai-python-bridge.md` |
| 3 search providers | Redundancy + complementary coverage (web + X corpus) | `docs/decisions/adr-003-multi-provider.md` |
| zvec for vector output + multi-agent accumulation | Search results pushed to shared ZVec collection for cross-topic synthesis | `docs/decisions/adr-004-zvec-output.md` |
## ZVec Multi-Agent Research Pattern

Shared vector collection for parallel subagent research. Each subagent searches independently and pushes results to a common ZVec collection. After all agents finish, query the accumulated pool to synthesize across topics.

```
Agent 1 (Rust binary --index) ──┐
Agent 2 (Rust binary --index) ──┼── writes ──► ~/.open-dsearch/zvec_data/
Agent 3 (Rust binary --index) ──┘              (fcntl.flock serializes writes)

Main agent: query_collection("topic synthesis") → cross-topic results
```

### Key design decisions

**File locking via fcntl.flock**: ZVec file-locks its collection on write. Multiple processes writing simultaneously causes `Resource temporarily unavailable`. The `_write_lock()` context manager in `push_zvec.py` acquires an exclusive blocking lock before any write operation, serializing access.

**Batch push only**: Always use `push_batch()` (single subprocess call) not per-result pushes. The Rust binary calls `push_zvec_batch()` which writes all results to a temp JSONL file and pipes it to `python3 push_zvec.py add --batch`. This avoids N subprocess spawns for N results.

**BM25 embeddings (4D)**: No API key needed. ZVec's built-in `BM25EmbeddingFunction(text)` produces a 4D float32 vector. Deterministic hash fallback if BM25 fails. Embedding dimension is set once on first call and reused for the collection schema.

**Doc IDs are MD5 hashes (16 chars)**: ZVec's regex validation rejects doc_ids with dots, slashes, or >50 chars. Use `hashlib.md5(url.encode()).hexdigest()[:16]` for safe, collision-resistant IDs.

**Collection path resolution**: Default is `~/.open-dsearch/zvec_data/`. Pass `--index-collection /path` to override. The `_get_collection()` function tries `zvec.open()` first (existing collection), falls back to `create_and_open()` after `shutil.rmtree()` if stale/corrupt.

### CLI usage

```bash
# Rust binary — search + index in one command
./scripts/rust/target/release/research --topic "Rust async patterns" \
    -q "Rust async patterns" -q "Rust concurrency primitives" \
    --mode json --index

# Query the accumulated pool (any pipeline)
python3 scripts/push_zvec.py query "async patterns" -n 5 --topic "Rust async patterns"
python3 scripts/push_zvec.py stats
python3 scripts/push_zvec.py clear --topic "my-topic"  # purge by topic

# Python pipeline also supports --index
python3 scripts/research_python.py "topic" --index -m json -n 10
```

| Block Reddit/Twitter/Medium | Low signal-to-noise in technical research | `docs/decisions/adr-005-domain-blocklist.md` |

---

## Reference Map

| What | Where |
|---|---|
| Architecture diagram + data flow | `docs/architecture/overview.md` |
| Module ownership | `docs/architecture/modules.md` |
| xAI integration design | `references/xai-integration-design.md` |
| Golden principles | `docs/agents/golden-principles.md` |
| Escalation rules | `docs/agents/escalation-rules.md` |
| Tool catalog | `docs/agents/tool-catalog.md` |
| Known issues | `docs/context/known-issues.md` |
| Tech debt | `docs/context/tech-debt.md` |
| Session state template | `plans/SESSION_STATE.template.md` |
| Project diary | `plans/diary.md` |

---

## Hard Rules

1. **Never commit API keys.** `GEMINI_API_KEY`, `MINIMAX_API_KEY`, `XAI_API_KEY` — environment only.
2. **Build Rust before running.** `cargo build --release` in `scripts/rust/` after any source change.
3. **`references/` is read-only.** Agents read, never modify. Changes need explicit user approval.
4. **Max function length: 50 lines (Rust) / 40 lines (Python).** Split if exceeded.
5. **No bare `except:` in Python.** Always catch a specific exception type.

---

## Tooling Quick Reference

```bash
cd scripts/rust && cargo build --release           # build first

# Rust binary (fast, primary)
./scripts/rust/target/release/research --topic "topic" --mode json --index
./scripts/rust/target/release/research --topic "topic" -q "query1" -q "query2" --mode md --index --index-collection /path

# Python pipeline (fallback / scripting)
python3 scripts/research_python.py "topic" --index -m json -n 10

# ZVec CLI tools
python3 scripts/push_zvec.py add --batch < results.jsonl --topic "my-topic"
python3 scripts/push_zvec.py query "semantic query" -n 5 -t "my-topic"
python3 scripts/push_zvec.py stats -c /path/to/collection

python3 scripts/drift_scan.py                      # must pass before every commit
```

Full tooling reference → `rules/tooling.md`

---

## CLI Design Decisions (Rationale)

The Python CLI (`research_python.py`) is the primary interface. Key decisions:

### `--verify` defaults to OFF
URL verification (checking if a URL responds) does NOT catch hallucinated URLs — it only filters genuinely dead servers. For LLM-augmented research, the human/agent spot-checks final links anyway. Speed > pre-filtering. Verification is available via `--verify` for cases where it's genuinely needed.

### `--dry-run` exists
Shows the query plan before burning API calls. Always use this first when scoping a new topic — confirm the query variants look right, then run for real.

### `--no-fetch` for md mode
Full page fetching (HTML → markdown) is the slow step. `--no-fetch` gives you titles, URLs, and snippets immediately in md format — useful when you only need to know what sources exist, not their content.

### `-Q` (not `-q`) for query count
Standard Unix convention: `-q` means "quiet/terse". Using `-Q` avoids accidental collision when scripts pass through extra flags.

### `--mode vectors` is the default
Vectors mode produces a minimal JSON index (title + URL) optimized for LLM consumption. Fastest path from search → structured data the agent can work with. Switch to `json` for raw results with snippets, `md` for full reports.

### Why these defaults work for agents
An agent doing research needs: speed (no unnecessary I/O), controllable output (know what will happen before it happens), and structured output (not walls of text). Every default is chosen to serve that pattern.

### `--index` flag on Rust binary
Pass `--index` to push all results to ZVec after search. The Rust binary calls `push_zvec.py` internally via subprocess (batch JSONL), so the Python runtime does not need to be available for the Rust binary to run. File locking (`fcntl.flock`) in `push_zvec.py` ensures safe concurrent writes from multiple processes.

---

## Workflow

Follows global workflow from `~/.agents/AGENTS.md`. Project additions:
- Before any Rust changes: read `references/rust-best-practices.md`
- After Rust changes: `cargo build --release && cargo test`
- Drift scan before every commit: `python3 scripts/drift_scan.py`

---

**When in doubt about architecture or scope — STOP and ask EJ gor gor.**
