---
name: build-cd-pipeline
description: Adds a GitHub Actions CD workflow with a safe, progressive rollout and automatic rollback. Use when automating release.
---

# Build the CD pipeline

Add a **GitHub Actions** deploy workflow (`.github/workflows/cd.yml`) that builds the image
and deploys with a **progressive, low-risk rollout**:

- Trigger on `push` to `main` (or `workflow_dispatch`); gate production behind an
  `environment:` with **required reviewers** so a human approves the release.
- **Build** the image once, generate and (optionally) sign an **SBOM**, then **Deploy**
  using a **canary** (shift a small % of traffic first) or **blue-green** (switch between
  two identical environments) strategy.
- Provide an automatic **rollback path** (`kubectl rollout undo`) when health checks fail
  (a step with `if: failure()`).
- Promote the **same artifact** (one built image) through Staging before Production.
