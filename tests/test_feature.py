"""Tests for incremental ("feature") mode: extend already-developed software.

Covers the existing-project loader, the feature-state constructor, the feature-mode
prompt brief, the dry-run feature variant, and an end-to-end build → feature pass that
proves the team integrates a new feature into an existing project without losing it.
"""

import shutil

import pytest
from typer.testing import CliRunner

from software_team import dryrun, project
from software_team.agents.base import feature_brief
from software_team.graph import build_graph
from software_team.main import app
from software_team.skills.common import filesystem
from software_team.state import (
    FEATURE_BRIEF_HEADER,
    FEATURE_MODE,
    new_feature_state,
    new_state,
)


def _make_project(root: str) -> None:
    """Write a tiny project (source + docs) into ``root``."""
    filesystem.write_file(root, "app/main.py", "x = 1")
    filesystem.write_file(root, "requirements.txt", "fastapi")
    filesystem.write_file(root, "docs/architecture.md", "# Arch")
    filesystem.write_file(root, "README.md", "# Readme")


# --------------------------------------------------------------------------- #
# project loader
# --------------------------------------------------------------------------- #


def test_load_partitions_source_and_docs(tmp_path):
    _make_project(str(tmp_path))
    proj = project.load(str(tmp_path))

    assert set(proj.source_files) == {"app/main.py", "requirements.txt"}
    assert set(proj.docs) == {"docs/architecture.md", "README.md"}
    assert not proj.is_empty
    assert "app/main.py" in proj.all_files and "README.md" in proj.all_files


def test_load_rejects_directory_without_source(tmp_path):
    # Only docs present → nothing to extend.
    filesystem.write_file(str(tmp_path), "docs/notes.md", "just notes")
    with pytest.raises(project.ProjectError):
        project.load(str(tmp_path))


def test_load_rejects_missing_directory(tmp_path):
    with pytest.raises(project.ProjectError):
        project.load(str(tmp_path / "does-not-exist"))


def test_brief_carries_header_tree_and_docs(tmp_path):
    _make_project(str(tmp_path))
    brief = project.load(str(tmp_path)).brief()

    assert FEATURE_BRIEF_HEADER in brief
    assert "app/main.py" in brief  # file tree
    assert "# Arch" in brief and "# Readme" in brief  # curated doc excerpts


def test_mirror_copies_every_file(tmp_path):
    _make_project(str(tmp_path / "src"))
    proj = project.load(str(tmp_path / "src"))
    dst = tmp_path / "dst"

    project.mirror(proj, str(dst))

    assert (dst / "app" / "main.py").exists()
    assert (dst / "docs" / "architecture.md").exists()
    assert (dst / "README.md").exists()


# --------------------------------------------------------------------------- #
# state + prompt brief
# --------------------------------------------------------------------------- #


def test_new_feature_state_flags_mode_and_seeds_files():
    src = {"app/main.py": "x = 1"}
    state = new_feature_state("<prompt>", "add priority", "/out", source_files=src, baseline="BASE")

    assert state["mode"] == FEATURE_MODE
    assert state["spec_text"] == "add priority"
    assert state["baseline"] == "BASE"
    assert state["source_files"] == {"app/main.py": "x = 1"}

    # The seed is copied, not aliased — later edits to the source map don't leak in.
    src["app/extra.py"] = "y = 2"
    assert "app/extra.py" not in state["source_files"]


def test_new_state_is_build_mode():
    assert new_state("s", "t", "/out")["mode"] != FEATURE_MODE


def test_feature_brief_empty_in_build_mode():
    assert feature_brief({"mode": "build"}) == ""
    assert feature_brief({}) == ""


def test_feature_brief_present_in_feature_mode():
    out = feature_brief({"mode": FEATURE_MODE, "baseline": "BASELINE-MARKER"})
    assert "BASELINE-MARKER" in out
    assert "NEW feature" in out


# --------------------------------------------------------------------------- #
# dry-run variant
# --------------------------------------------------------------------------- #


