---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
related_modules: [search, fetch, rank, research, xai_search]
---

# Conventions

## Rust

- Function max: 50 lines. Split into named helpers if exceeded.
- Error handling: propagate with `?`. Use `anyhow` for app errors. No `unwrap()` outside tests.
- Async: `tokio::join!` for concurrent phases. `spawn_blocking` only for Python interop.
- Structs: derive `Debug, Serialize, Deserialize` by default on all data types.
- Naming: `snake_case` for files/functions/variables. `PascalCase` for types/enums.

## Python

- Function max: 40 lines.
- No bare `except:` — always catch a specific exception type.
- No hardcoded paths — use `pathlib.Path(__file__).parent` for script-relative paths.
- Dataclasses for structured output (see `SearchResult` in `xai_search.py`).
- Type hints on all function signatures.

## Canonical Search Result Shape

All providers must return results compatible with:

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # "gemini" | "minimax" | "xai_web" | "xai_x"
```

Rust equivalent: `ScoredResult` in `rank.rs`.

## Blocked Domains (rank.rs — do not add without ADR)

reddit.com, twitter.com, x.com, medium.com
