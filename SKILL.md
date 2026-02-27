---
name: dsearch
description: Comprehensive research methodology using Gemini, MiniMax, or xAI (Grok) search with zvec vector storage. Use when researching AI agents, protocols, or technical topics.
---

# CCLL - Deep Research

## Quick Start

When user asks to research something, the first steps are:
1. Try splitting the query into smaller, more specific sub-queries.
2. Use industry terms and established nomenclature where applicable.

Then, ask them what they want:

**"What output format do you want?"**

1. **Vector data** - Push all results to zvec for LLM to query later (best for synthesis)
2. **Raw JSON** - Just save search results as JSON file
3. **MD file** - Full research report with fetched content

Or give examples:
- *"Search + vectors to zvec"* → for LLM processing
- *"Save results to JSON"* → raw data
- *"Research report in markdown"* → final report

## Commands

```bash
# 1. Vector output (recommended) - pushes to zvec as results come in
python scripts/research.py "topic" --mode vectors

# 2. Raw JSON - save all search results
python scripts/research.py "topic" --mode json

# 3. Full MD report - search + fetch + report
python scripts/research.py "topic" --mode md --top 10
```

## How It Works

1. **20 queries via Gemini** → results stream in
2. **20 queries via MiniMax** → results stream in
3. **20 queries via xAI (Grok)** → results stream in (web search)
4. **20 queries via xAI (Grok)** → results stream in (X search)
5. Each result → push to zvec (background) immediately
6. User's LLM can query vectors for synthesis

## Environment

Set API keys:
```bash
export GEMINI_API_KEY=your-key  # Free: 1000/day
export MINIMAX_API_KEY=your-key  # Paid: Coding Plan
export XAI_API_KEY=your-key  # Paid: Grok Fast Reasoning
```
