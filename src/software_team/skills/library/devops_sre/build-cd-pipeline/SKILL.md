---
name: build-cd-pipeline
description: Extends the GitLab + Jenkins pipeline with a safe, progressive rollout and automatic rollback. Use when automating release.
---

# Build the CD pipeline

Extend the GitLab + Jenkins pipeline so it builds the image and deploys with a
**progressive, low-risk rollout**:

- Add a **`deploy` stage** to `.gitlab-ci.yml` — a **manual** production gate that triggers
  the Jenkins deploy job; keep the existing lint / test / trigger-jenkins stages.
- In the **`Jenkinsfile`**, add **Build image** and **Deploy** stages using a **canary**
  (shift a small % of traffic first) or **blue-green** (switch between two identical
  environments) strategy.
- Provide an automatic **rollback path** (`kubectl rollout undo`) if health checks fail.
- Promote the **same artifact** (one built image) through Staging before Production.
