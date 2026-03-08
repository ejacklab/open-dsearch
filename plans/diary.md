# Project Diary

Append-only. New entries prepended. One entry per session.
Cap: 2 unreviewed [DRAFT] entries. At cap — stop and ask EJ gor gor to review.

---

## 2026-03-09 — Search Provider Reconfiguration (Kimi Integration)

**Outcome:** DONE
**Review:** [DRAFT — awaiting human review]

**What happened:**
1. **Kimi Integration:** Added Kimi (Moonshot AI) as a search provider. Kimi uses an OpenAI-compatible chat completion API at `api.moonshot.cn` with web search enabled via tool calling (`$web_search` builtin function).
2. **xAI Disabled:** Commented out xAI search phases in research.rs (code preserved for easy re-enablement).
3. **Provider Standardization:** All search provider secrets now use the same GCP project (`771559838251`).

**Decisions:**
- Use `kimi-k2-turbo-preview` model for Kimi search (cost-effective, fast)
- Keep xAI code but disable calls — easy to re-enable if needed
- All API keys consolidated in single GCP project: `764461751740`

**Key Learning — Provider API Patterns Differ:**
| Provider | Search Method | API Pattern |
|----------|---------------|-------------|
| MiniMax | Dedicated endpoint | `POST /v1/coding_plan/search` |
| Gemini | Grounding metadata | `googleSearch` tool in generateContent |
| Kimi | Tool calling (multi-turn) | Chat completion with `$web_search` builtin → requires 2nd call with tool results |

This diversity means each provider integration requires understanding their specific API design — no universal pattern.

**Dead ends:**
- None this session.

**State at end:**
Active providers: Gemini, Kimi, MiniMax. xAI disabled.
Next: Test Kimi with real API key once provisioned in GCSM.

---

## 2026-03-08 — Security Hardening, Technical Debt Refactor & Z.ai Advanced Integration

**Outcome:** DONE (Security & Refactor) | IN PROGRESS (Z.ai Integration)
**Review:** [DRAFT — awaiting human review]

**What happened:**
1. **Security Hardening:** Shifted API key management from `.env` files to a GCSM-first resolution pipeline. Implemented `scripts/secrets.py` (Python) and `scripts/rust/src/secrets.rs` (Rust). Added multi-project support (Project: `771559838251` and `monitor01-ec400`).
2. **Technical Debt Refactor:** Resolved all 15 drift issues (GP-03, GP-04). `drift_scan: clean`.
3. **Z.ai Advanced Integration:**
   - Implemented `scripts/rust/src/zai_poc.rs` to test Z.ai MCP servers (`web_search_prime`, `web_reader`) using JSON-RPC over HTTP SSE.
   - Successfully integrated **Z.ai Reader MCP** into the main Rust research pipeline for high-quality markdown extraction.
   - Implemented `scripts/research_zai.py` (Python) using the **Anthropic SDK** (`base_url="https://api.z.ai/api/anthropic"`) for superior synthesis with **GLM-5**.
   - Discovered that `web_search_prime` requires `location: "us"` for Max Tier accounts and strict header formatting (`Authorization: Bearer`).

**Decisions:**
- Use **GLM-5 via Anthropic SDK** for synthesis: much smoother integration than direct REST.
- Use **Z.ai Reader MCP** as primary fetcher: provides cleaner content than standard scraping.
- Maintain fallback to standard `fetch_url` if MCP fails.

**Dead ends:**
- Direct REST calls to Z.ai Search Prime were brittle; pivoting to MCP-specific protocols resolved most parsing issues.
- Encountered `MCP error -401` and `1113` (balance) during search testing; Z.ai account may require specific "resource package" activation for the Prime engine even on Max Tier.

**State at end:**
Security baseline hardened. Technical debt cleared. Z.ai Advanced Reader integrated.
Synthesizer upgraded to GLM-5 via Anthropic SDK.
Next: Resolve remaining authentication/quota hurdles for Search Prime to achieve "Billionaire-grade" search.

---

## 2026-02-28 — Bootstrap agent harness

**Outcome:** DONE
**Review:** [REVIEWED]

**What happened:**
Full harness bootstrapped for open-dsearch. Created CLAUDE.md, rules/ (architecture,
conventions, security, tooling, workflow/diary, workflow/cleanup), docs/ (architecture,
decisions × 5 ADRs, agents × 3 docs, context × 2 docs), plans/ (SESSION_STATE template,
this diary), and scripts/drift_scan.py. No existing source code or references/ modified.

**Decisions:**
- Framing as "AI agent terminal skill" not "Claude Code skill": project works across
  Claude Code, Gemini CLI, Qwen CLI, OpenCode and others.
- CLAUDE.md complements ~/.agents/AGENTS.md rather than duplicating it: project-specific
  rules only.
- Go/TS stubs filed as tech debt TD-01 not deleted: deletion needs explicit user decision.
- drift_scan uses subprocess for GP-07 (references/ git check) rather than file mtime,
  because mtime is unreliable across git checkouts.

**Dead ends:**
- None this session.

**State at end:**
All 22 harness files created. drift_scan.py implemented with 7 checks.
Next: run drift_scan to validate clean exit, then user reviews harness content.
