---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
---

# Tech Debt

Agents must NOT fix these without a user-approved plan.

## TD-01: Go and TypeScript stubs

**Cost to fix:** Medium (full reimplementation or deletion decision)
**Why deferred:** Rust + Python path covers all current needs.
**Risk if touched:** Incomplete implementations could mislead consumers of the skill.
**Fix approach:** Decide whether multi-language support is needed. If not, delete both
stubs and update SKILL.md accordingly.

## TD-02: No mocked API tests

**Cost to fix:** Medium
**Why deferred:** Skill is early-stage; API response shapes are still evolving.
**Risk if touched:** Tests against live APIs are brittle (rate limits, API costs, flakiness).
**Fix approach:** Add `mockito` (Rust) + `responses` (Python) fixtures for each provider.
Wire into `cargo test` and a pytest suite.

## TD-04: Pre-existing GP-03 / GP-04 violations in source code

**Cost to fix:** Medium (refactoring, not logic changes)
**Why deferred:** Functions work correctly; refactor needs careful review to avoid regressions.
**Risk if touched:** `research.rs:main` is 286 lines — splitting needs a clear decomposition plan.
**Violations found by drift_scan:**
- `scripts/research.py:71` — `def main` (41 lines, limit 40)
- `scripts/push_zvec.py:50` — `def push_to_zvec` (58 lines) + 4 bare `except:` clauses
- `scripts/xai_search.py:169` — `def search` (109 lines), `def search_async` (77 lines)
- `scripts/rust/src/research.rs:51` — `fn main` (286 lines)
- `scripts/rust/src/search.rs` — `search_gemini` (61L), `search_with_fallback` (86L), `synthesize_with_llm` (113L)
- `scripts/rust/src/web_search.rs` — `search_gemini` (68L), `search_minimax` (52L)

**Fix approach:** Plan each refactor separately; start with `push_zvec.py` (bare excepts are highest risk).

## TD-03: zvec integration is implicit

**Cost to fix:** Low
**Why deferred:** zvec availability is environment-dependent; making it required
would break environments without it.
**Risk if touched:** Changing the zvec interface could break `push_zvec.py` silently.
**Fix approach:** Add explicit `--no-vectors` flag, clearer error messages when zvec
is absent, and document the zvec setup steps in SKILL.md.
