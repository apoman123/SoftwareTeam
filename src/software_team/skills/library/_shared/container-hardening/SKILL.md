---
name: container-hardening
description: Hardens Docker images and container runtime — non-root user, pinned minimal base, read-only root filesystem, dropped capabilities, no baked secrets. Use when writing a Dockerfile or container runtime config.
---

# Container hardening

A container should run with the least privilege that still works. Build the image so it
cannot be tampered with and cannot escalate at runtime.

**In the Dockerfile:**

- **Pin a minimal base** by tag/digest (`python:3.12-slim`, `alpine`, or `distroless`) —
  never a bare `:latest`; smaller base = smaller attack surface.
- **Create and switch to a non-root user**, and own app files to it:
  `RUN adduser --system --no-create-home appuser` then `COPY --chown=appuser .` and `USER appuser`.
- **No secrets in layers** (no `ARG`/`ENV` secret, no copied `.env`); inject at runtime.
- Add a `HEALTHCHECK`; copy only what you need (use `.dockerignore`); install deps in a
  cached layer before app code.

**At runtime / in the Pod securityContext:**

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
  seccompProfile: { type: RuntimeDefault }
```

Run `docker run --read-only --security-opt=no-new-privileges:true`, and **scan the image**
before pushing (see `vulnerability-scanning`).

> **Source:** Adapted from the `container-hardening` skill in
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills/tree/main/security/hardening/container-hardening)
> (MIT licence, © 2026 Toby Miller).