def test_dryrun_returns_feature_files_only_with_marker():
    feature_out = dryrun.canned_response("software_engineer", f"task\n{FEATURE_BRIEF_HEADER}\n")
    assert "def set_priority" in feature_out
    assert "tests/test_priority.py" in feature_out

    build_out = dryrun.canned_response("software_engineer", "plain greenfield build")
    assert "def set_priority" not in build_out


# --------------------------------------------------------------------------- #
# end-to-end (build, then add a feature into the built project)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def built_workspace(tmp_path_factory):
    """Run the full build pipeline once (dry-run) and return the resulting workspace."""
    base = tmp_path_factory.mktemp("built")
    state = new_state("spec.md", "Build a Task API", str(base))
    state["dry_run"] = True
    build_graph().invoke(state, config={"recursion_limit": 50})
    return base


@pytest.fixture(scope="module")
def feature_run(built_workspace, tmp_path_factory):
    """Add a feature into the built project once (dry-run); return (workspace, final state)."""
    ws = tmp_path_factory.mktemp("feature") / "ws"
    shutil.copytree(built_workspace, ws)

    existing = project.load(str(ws))
    assert "set_priority" not in existing.source_files["app/service.py"]  # precondition

    state = new_feature_state(
        "<prompt>",
        "Add a priority field to tasks and an endpoint to set it",
        str(ws),
        source_files=existing.source_files,
        baseline=existing.brief(),
    )
    state["dry_run"] = True
    final = build_graph().invoke(state, config={"recursion_limit": 50})
    return ws, final


def test_feature_run_extends_existing_project(feature_run):
    ws, final = feature_run

    # The run was framed as a feature run.
    assert final["mode"] == FEATURE_MODE

    # The feature landed: the service grew the capability and a new test file appeared.
    assert "def set_priority" in (ws / "app" / "service.py").read_text()
    assert "tasks/{task_id}/priority" in (ws / "app" / "main.py").read_text()
    assert (ws / "tests" / "test_priority.py").exists()

    # Existing code and docs were preserved, not wiped.
    assert (ws / "app" / "__init__.py").exists()
    assert (ws / "tests" / "test_service.py").exists()
    assert (ws / "docs" / "architecture.md").exists()


def test_feature_run_goes_through_full_cicd_devops_pipeline(feature_run):
    # A feature run re-runs the WHOLE SDLC, so the change is reviewed, regression-tested,
    # containerised, deployed, operated, and security-audited — not just code-edited.
    ws, final = feature_run

    # Every quality/deploy gate ran and passed end-to-end.
    assert final["review_status"] == "approve"
    assert final["tests_passed"] is True
    assert final["deploy_status"] == "healthy"

    # Every CI/CD + DevOps + operate artifact was (re)generated for the feature.
    for rel in (
        "Dockerfile",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "terraform/main.tf",
        "k8s/deployment.yaml",
        "k8s/service.yaml",
        "monitoring/prometheus.yml",
        "monitoring/alerts.yml",
        "docs/runbook.md",
        "docs/operations_report.md",
        "docs/infrastructure.md",
        "docs/security_review.md",
    ):
        assert (ws / rel).exists(), f"missing pipeline artifact: {rel}"

    # The pipeline is wired (GitLab shift-left security stage + Jenkins trigger) and the
    # DevSecOps audit gate is clean for the updated artifacts.
    gitlab_ci = (ws / ".gitlab-ci.yml").read_text()
    assert "trigger-jenkins" in gitlab_ci
    assert "container-scan" in gitlab_ci
    security_review = (ws / "docs" / "security_review.md").read_text()
    assert "Security Review (DevSecOps)" in security_review
    assert "_(fix needed)_" not in security_review


def test_feature_cli_in_place(built_workspace, tmp_path):
    ws = tmp_path / "cli_ws"
    shutil.copytree(built_workspace, ws)

    result = CliRunner().invoke(
        app, ["feature", "--into", str(ws), "--prompt", "Add task priority", "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert (ws / "tests" / "test_priority.py").exists()


def test_feature_cli_rejects_project_without_source(tmp_path):
    # An empty workspace has nothing to extend; the command should fail cleanly (not crash).
    result = CliRunner().invoke(
        app, ["feature", "--into", str(tmp_path), "--prompt", "x", "--dry-run"]
    )
    assert result.exit_code != 0
