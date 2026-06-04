"""End-to-end smoke test of the whole graph in dry-run mode."""

from pathlib import Path

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
        "docs/ux_design.md",
        "docs/architecture.md",
        "docs/test_plan.md",
        "app/service.py",
        "app/main.py",
        "tests/test_service.py",
        "tests/test_e2e.py",
        "Dockerfile",
        ".github/workflows/ci.yml",
        ".github/workflows/cd.yml",
        "terraform/main.tf",
        "k8s/deployment.yaml",
        "monitoring/prometheus.yml",
        "docs/runbook.md",
        "docs/operations_report.md",
    ]
    for rel in expected:
        assert (tmp_path / rel).exists(), f"missing artifact: {rel}"
