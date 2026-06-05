---
name: sbom-supply-chain
description: Generates, signs, and verifies an SBOM and build provenance to secure the software supply chain. Use when releasing an artifact, implementing SLSA controls, or producing compliance evidence.
---

# SBOM & supply-chain security

You can't secure or audit what you can't inventory. For every released artifact, produce a
Software Bill of Materials and make the build verifiable.

- **Generate an SBOM** at build time with [Syft](https://github.com/anchore/syft) (or
  cdxgen) in CycloneDX/SPDX format: `syft myapp:$TAG -o cyclonedx-json > sbom.json`, and
  publish it as a release artifact.
- **Match the SBOM against CVEs** (`grype sbom:sbom.json`) so you can answer "are we
  affected by CVE-X?" without rebuilding.
- **Sign artifact + SBOM and attach provenance** with [cosign](https://docs.sigstore.dev/)
  (keyless/Sigstore): `cosign sign` and `cosign attest --predicate sbom.json`. Verify on
  deploy (`cosign verify` / admission policy) so only trusted, attested images run.
- **Aim for SLSA**: build from source in CI, record who/what/how (provenance), and pin
  dependencies by digest.

Feeds `dependency-scanning` and `vulnerability-scanning`, and supports
`supply-chain-attack-response` when a dependency is compromised.

> **Source:** Adapted from the `sbom-supply-chain` skill in
> [BagelHole/DevOps-Security-Agent-Skills](https://github.com/BagelHole/DevOps-Security-Agent-Skills/tree/main/security/scanning/sbom-supply-chain)
> (MIT licence, © 2026 Toby Miller).
