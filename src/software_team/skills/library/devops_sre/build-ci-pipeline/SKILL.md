---
name: build-ci-pipeline
description: Authors a GitHub Actions CI workflow that gates every pull request. Use when automating integration.
---

# Build the CI pipeline

Author a **GitHub Actions** CI workflow that runs on every pull request:

- Install dependencies, **lint / static-analyse**, run the **test suite**.
- Keep it fast.
- A red pipeline **blocks the merge** — CI is the first automated quality gate.
