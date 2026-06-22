"""DevSecOps audit — static, offline hardening review of generated artifacts.

A dependency-free checker the DevOps/SRE character runs over the deployment artifacts it
produces (Dockerfile, Kubernetes manifests, GitHub Actions workflows) to flag missing
container/K8s hardening and absent security-scan gates, with a concrete fix for each
finding. It performs no I/O and reaches no network, so it is deterministic and works in
``--dry-run``; it inspects text already in the team state rather than running real scanners.

Exposed as a plain function (``audit_report``) for the deterministic DevOps node and as a
LangChain ``@tool`` (``security_audit``) for tool-capable models, mirroring the other
skills in ``common/``.

The checklist is adapted from the DevSecOps skills (container/kubernetes hardening,
vulnerability/SAST/dependency scanning, SBOM) of
``BagelHole/DevOps-Security-Agent-Skills`` (MIT licence, © 2026 Toby Miller);
https://github.com/BagelHole/DevOps-Security-Agent-Skills.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.tools import tool


@dataclass(frozen=True)
class Finding:
    """A single audit result: which artifact, pass/fail, the issue, and the fix."""

    artifact: str
    ok: bool
    check: str
    detail: str

    def render(self) -> str:
        """Render the finding as a markdown bullet (✅ pass / ⚠️ action needed)."""
        mark = "✅" if self.ok else "⚠️"
        body = f"{mark} **{self.check}** — {self.detail}"
        return body if self.ok else f"{body} _(fix needed)_"


def _audit_dockerfile(text: str) -> list[Finding]:
    """Check a Dockerfile for image-hardening basics (non-root, pinned base, no secrets)."""
    lowered = text.lower()
    findings = [
        Finding(
            "Dockerfile",
            "user " in lowered,
            "Runs as non-root",
            "declare a `USER` (create an unprivileged user and switch to it)"
            if "user " not in lowered
            else "a non-root `USER` is set",
        ),
        Finding(
            "Dockerfile",
            ":latest" not in lowered and "from " in lowered,
            "Base image pinned",
            "pin the base image to a specific tag/digest, not `:latest`"
            if ":latest" in lowered
            else "base image is pinned to a version",
        ),
        Finding(
            "Dockerfile",
            "healthcheck" in lowered,
            "Has a HEALTHCHECK",
            "add a `HEALTHCHECK` so the runtime can detect an unhealthy container"
            if "healthcheck" not in lowered
            else "a HEALTHCHECK is defined",
        ),
        Finding(
            "Dockerfile",
            not _mentions_secret(lowered),
            "No secrets baked in",
            "remove secret-looking ARG/ENV; inject secrets at runtime"
            if _mentions_secret(lowered)
            else "no obvious secrets in build layers",
        ),
    ]
    return findings


def _mentions_secret(lowered: str) -> bool:
    """Heuristically detect a secret assigned in an ``ARG``/``ENV`` line of a Dockerfile."""
    secret_words = ("secret", "password", "passwd", "api_key", "apikey", "token", "aws_secret")
    for line in lowered.splitlines():
        stripped = line.strip()
        if stripped.startswith(("arg ", "env ")) and any(word in stripped for word in secret_words):
            return True
    return False


def _audit_k8s(text: str) -> list[Finding]:
    """Check Kubernetes manifests for securityContext, resource limits, and probes."""
    lowered = text.lower()
    return [
        Finding(
            "Kubernetes",
            "runasnonroot" in lowered,
            "Pod runs as non-root",
            "set `securityContext.runAsNonRoot: true`"
            if "runasnonroot" not in lowered
            else "runAsNonRoot is set",
        ),
        Finding(
            "Kubernetes",
            "allowprivilegeescalation" in lowered,
            "Privilege escalation disabled",
            "set `allowPrivilegeEscalation: false` and `capabilities.drop: [ALL]`"
            if "allowprivilegeescalation" not in lowered
            else "privilege escalation is disabled",
        ),
        Finding(
            "Kubernetes",
            "limits" in lowered and "requests" in lowered,
            "Resource requests/limits set",
            "set CPU/memory `requests` and `limits` to prevent resource exhaustion"
            if not ("limits" in lowered and "requests" in lowered)
            else "resource requests and limits are defined",
        ),
        Finding(
            "Kubernetes",
            "readinessprobe" in lowered or "livenessprobe" in lowered,
            "Health probe configured",
            "add a readiness/liveness probe"
            if not ("readinessprobe" in lowered or "livenessprobe" in lowered)
            else "a health probe is configured",
        ),
    ]


def _audit_pipeline(ci_text: str, extra_text: str = "") -> list[Finding]:
    """Check the CI/CD config for security-scan gates (SAST, deps, image, SBOM)."""
    lowered = (ci_text + "\n" + extra_text).lower()

    def has(*needles: str) -> bool:
        return any(needle in lowered for needle in needles)

    return [
        Finding(
            "CI/CD pipeline",
            has("semgrep", "bandit", "codeql", "sonar", "sast"),
            "SAST gate present",
            "add a static analysis stage (e.g. Semgrep/Bandit)"
            if not has("semgrep", "bandit", "codeql", "sonar", "sast")
            else "a SAST stage is present",
        ),
        Finding(
            "CI/CD pipeline",
            has("pip-audit", "npm audit", "snyk", "dependency-check", "osv-scanner", "dependabot"),
            "Dependency scan present",
            "add a dependency/SCA scan (e.g. pip-audit/Snyk)"
            if not has("pip-audit", "snyk", "dependency-check", "osv-scanner", "dependabot")
            else "a dependency scan is present",
        ),
        Finding(
            "CI/CD pipeline",
            has("trivy", "grype", "image scan", "clair"),
            "Image vulnerability scan present",
            "add an image scan that fails on HIGH/CRITICAL (e.g. Trivy)"
            if not has("trivy", "grype", "image scan", "clair")
            else "an image scan is present",
        ),
        Finding(
            "CI/CD pipeline",
            has("syft", "sbom", "cyclonedx", "spdx", "cosign"),
            "SBOM / provenance step present",
            "generate and sign an SBOM (e.g. Syft + cosign)"
            if not has("syft", "sbom", "cyclonedx", "spdx", "cosign")
            else "an SBOM/provenance step is present",
        ),
    ]


def audit(
    dockerfile: str = "",
    k8s: str = "",
    ci_config: str = "",
    pipeline: str = "",
) -> list[Finding]:
    """Run every applicable hardening/scan check over the supplied artifacts.

    Args:
        dockerfile: The Dockerfile contents (skipped when empty).
        k8s: The Kubernetes manifest contents (skipped when empty).
        ci_config: The CI workflow (e.g. ``.github/workflows/ci.yml``) contents.
        pipeline: Additional workflow text (e.g. ``.github/workflows/cd.yml``) folded into
            the scan checks alongside ``ci_config``.

    Returns:
        The list of findings across all provided artifacts.
    """
    findings: list[Finding] = []
    if dockerfile.strip():
        findings += _audit_dockerfile(dockerfile)
    if k8s.strip():
        findings += _audit_k8s(k8s)
    if ci_config.strip() or pipeline.strip():
        findings += _audit_pipeline(ci_config, pipeline)
    return findings


def audit_report(
    dockerfile: str = "",
    k8s: str = "",
    ci_config: str = "",
    pipeline: str = "",
) -> str:
    """Audit the artifacts and render a markdown DevSecOps review.

    This is the plain-function entry point the DevOps node calls deterministically (no
    model, no network), so the review is reproducible and works in ``--dry-run``.

    Args:
        dockerfile: The Dockerfile contents.
        k8s: The Kubernetes manifest contents.
        ci_config: The CI workflow (e.g. ``.github/workflows/ci.yml``) contents.
        pipeline: Additional workflow text (e.g. ``.github/workflows/cd.yml``).

    Returns:
        A markdown report grouped by artifact, with a pass/total summary and the
        outstanding fixes called out first.
    """
    findings = audit(dockerfile, k8s, ci_config, pipeline)
    lines = ["# Security Review (DevSecOps)", ""]
    if not findings:
        lines += ["_No deployment artifacts were available to audit._", ""]
        return "\n".join(lines)

    passed = sum(1 for finding in findings if finding.ok)
    actions = [finding for finding in findings if not finding.ok]
    lines.append(f"**Score:** {passed}/{len(findings)} hardening checks passed.")
    lines.append("")
    if actions:
        lines.append("## Action items")
        lines += [f"- {finding.render()}" for finding in actions]
        lines.append("")

    # Full results grouped by artifact, in first-seen order.
    for artifact in dict.fromkeys(finding.artifact for finding in findings):
        lines.append(f"## {artifact}")
        lines += [f"- {f.render()}" for f in findings if f.artifact == artifact]
        lines.append("")

    lines.append(
        "> Checklist adapted from the DevSecOps skills of "
        "[BagelHole/DevOps-Security-Agent-Skills]"
        "(https://github.com/BagelHole/DevOps-Security-Agent-Skills) (MIT, © 2026 Toby Miller)."
    )
    lines.append("")
    return "\n".join(lines)


# --- LangChain tool wrapper (for ReAct-style agents on tool-capable models) ---


@tool
def security_audit(
    dockerfile: str = "", k8s: str = "", ci_config: str = "", pipeline: str = ""
) -> str:
    """Audit deployment artifacts for container/K8s hardening and CI security-scan gates.

    Pass the Dockerfile, Kubernetes manifests, and GitHub Actions workflow (CI/CD) text.
    Returns a markdown DevSecOps review: a pass/total score, the outstanding fixes, and the
    full per-artifact checklist. Use before declaring a deployment ready.
    """
    return audit_report(dockerfile, k8s, ci_config, pipeline)
