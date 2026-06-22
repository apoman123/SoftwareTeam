---
name: audit-container-security
description: Statically audits the Dockerfile, Kubernetes manifests, and CI/CD config for container/K8s hardening and missing security-scan gates, returning a pass/total review. Use after generating deployment artifacts, before declaring a release ready.
tool: security_audit
---

# Audit container & deployment security

Before calling a deployment ready, run the `security_audit` tool over the artifacts you
produced — the Dockerfile, the Kubernetes manifests, and the GitHub Actions workflows
(`.github/workflows/ci.yml` and `cd.yml`). It returns a markdown DevSecOps review: a
pass/total score, the
outstanding fixes first, then the full per-artifact checklist.

It checks for:

- **Container hardening** — non-root `USER`, a pinned base image (no `:latest`), a
  `HEALTHCHECK`, and no secrets baked into layers.
- **Kubernetes hardening** — `runAsNonRoot`, `allowPrivilegeEscalation: false`, CPU/memory
  `requests`/`limits`, and a health probe.
- **Pipeline scan gates** — a SAST stage, a dependency/SCA scan, an image vulnerability
  scan, and an SBOM/provenance step.

Treat every flagged item as work to do: fix the artifact (see `container-hardening`,
`kubernetes-hardening`) or add the missing scan stage (see `vulnerability-scanning`,
`sast-scanning`, `dependency-scanning`, `sbom-supply-chain`), then re-audit.

> **Source:** Checklist adapted from the DevSecOps skills of
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills)
> (MIT licence, © 2026 Toby Miller).
