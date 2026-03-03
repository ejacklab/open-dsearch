---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 14d
---

# Known Issues

Update when new issues are confirmed. Remove entries when fixed.

## KI-01: No automated test suite

**Severity:** Medium
**Symptom:** No `cargo test` integration tests. Only manual `test_xai.py` scripts exist.
**Workaround:** Run `test_xai.py` manually before commits that touch the xAI bridge.
**Fix:** Add integration test fixtures with mocked API responses (`mockito` for Rust,
`responses` for Python).
**Owner:** ej

## KI-02: Go and TypeScript implementations are stubs

**Severity:** Low
**Symptom:** `scripts/go/research.go` and `scripts/ts/research.js` are partial
implementations. They are not functional.
**Workaround:** Use the Python/Rust path exclusively.
**Fix:** Decide whether multi-language support is needed. If not, remove the stubs
(TD-01).
**Owner:** ej
