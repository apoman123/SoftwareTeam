---
name: build-ci-pipeline
description: Authors a GitHub Actions CI workflow that gates every pull request. Use when automating integration.
---

# Build the CI pipeline

Author a **GitHub Actions** workflow (`.github/workflows/ci.yml`) that runs on every pull
request (and pushes to `main`) and gates the merge:

- **Jobs** check out the code, install dependencies, **lint / static-analyse**, and run the
  **test suite** — kept fast, since this is the merge gate. Run independent jobs in parallel
  and `cache` dependencies.
- A **security** set of jobs shifts security left: a **SAST** scan, a **dependency/SCA**
  scan, and a **container image/config** CVE scan that fails on HIGH/CRITICAL.
- Read any secrets from `${{ secrets.* }}` and set least-privilege `permissions:` — never
  inline secrets.
- A red workflow **blocks the merge** (make the checks branch-protection rules) — CI is the
  first automated quality gate.

See the `github-actions-expert`, `ci-cd-and-automation`, and `gh` skills for the underlying
GitHub Actions detail.
