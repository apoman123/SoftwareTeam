---
name: security-and-hardening
description: Hardens code and pipelines against vulnerabilities — treat every external input as hostile and every secret as sacred. Use when handling user input, auth, data storage, external integrations, or wiring secrets into CI/CD.
---

# Security and hardening

Security is a constraint on every line that touches untrusted data, authentication, or
external systems — not a final phase.

**Always do (no exceptions):**

- **Validate all external input at the boundary** (API routes, form/handlers, webhooks);
  reject by default, allow-list what is expected.
- **Parameterise queries** and use safe serialisers — never build SQL/commands by string
  concatenation.
- **Keep secrets out of git.** Inject them from a secret store / CI secrets
  (GitHub Actions encrypted repository or environment secrets); commit only `.env.example`.
- **Authorise every request** server-side; never trust client-supplied identity or roles.
- **Least privilege** for tokens, deploy keys, and service accounts; scope and rotate them.

**Also:** pin and scan dependencies, send security headers / HTTPS, hash passwords with a
slow KDF, and log security events without logging the secrets themselves.

> **Source:** Adapted from the `security-and-hardening` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/security-and-hardening)
> (MIT licence, © 2025 Addy Osmani).
