---
name: document-infrastructure
description: Documents where and how the service is deployed — pipelines, cloud resources, configuration, and rollout strategy. Use at handoff.
---

# Document the infrastructure

Record **where and how** the system runs, for on-call and platform engineers:

- **Pipelines** — what each CI and CD stage does, and what gates a release.
- **Resources** — the container image, the Terraform-managed cloud resources, and the Kubernetes Deployment/Service.
- **Configuration** — the required environment variables and *where* they live (never commit secrets).
- **Rollout & rollback** — the deploy strategy (canary / blue-green) and exactly how to roll back.

Pair this with the runbook: this document is the *where*, the runbook is the *what-to-do-when*.
