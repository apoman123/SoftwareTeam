"""Tests for the DevSecOps security-audit engine, tool, and skill wiring."""

from software_team.skills.common import security as sec

_BAD_DOCKERFILE = 'FROM python:latest\nRUN pip install -r requirements.txt\nCMD ["run"]\n'
_GOOD_DOCKERFILE = (
    "FROM python:3.12-slim\n"
    "RUN adduser --system appuser\n"
    "USER appuser\n"
    'HEALTHCHECK CMD python -c "import sys"\n'
    'CMD ["run"]\n'
)
_BAD_K8S = "kind: Deployment\nspec:\n  containers:\n    - image: app:latest\n"
_GOOD_K8S = (
    "kind: Deployment\nspec:\n  template:\n    spec:\n"
    "      securityContext:\n        runAsNonRoot: true\n"
    "      containers:\n        - image: app:1.0.0\n"
    "          securityContext:\n            allowPrivilegeEscalation: false\n"
    "          resources:\n            requests: {cpu: 100m}\n            limits: {cpu: 500m}\n"
    "          readinessProbe:\n            httpGet: {path: /health, port: 8000}\n"
)
_BAD_CI = "stages:\n  - test\ntest:\n  script: pytest\n"
_GOOD_CI = (
    "stages: [test, security]\n"
    "sast:\n  script: bandit -r app\n"
    "deps:\n  script: pip-audit\n"
    "scan:\n  script: trivy image app\n"
    "sbom:\n  script: syft app -o cyclonedx-json\n"
)


def test_audit_flags_unhardened_artifacts():
    findings = sec.audit(_BAD_DOCKERFILE, _BAD_K8S, _BAD_CI)
    assert findings
    # The unhardened artifacts fail the key hardening/scan checks.
    failed = {finding.check for finding in findings if not finding.ok}
    assert {
        "Runs as non-root",
        "Base image pinned",
        "Pod runs as non-root",
        "Image vulnerability scan present",
    } <= failed


def test_audit_passes_hardened_artifacts():
    findings = sec.audit(_GOOD_DOCKERFILE, _GOOD_K8S, _GOOD_CI)
    assert findings
    assert all(finding.ok for finding in findings), [f.check for f in findings if not f.ok]


def test_audit_skips_absent_artifacts():
    # Only a Dockerfile is provided → only Dockerfile checks run.
    findings = sec.audit(dockerfile=_GOOD_DOCKERFILE)
    assert {finding.artifact for finding in findings} == {"Dockerfile"}


def test_audit_report_summarises_and_lists_actions():
    report = sec.audit_report(_BAD_DOCKERFILE, _GOOD_K8S, _GOOD_CI)
    assert "# Security Review (DevSecOps)" in report
    assert "## Action items" in report  # the bad Dockerfile produces fixes
    assert "BagelHole/DevOps-Security-Agent-Skills" in report  # attribution rendered


def test_audit_report_clean_has_no_action_items():
    report = sec.audit_report(_GOOD_DOCKERFILE, _GOOD_K8S, _GOOD_CI)
    assert "_(fix needed)_" not in report
    assert "checks passed" in report


def test_audit_report_handles_no_artifacts():
    assert "No deployment artifacts" in sec.audit_report()


def test_security_audit_tool_wrapper():
    out = sec.security_audit.invoke(
        {"dockerfile": _GOOD_DOCKERFILE, "k8s": _GOOD_K8S, "ci_config": _GOOD_CI}
    )
    assert "Security Review (DevSecOps)" in out


def test_devsecops_shared_skills_mapped_to_devops_only():
    from software_team.skills.loader import SHARED, SHARED_SKILLS, load_character_skills

    devsecops = {
        "vulnerability-scanning",
        "sast-scanning",
        "dependency-scanning",
        "sbom-supply-chain",
        "container-hardening",
        "kubernetes-hardening",
    }
    # Each exists on disk and is mapped to the DevOps/SRE character.
    for name in devsecops:
        assert (SHARED / name / "SKILL.md").exists(), f"missing shared skill: {name}"
    assert devsecops <= set(SHARED_SKILLS["devops_sre"])

    loaded = {s.name for s in load_character_skills("devops_sre")}
    assert devsecops <= loaded

    # No other character picks up the DevSecOps set.
    for role in ("product_manager", "ux_designer", "tech_lead", "software_engineer", "qa_engineer"):
        assert devsecops.isdisjoint({s.name for s in load_character_skills(role)})


def test_audit_container_security_is_tool_backed():
    from software_team.skills.loader import load_character_skills

    devops = {s.name: s for s in load_character_skills("devops_sre")}
    assert "audit-container-security" in devops
    assert devops["audit-container-security"].tool is not None
    assert devops["audit-container-security"].kind == "tool"
