---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 90d
---

# ADR-005: Domain Blocklist

## Blocked Domains

reddit.com, twitter.com, x.com, medium.com

## Why

These domains consistently produce low-signal results for technical research:
- **Reddit / X / Twitter**: community speculation, opinion threads, and noise
  dominate over authoritative technical content
- **Medium**: paywall, duplicate secondary sources, SEO-optimised summaries
  that rarely contain primary technical depth

## How to Add a Domain

1. Open a new ADR documenting the domain, the problem pattern, and example bad results
2. Get explicit user approval
3. Update the blocked list in `rank.rs`

Do not edit `rank.rs` without an ADR — the blocklist is an architectural decision,
not a configuration detail.

## When to Revisit

If a blocked domain introduces a high-quality technical subcommunity or changes
its content model (e.g., Medium removes paywall for technical docs).
