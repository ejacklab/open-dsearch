# Project Diary

Append-only. New entries prepended. One entry per session.
Cap: 2 unreviewed [DRAFT] entries. At cap — stop and ask EJ gor gor to review.

---

## 2026-02-28 — Bootstrap agent harness

**Outcome:** DONE
**Review:** [DRAFT — awaiting human review]

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
