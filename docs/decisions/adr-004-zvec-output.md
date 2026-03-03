---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 90d
---

# ADR-004: zvec for Vector Output Mode

## Context

Research results need to be consumed by downstream LLM synthesis. Raw JSON works
for human reading but is not optimal for retrieval-augmented generation.

## Decision

`--mode vectors` pushes results to zvec (local vector database). Gracefully degrades
to JSONL file storage if zvec is unavailable.

## Why

- Enables downstream LLM retrieval without external vector infrastructure
- zvec is local — no network dependency, no cost per query
- Graceful degradation means the skill works in environments without zvec installed

## Why NOT a cloud vector DB (Pinecone, Weaviate, etc.)

This is a local skill for terminal use. Adding a cloud dependency would require
credentials, network access, and per-use costs — incompatible with the lightweight
skill model.

## When to Revisit

If a more portable local vector format becomes standard, or if zvec is abandoned.
