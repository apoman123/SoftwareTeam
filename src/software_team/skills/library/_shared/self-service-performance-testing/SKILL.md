---
name: self-service-performance-testing
description: Decides whether and how to performance-test a change and writes the test — load tests with k6, frontend Core Web Vitals, and unit-level benchmarks wired into CI. Use when adding or changing endpoints, queries, or critical paths.
---

# Self-service performance testing

Advise whether a change needs a performance test, pick the right kind, and produce a
runnable stub — always explaining the reasoning so the engineer can push back.

- **Decide first.** New/changed API endpoints, DB queries, or hot paths usually warrant a
  test; trivial changes do not.
- **Pick the tool to the layer:**
  - **Load / stress** of an endpoint → a **k6** script with explicit thresholds
    (e.g. `http_req_duration p(95) < 200`).
  - **Frontend** pages → Core Web Vitals (LCP/CLS/INP) budgets.
  - **Unit-level** hot code → a micro-benchmark asserting a ceiling so regressions fail CI.
- **Set thresholds, not vibes** — a test without a pass/fail bound can't catch a
  regression.
- **Run against staging, never production**, and respect shared-infrastructure safety
  rules (rate limits, isolated data).

> **Source:** Adapted from the `self-service-performance-testing` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/self-service-performance-testing)
> (MIT licence, © 2026 GitLab B.V.).
