---
name: performance-optimization
description: Optimises performance by measuring first — profile, find the real bottleneck, fix it, measure again. Use when a performance budget or SLA exists, monitoring reports slowness, or you suspect a regression.
---

# Performance optimization

Measure before optimising. Performance work without measurement is guessing, and guessing
leads to premature optimisation that adds complexity without improving what matters.

The loop: **profile → identify the actual bottleneck → fix it → measure again.** Optimise
only what measurements prove matters.

- **Set a budget** up front (p95 latency, throughput, load-time target) so "fast enough"
  is defined, not subjective.
- **Find the dominant cost** — usually I/O, N+1 queries, missing indexes/caches, or
  unnecessary work in a hot loop — rather than micro-tuning cold code.
- **Verify with a before/after number**, and guard the win with a regression check so it
  doesn't silently erode.

Don't optimise before there is evidence of a problem.

> **Source:** Adapted from the `performance-optimization` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/performance-optimization)
> (MIT licence, © 2025 Addy Osmani).
