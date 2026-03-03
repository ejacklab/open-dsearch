---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 90d
---

# ADR-003: Three Search Providers

## Context

A single search provider has blind spots. Gemini has good web coverage but no social
corpus. MiniMax fills coverage gaps. xAI/Grok uniquely covers X/Twitter discourse —
valuable for tracking current technical discussions, release announcements, and
community reactions that don't appear in traditional web results.

## Decision

Run three providers concurrently: Gemini, MiniMax, xAI web search, and xAI X search
(the latter two count as one provider via the same SDK).

## Why

- Redundancy: if one provider fails, others still return results
- Complementary corpus: web + X/Twitter gives broader signal
- Concurrent execution means no latency penalty for adding providers
- Gemini free tier (1000 req/day) covers baseline; paid providers add depth

## When to Revisit

If a provider removes API access, costs become prohibitive, or a new provider
offers significantly better coverage for technical research topics.
