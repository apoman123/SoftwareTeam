"""End-to-end smoke test of the whole graph in dry-run mode."""

from software_team.graph import build_graph
from software_team.state import new_state


def test_full_pipeline_dry_run(tmp_path):
    spec = "Build a Task API with create/list/complete/delete and input validation."
    state = new_state("spec.md", spec, str(tmp_path))
    state["dry_run"] = True

    final = build_graph().invoke(state, config={"recursion_limit": 50})

    # The generated project tests must actually pass.
    assert final["tests_passed"] is True
    assert final["review_status"] == "approve"
    assert final["deploy_status"] == "healthy"

    # Every phase produced its hallmark artifacts on disk.
    expected = [
        "docs/product_backlog.md",
        "docs/design_system.md",
        "docs/ux_design.md",
        "docs/architecture.md",
        "docs/test_plan.md",
        "app/service.py",
        "app/main.py",
        "tests/test_service.py",
        "tests/test_e2e.py",
        "Dockerfile",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "terraform/main.tf",
        "k8s/deployment.yaml",
        "monitoring/prometheus.yml",
        "docs/runbook.md",
        "docs/operations_report.md",
        "docs/security_review.md",
        # Document & Handoff phase — one deliverable per responsible role.
        "README.md",
        "docs/test_report.md",
        "docs/infrastructure.md",
        "docs/user_manual.md",
        "docs/release_notes.md",
    ]
    for rel in expected:
        assert (tmp_path / rel).exists(), f"missing artifact: {rel}"

    # The DevSecOps audit ran over the (hardened) artifacts and every check passes.
    security_review = (tmp_path / "docs" / "security_review.md").read_text()
    assert "Security Review (DevSecOps)" in security_review
    assert "_(fix needed)_" not in security_review

    # GitLab CI is wired to Jenkins: the pipeline triggers a Jenkins build, and the
    # Jenkinsfile is a declarative pipeline that deploys with an automatic rollback.
    gitlab_ci = (tmp_path / ".gitlab-ci.yml").read_text()
    assert "trigger-jenkins" in gitlab_ci
    assert "JENKINS_URL" in gitlab_ci
    jenkinsfile = (tmp_path / "Jenkinsfile").read_text()
    assert "pipeline {" in jenkinsfile
    assert "rollout undo" in jenkinsfile
