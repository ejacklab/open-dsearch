---
owner: ej
last_verified: 2026-02-28
status: CURRENT
review_cycle: 90d
---

# ADR-001: Rust Core Engine

## Context

The research pipeline runs 4 concurrent search phases × 20 queries each = 80 concurrent
HTTP requests, plus N concurrent fetch tasks. Performance and resource efficiency matter
because this is invoked as a CLI skill — startup latency and memory footprint are visible
to the user.

## Decision

Implement the core pipeline in Rust with the tokio async runtime.

## Why

- Zero-cost async concurrency — 80 concurrent requests without thread-per-request overhead
- No GC pauses during fetch bursts
- Single statically-linked binary easy to deploy as a skill
- Memory safety without runtime cost

## Why NOT Python

- GIL limits true parallelism for CPU-bound work
- asyncio would work for I/O but adds startup overhead and dependency management complexity
- Harder to ship as a self-contained binary

## Why NOT Go

- Go was prototyped (`scripts/go/research.go`) but not completed
- Rust's type system catches more errors at compile time, important for a pipeline with many
  concurrent error paths
- Existing `xai_search.py` bridge pattern works cleanly with Rust's `spawn_blocking`

## When to Revisit

If xAI or future providers require deep Python integration that cannot be bridged via
`spawn_blocking`, or if the skill needs to run in environments where Rust cannot be compiled.
