---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Golden Principles

Enforced by `scripts/drift_scan.py`. Violations block commit.

## GP-01: Build before run

Never run the research pipeline without a fresh Rust build after any source change.
**Enforcement:** drift_scan checks binary mtime vs source mtime.
**Correct:** `cd scripts/rust && cargo build --release && python3 scripts/research.py ...`
**Incorrect:** Running research with a stale binary after editing Rust source.

## GP-02: No secrets in files

API keys must not appear in any committed file.
**Enforcement:** drift_scan scans for literal key patterns.
**Correct:** `os.environ["XAI_API_KEY"]` / `std::env::var("XAI_API_KEY")`
**Incorrect:** `api_key = "xai-abc123..."`

## GP-03: Function length limits

Rust functions must not exceed 50 lines. Python functions must not exceed 40 lines.
Split into named helper functions with descriptive names.
**Enforcement:** drift_scan GP-03 check on `.rs` and `.py` files.

## GP-04: No bare except

Python: always catch a specific exception type.
**Enforcement:** drift_scan GP-04 check.
**Correct:** `except requests.exceptions.Timeout:`
**Incorrect:** `except:`

## GP-05: No module-level heavy imports

Lazy-import xAI SDK and other optional dependencies inside functions, not at module top.
**Enforcement:** drift_scan GP-05 check.
**Rationale:** Prevents import failure when optional deps are missing in some environments.
**Correct:** `def search(): from xai_sdk import Client; ...`
**Incorrect:** `from xai_sdk import Client` (top of file)

## GP-06: No hardcoded paths

Use `pathlib.Path(__file__).parent` for all script-relative paths in Python.
**Enforcement:** drift_scan GP-06 check.
**Correct:** `SCRIPT_DIR = Path(__file__).parent`
**Incorrect:** `open("/home/wnej/dev/open-dsearch/...")`

## GP-07: references/ is read-only for agents

Files in `references/` are design docs. Agents read them, never modify.
Changes require explicit instruction from EJ gor gor.
**Enforcement:** drift_scan GP-07 checks git staged diff for `references/` changes.
