---
name: sast-scanning
description: Runs static application security testing (SAST) on source code to catch vulnerabilities before deploy. Use when adding a security gate to CI/CD or automating secure code review.
---

# SAST scanning

Static analysis reads the source (no running app) to find injection, hardcoded secrets,
unsafe deserialisation, and similar bug classes early — the cheapest place to fix them.

- **Add a CI job** that runs a SAST scanner on every pull request:
  [Semgrep](https://semgrep.dev/) (`semgrep ci` with the `p/ci` + language rulesets) is a
  fast default; CodeQL or SonarQube suit larger orgs. For Python, `bandit -r app/`.
- **Make it a quality gate**: fail the pipeline on new HIGH/ERROR findings so they can't
  merge; report (don't block) on pre-existing/low ones to avoid alert fatigue.
- **Tune to cut false positives**: scan only your code (exclude vendored/test fixtures),
  pin the ruleset, and triage with inline `nosem`/baseline suppressions that carry a reason.
- **Add a secrets scan** in the same gate (e.g. gitleaks) so credentials never reach the repo.

Combine with `dependency-scanning` (third-party code) and `dast-scanning` (running app) for
defence in depth.

> **Source:** Adapted from the `sast-scanning` skill in
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills/tree/main/security/scanning/sast-scanning)
> (MIT licence, © 2026 Toby Miller).
