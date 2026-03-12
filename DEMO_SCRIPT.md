# Demo Script: Open-Dsearch

**Duration:** 60 seconds
**Format:** Side-by-side comparison

---

## Scene 1: The Problem (0-15s)

**Visual:** Split screen - User typing same query into different tools

**User:** "Research AI agent architectures 2026"

**Tool 1 (ChatGPT):** 
- Shows 3-5 sources
- Shallow summary
- "Learn more" links to docs

**Tool 2 (Perplexity):**
- Shows 5-10 sources
- Quick overview
- Citations but no depth

**Narrator:** "Most AI search tools give you 3-10 sources. That's shallow research."

---

## Scene 2: The Solution (15-45s)

**Visual:** Open terminal, run open-dsearch

**User types:**
```bash
python3 scripts/research.py "AI agent architectures 2026" --mode md
```

**Terminal shows:**
```
🔍 Phase 1: Gemini (20 queries)...
🔍 Phase 2: MiniMax (20 queries)...
🔍 Phase 3: xAI Web (20 queries)...
🔍 Phase 4: xAI X/Twitter (20 queries)...

✓ 84 sources found
✓ Top 10 ranked by relevance
✓ Full content fetched
✓ Markdown report generated

Time: 2.3s
```

**Visual:** Scroll through generated markdown
- Sources 1-10 with summaries
- Key insights extracted
- Architecture diagrams referenced
- Code examples highlighted

**Narrator:** "Open-dsearch: 80+ sources from 3 providers. Real deep research."

---

## Scene 3: The Output (45-60s)

**Visual:** Open generated markdown file

**Show:**
- Executive summary
- Key findings
- Source list (scrolling)
- Technical recommendations

**Narrator:** "Full research reports. Vector-ready for LLM synthesis. Open source."

**Final screen:**
```
Open-Dsearch
github.com/ejacklab/open-dsearch

Deep research for AI agents.
80+ sources. 3 providers. Open source.
```

---

## Tags for Social Media

- #AISearch
- #DeepResearch
- #OpenSource
- #ClaudeCode
- #MultiModel
- #RustLang

---

## Thumbnail Ideas

**Option 1:** Split screen
- Left: "3 sources" (sad face)
- Right: "84 sources" (fire emoji)

**Option 2:** Terminal screenshot
- Running research command
- Results streaming in
- "2.3s" timestamp highlighted

**Option 3:** Comparison chart
- Bar chart: 3 vs 5 vs 84
- Open-dsearch bar 10x taller
