---
name: plan-performance-tests
description: Use when verifying non-functional requirements, to sketch a load/stress scenario with pass/fail thresholds.
---

# Plan performance tests

Sketch a load/stress scenario that mirrors **peak traffic**:

- Concurrency level and duration.
- Pass/fail **thresholds** tied to the non-functional requirements (e.g. p95 latency, error rate).
- Name a tool (**k6**, **Locust**) and run it against **Staging**, not Production.
