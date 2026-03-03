---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Garbage Collection

## Trigger

Only after a stage or task is fully complete and verified.
Never mid-session. Never speculatively.

## Safe to Delete (dry-run + approval required)

- Stale `_raw.json` and `_fetched.md` outputs older than 7 days
- `*.pyc` and `__pycache__/` directories
- `scripts/rust/target/` (can always rebuild)
- Completed SESSION_STATE files from closed tasks

## Never Delete

- Anything in `references/`
- `plans/diary.md`
- Any file in `rules/` or `docs/`
- Source code without explicit user instruction

## Process

1. Dry-run: list files to be deleted, present to user
2. Get explicit approval
3. Delete

Default is **DO NOT DELETE**.
