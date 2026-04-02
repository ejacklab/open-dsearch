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
| Deployed to | `~/.agents/skills/dsearch/` |

---

## Key Decisions

| Decision | Rationale | ADR |
|---|---|---|
| Rust core, not Python | Concurrency + speed for parallel multi-phase search | `docs/decisions/adr-001-rust-core.md` |
| xAI via Python bridge | xAI SDK is Python-only; Rust spawns blocking Python tasks | `docs/decisions/adr-002-xai-python-bridge.md` |
| 3 search providers | Redundancy + complementary coverage (web + X corpus) | `docs/decisions/adr-003-multi-provider.md` |
| zvec for vector output | Downstream LLM synthesis without extra infrastructure | `docs/decisions/adr-004-zvec-output.md` |
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
python3 scripts/research.py "topic" --mode md --top 8 --queries 5
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
An agent doing research needs: speed (no unnecessary I/O),可控性 (know what will happen before it happens), and structured output (not walls of text). Every default is chosen to serve that pattern.

---

## Workflow

Follows global workflow from `~/.agents/AGENTS.md`. Project additions:
- Before any Rust changes: read `references/rust-best-practices.md`
- After Rust changes: `cargo build --release && cargo test`
- Drift scan before every commit: `python3 scripts/drift_scan.py`

---

**When in doubt about architecture or scope — STOP and ask EJ gor gor.**
