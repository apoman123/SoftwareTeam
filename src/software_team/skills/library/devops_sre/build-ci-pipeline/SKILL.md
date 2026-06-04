---
name: build-ci-pipeline
description: Use when automating integration, to author a GitHub Actions CI workflow that gates every pull request.
---

# Build the CI pipeline

Author a **GitHub Actions** CI workflow that runs on every pull request:

- Install dependencies, **lint / static-analyse**, run the **test suite**.
- Keep it fast.
- A red pipeline **blocks the merge** — CI is the first automated quality gate.
