---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
related_modules: [research, rust]
---

# Tooling

## Build (required after any Rust source change)

```bash
cd scripts/rust && cargo build --release
cd scripts/rust && cargo check          # faster, no binary output
cd scripts/rust && cargo test
cd scripts/rust && cargo fmt
cd scripts/rust && cargo clippy -- -D warnings
```

## Research

```bash
python3 scripts/research.py "topic" --mode md      --top 8  --queries 5
python3 scripts/research.py "topic" --mode json    --top 5  --queries 3
python3 scripts/research.py "topic" --mode vectors --top 10 --queries 5
```

## Synthesis

```bash
python3 scripts/synthesize.py --title "Report Title" --findings-dir ./findings/
```

## Standalone Binaries

```bash
./scripts/rust/target/release/web_search "query"
./scripts/rust/target/release/web_fetch  "https://example.com"
```

## xAI (Python bridge)

```bash
python3 scripts/xai_search.py "query" --mode web
python3 scripts/xai_search.py "query" --mode x
python3 scripts/test_xai.py
python3 scripts/test_xai_citations.py
```

## Drift Scan (must pass before every commit)

```bash
python3 scripts/drift_scan.py
```
