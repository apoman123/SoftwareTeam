---
name: dependency-scanning
description: Performs software composition analysis (SCA) — scans third-party dependencies for known vulnerabilities and keeps them patched. Use when managing dependencies or adding an SCA gate to CI/CD.
---

# Dependency scanning

Most of your attack surface is code you didn't write. Continuously scan declared
dependencies (and their transitive tree) for known CVEs and keep them current.

- **Scan in CI on every change**: `pip-audit` (Python), `npm audit`/`osv-scanner`,
  Snyk, or OWASP Dependency-Check. Fail the build on HIGH/CRITICAL with an available fix.
- **Pin and lock** versions (lockfile / hashes) so scans are reproducible and a resolved
  fix can't silently regress.
- **Automate upgrades** with Dependabot/Renovate (grouped PRs) so patching is routine, not
  a fire drill — security patches first.
- **Scan the lockfile, not just direct deps**: most CVEs live in transitive packages.
- Record unavoidable, unfixed CVEs with an explicit, time-boxed waiver.

Pairs with `sbom-supply-chain` (inventory + provenance) and `vulnerability-scanning`
(the built image).

> **Source:** Adapted from the `dependency-scanning` skill in
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills/tree/main/security/scanning/dependency-scanning)
> (MIT licence, © 2026 Toby Miller).
