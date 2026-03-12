# Reddit Post - r/ClaudeAI

## Title
**Built a Claude Code skill for deep research (80+ sources, multi-provider)**

## Body

Hey r/ClaudeAI! 👋

If you use **Claude Code** for research, I built something you might like:

---

### open-dsearch

A Claude Code skill that does **deep research** instead of shallow search.

---

### The Issue

When I ask Claude to research something, even with web search, I get maybe 5-10 sources. That's fine for quick answers, but for deep technical research? Not enough.

---

### What This Does

**Claude Code skill** that:
1. Takes your research query
2. Generates **20 query variations** (industry terminology, different angles)
3. Runs them across **3 providers** (Gemini + MiniMax + xAI/Grok)
4. Ranks and synthesizes the top results
5. Returns a full research report

**Total: 80+ sources in ~2.8 seconds**

---

### Example Usage

```bash
# In Claude Code
"Research AI agent memory persistence patterns"

# Claude activates open-dsearch skill
# → 80+ sources fetched and synthesized
# → Full markdown report generated
```

---

### Features

✅ **Claude Code integration** - works as a native skill
✅ **Multi-provider** - not dependent on one API
✅ **X/Twitter search** - real-time discussions
✅ **Local deployment** - your API keys, your machine
✅ **Vector storage** - ZVec integration for RAG

---

### Installation

```bash
git clone https://github.com/ejacklab/open-dsearch
cd open-dsearch
# Follow README.md for Claude Code setup
```

---

### Architecture

Built with:
- **Rust core** (tokio async, 2.8x faster than Python)
- **Python bridges** (for xAI SDK)
- **Claude Code skill** system

Full details in the repo README.

---

### Why This Matters

Claude is great at synthesis, but needs **good sources**. This skill ensures Claude has 80+ sources to synthesize from, not just 5.

Better sources → Better synthesis → Better results

---

**GitHub:** https://github.com/ejacklab/open-dsearch

**Feedback welcome!** Especially from heavy Claude Code users.

---

*Built with Claude's help. Irony appreciated. 😄*
