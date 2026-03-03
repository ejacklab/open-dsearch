---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Diary Protocol

## When to Write

At the end of every session where code was changed or decisions were made.
Mandatory — skipping is a hard rule violation.

## Format

```
## YYYY-MM-DD — <session goal, one line>

**Outcome:** DONE | PARTIAL | ABANDONED | BLOCKED
**Review:** [DRAFT — awaiting human review] | [REVIEWED]

**What happened:**
<narrative — enough for a cold-start agent to understand what was done>

**Decisions:**
- <decision>: <why, with trade-offs>

**Dead ends:**
- <what failed>: <specific reason>

**State at end:**
<what's left, what's in progress, what's next>
```

## Anti-Patterns

- Vague outcomes: "Made progress" → must name exactly what changed
- Missing dead ends: if something was tried and abandoned, record it
- Missing review status: every entry gets `[DRAFT]` until EJ gor gor marks it `[REVIEWED]`
- Writing at session start: diary is written at END only

## Cap

Max 2 unreviewed `[DRAFT]` entries. At cap — stop and ask EJ gor gor to review before continuing.
