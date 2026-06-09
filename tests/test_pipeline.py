"""End-to-end smoke tests of the whole graph in dry-run mode."""

import asyncio

from software_team.graph import build_graph
from software_team.state import new_state


def test_full_pipeline_dry_run(tmp_path):
    # A full-stack, deployable spec exercises every phase: UX + frontend + deployment.
    spec = (
        "Build a task management web app with a React frontend and a REST API, "
        "deployed with Docker and Kubernetes."
    )
    state = new_state("spec.md", spec, str(tmp_path))
    state["dry_run"] = True

    final = asyncio.run(build_graph().ainvoke(state, config={"recursion_limit": 60}))

    # Capability triage routed the full pipeline.
    assert final["needs_frontend"] is True
    assert final["needs_backend"] is True
    assert final["needs_deployment"] is True

    # The work was decomposed into features and built one at a time: the loop walked the
    # whole plan (cursor reached the last feature) and the Tech Lead approved the result.
    assert len(final["features"]) >= 1
    assert final["feature_cursor"] == len(final["features"]) - 1

    # The generated project tests must actually pass.
    assert final["tests_passed"] is True
    assert final["review_status"] == "approve"
    assert final["deploy_status"] == "healthy"

    # Every phase produced its hallmark artifacts on disk.
    expected = [
        "docs/product_backlog.md",
        "docs/ux_design.md",
        "docs/architecture.md",
        "docs/test_plan.md",
        "app/service.py",
        "app/main.py",
        "tests/test_service.py",
        "tests/test_e2e.py",
        # Frontend phase (needs_frontend) — emitted under frontend/.
        "frontend/package.json",
        "frontend/src/App.jsx",
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


def test_pipeline_skips_frontend_and_deployment_for_a_library(tmp_path):
    # A library needs no UI and no deployment — triage skips those phases entirely.
    spec = "A Python library for parsing CSV files into typed records."
    state = new_state("spec.md", spec, str(tmp_path))
    state["dry_run"] = True

    final = asyncio.run(build_graph().ainvoke(state, config={"recursion_limit": 60}))

    assert final["needs_frontend"] is False
    assert final["needs_backend"] is True
    assert final["needs_deployment"] is False
    # The code still gets built and tested.
    assert final["tests_passed"] is True
    assert final["review_status"] == "approve"
    # No deploy phase ran, so there is no deploy status.
    assert final.get("deploy_status") is None

    # Present: planning, code, tests, and the non-infra handoff docs.
    for rel in (
        "docs/product_backlog.md",
        "docs/architecture.md",
        "docs/test_plan.md",
        "app/main.py",
        "tests/test_service.py",
        "README.md",
        "docs/test_report.md",
        "docs/user_manual.md",
        "docs/release_notes.md",
    ):
        assert (tmp_path / rel).exists(), f"missing artifact: {rel}"

    # Absent: the UI and every deployment/operate/infra artifact were skipped.
    for rel in (
        "docs/ux_design.md",
        "frontend/package.json",
        "Dockerfile",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "terraform/main.tf",
        "k8s/deployment.yaml",
        "monitoring/prometheus.yml",
        "docs/runbook.md",
        "docs/operations_report.md",
        "docs/security_review.md",
        "docs/infrastructure.md",
    ):
        assert not (tmp_path / rel).exists(), f"unexpected artifact: {rel}"
