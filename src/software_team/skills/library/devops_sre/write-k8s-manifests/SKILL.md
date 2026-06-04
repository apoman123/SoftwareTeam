---
name: write-k8s-manifests
description: Use when deploying to Kubernetes, to write manifests with probes and replicas that make rolling updates safe.
tool: write_source_file
---

# Write Kubernetes manifests

Write Kubernetes manifests:

- A **Deployment** with multiple replicas.
- A **readiness probe** (traffic only reaches healthy pods) and a **liveness probe**.
- Sensible resource **requests/limits**.
- A **Service** to expose it.

Probes + replicas are what make rolling updates and self-healing safe.
