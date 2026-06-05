---
name: kubernetes-hardening
description: Hardens Kubernetes workloads — security contexts, Pod Security Standards, resource limits, network policies, and least-privilege RBAC. Use when writing Deployments, Pods, or other K8s manifests.
---

# Kubernetes hardening

Treat every workload as untrusted. Set the controls on the manifest so a compromised
container is contained.

**Every Pod/Deployment template:**

```yaml
spec:
  securityContext:        # pod-level
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: app
      image: app@sha256:...        # pin by digest, never :latest
      securityContext:             # container-level
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      resources:                   # requests + limits prevent noisy-neighbour / DoS
        requests: { cpu: "100m", memory: "128Mi" }
        limits:   { cpu: "500m", memory: "256Mi" }
```

**Also:**

- Enforce **Pod Security Standards** (`restricted`) via the namespace `pod-security.kubernetes.io/enforce` label.
- Add a **default-deny `NetworkPolicy`** (`podSelector: {}`) and open only the ingress/egress you need.
- **Least-privilege RBAC**: scope Roles/ServiceAccounts to the namespace and only the verbs required; never bind `cluster-admin`.
- Keep a liveness/readiness probe; mount secrets as files, not env, where possible.

> **Source:** Adapted from the `kubernetes-hardening` skill in
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills/tree/main/security/hardening/kubernetes-hardening)
> (MIT licence, © 2026 Toby Miller).
