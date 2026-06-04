---
name: build-cd-pipeline
description: Use when automating release, to author a CD workflow with a safe, progressive rollout and automatic rollback.
---

# Build the CD pipeline

Author a CD workflow that builds the image and deploys with a **progressive, low-risk rollout**:

- **Canary** (shift a small % of traffic first) or **blue-green** (switch between two identical environments).
- An automatic **rollback path** if health checks fail.
- Promote the **same artifact** through Staging before Production.
