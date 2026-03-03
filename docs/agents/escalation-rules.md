---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Escalation Rules

## Mandatory Stop — ask EJ gor gor before proceeding

| Trigger | Why |
|---|---|
| Any change to `rank.rs` scoring logic | Affects all result quality downstream |
| Adding or removing a search provider | Architecture-level change, needs ADR |
| Modifying zvec push or output format | Breaks downstream consumers |
| Any schema change to `SearchResult` / `ScoredResult` | Cross-module contract |
| Any modification inside `references/` | Design docs, human judgment required |
| Drift scan exits non-zero after 3 fix attempts | Underlying issue needs diagnosis |
| Blocked domain list change in `rank.rs` | Requires ADR (see ADR-005) |

## Proceed Autonomously

| Task | Condition |
|---|---|
| Rust build + test | Routine, no source changes needed |
| Add/update `docs/` or `rules/` files | Content only, no code changes |
| Drift scan fixes (stale dates, missing frontmatter) | Mechanical, low risk |
| Diary entry at session end | Always mandatory, never needs approval |
| Add new test scripts in `scripts/` | Additive only, does not touch existing code |

## Decision Tree

1. Does it touch search ranking, provider list, or output format? → **STOP**
2. Does it modify a file in `references/`? → **STOP**
3. Have I failed this approach 3 times? → **STOP**
4. Otherwise → proceed, verify after each step

## When Stopping

Say exactly:

```
STOPPING: <trigger from mandatory stop table>
Current state: <what was done, what was not done>
Question: <the specific decision needed from EJ gor gor>
```
