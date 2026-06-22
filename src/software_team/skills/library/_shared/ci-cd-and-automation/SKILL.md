---
name: ci-cd-and-automation
description: Automates quality gates and deployment so no change ships without passing them. Use when setting up or modifying build/test/release pipelines (GitHub Actions workflows) or configuring deployment strategies.
---

# CI/CD and automation

CI/CD is the enforcement mechanism for every other engineering practice — it catches on
every change what humans and agents miss.

- **Shift left.** Order the pipeline cheapest-and-fastest first: format/lint → static
  analysis/type-check → unit tests → build → integration/e2e → deploy. A bug caught in lint
  costs minutes; the same bug in production costs hours.
- **Faster is safer.** Small, frequent releases are lower-risk than big-bang ones: a deploy
  with 3 changes is easier to debug than one with 30, and frequent releases build
  confidence in the release process itself.
- **The gate.** A red pipeline blocks the merge/promotion — no exceptions, no manual
  override of failing required checks.
- **Cache and parallelise** independent jobs to keep the gate fast; pin action/runner
  versions for reproducibility.
- **Promote one artifact.** Build once, then promote the *same* image through staging to
  production rather than rebuilding per environment.

> **Source:** Adapted from the `ci-cd-and-automation` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/ci-cd-and-automation)
> (MIT licence, © 2025 Addy Osmani).
