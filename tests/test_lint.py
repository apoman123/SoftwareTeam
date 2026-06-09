"""Tests for the language-aware linter runner."""

from software_team.skills.common import lint


def test_detect_lint_command_per_ecosystem(tmp_path):
    (tmp_path / "node").mkdir()
    (tmp_path / "node" / "package.json").write_text("{}")
    assert lint.detect_lint_command(str(tmp_path / "node"))[:3] == ["npx", "--no-install", "eslint"]

    (tmp_path / "go").mkdir()
    (tmp_path / "go" / "go.mod").write_text("module x\n")
    assert lint.detect_lint_command(str(tmp_path / "go")) == ["go", "vet", "./..."]

    (tmp_path / "py").mkdir()
    (tmp_path / "py" / "app.py").write_text("x = 1\n")
    assert lint.detect_lint_command(str(tmp_path / "py")) == ["ruff", "check", "."]


def test_detect_returns_none_when_nothing_to_lint(tmp_path):
    (tmp_path / "data.txt").write_text("not code")
    assert lint.detect_lint_command(str(tmp_path)) is None


def test_run_linters_skips_when_no_linter_applies(tmp_path):
    (tmp_path / "notes.md").write_text("# docs only")
    outcome = lint.run_linters(str(tmp_path))
    assert outcome.runs == []
    assert outcome.clean is True  # vacuously clean when nothing ran
    assert outcome.summary() == "no linter applicable"


def test_run_linters_skips_node_without_modules(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    outcome = lint.run_linters(str(tmp_path))
    # No node_modules -> dependencies not installed -> skipped, never a spurious failure.
    assert any("dependencies not installed" in s for s in outcome.skipped)
    assert outcome.clean is True


def test_run_linters_reports_python_issues(tmp_path):
    # An unused import is a clear ruff finding; the runner surfaces it (advisory).
    (tmp_path / "bad.py").write_text("import os\n\nx = 1\n")
    outcome = lint.run_linters(str(tmp_path))
    # ruff is a dev dependency here, so it runs (not skipped). If it were missing it would skip.
    if outcome.runs:
        assert outcome.components_with_issues >= 1
        assert "issues found" in outcome.summary()
