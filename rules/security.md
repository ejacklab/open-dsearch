---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 30d
related_modules: [research, xai_search, web_search]
---

# Security Rules

## API Keys

Never commit. Environment only:
- `GEMINI_API_KEY`
- `MINIMAX_API_KEY`
- `XAI_API_KEY`

Never log them. Never print them. Never write to output files.

## Pre-Commit Boundary Check

```bash
git remote get-url origin
gh repo view --json isPrivate -q '.isPrivate'          # must return true
grep -r "API_KEY\|SECRET\|TOKEN" . \
  --include="*.py" --include="*.rs" --include="*.go" \
  | grep -v "os.environ" | grep -v "std::env"
```

Abort if any literal key values are found.

## Endpoint Policy

Malaysia-based. International endpoints only.
No `*.cn` URLs. No China-region SDK configs.
Verify SDK base URLs when updating `xai_sdk` or Gemini SDK versions.

## Web Fetching

`fetch.rs` strips `<script>`, `<style>`, `<noscript>` before processing.
Do not disable this — it prevents accidental execution of fetched content.
