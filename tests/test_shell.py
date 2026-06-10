"""Tests for the shell runner's CommandResult (output normalisation + summary)."""

from pathlib import Path

from software_team.skills.common import shell
from software_team.skills.common.shell import CommandResult


def test_command_result_normalises_bytes_to_text():
    # TimeoutExpired can hand back raw bytes even in text mode; they must be decoded so
    # summary() does not try to concat str to bytes.
    result = CommandResult(124, b"partial out\xff", b"boom")
    assert isinstance(result.stdout, str) and isinstance(result.stderr, str)
    assert result.summary() == "partial out�\nboom"


def test_command_result_handles_none_output():
    assert CommandResult(0, None, None).summary() == ""


def test_summary_truncates_long_output():
    summary = CommandResult(0, "x" * 5000, "").summary(max_chars=100)
    assert summary.endswith("... (truncated)")
    assert len(summary) <= 100 + len("\n... (truncated)")


def test_missing_tool_reports_not_found(tmp_path):
    result = shell.run_command(str(tmp_path), ["definitely-not-a-real-binary-xyz"])
    assert result.returncode == 127
    assert "command not found" in result.summary()


def _make_passing_python_project(root):
    (root / "requirements.txt").write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")


def test_gate_runs_backend_and_skips_uninstalled_frontend(tmp_path):
    # Backend (python) is runnable; frontend has a manifest but no node_modules -> skipped.
    _make_passing_python_project(tmp_path)
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text('{"scripts":{"test":"vitest"}}', encoding="utf-8")

    outcome = shell.run_test_suites(str(tmp_path))

    assert outcome.passed is True
    assert [run.component for run in outcome.runs] == ["."]
    assert any("frontend" in name for name in outcome.skipped)


def test_gate_fails_when_a_real_suite_fails(tmp_path):
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_bad.py").write_text("def test_bad():\n    assert False\n", encoding="utf-8")

    outcome = shell.run_test_suites(str(tmp_path))
    assert outcome.passed is False


def test_gate_passes_vacuously_when_nothing_testable(tmp_path):
    (tmp_path / "notes.txt").write_text("no tests here", encoding="utf-8")
    outcome = shell.run_test_suites(str(tmp_path))
    assert outcome.passed is True
    assert outcome.runs == []


def test_detect_test_command_prefers_workspace_venv(tmp_path):
    # Once the install step has created a workspace venv, the suite runs through it (so the
    # project's installed deps resolve) instead of the team's own interpreter.
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    venv_py = shell._venv_python(tmp_path)
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("", encoding="utf-8")  # stand-in for the venv interpreter

    cmd = shell.detect_test_command(str(tmp_path))

    assert cmd[0] == str(venv_py)
    assert "pytest" in cmd


def test_install_component_deps_dispatches_per_ecosystem(tmp_path, monkeypatch):
    calls: list[tuple[str, list[str]]] = []

    def fake_run_command(cwd, command, timeout=300):
        calls.append((str(cwd), command))
        # Make the venv "exist" the moment its creation is requested, so the Python install
        # proceeds to the pip steps (the real venv interpreter would now be on disk).
        if "venv" in command:
            venv_py = shell._venv_python(Path(cwd))
            venv_py.parent.mkdir(parents=True, exist_ok=True)
            venv_py.write_text("", encoding="utf-8")
        return CommandResult(0, "", "")

    monkeypatch.setattr(shell, "run_command", fake_run_command)

    # Node: npm install.
    node = tmp_path / "node"
    node.mkdir()
    (node / "package.json").write_text("{}", encoding="utf-8")
    shell._install_component_deps(node, 60)
    assert any(command[:2] == ["npm", "install"] for _, command in calls)

    # Go: nothing to pre-install (the toolchain fetches deps during the test run).
    calls.clear()
    go = tmp_path / "go"
    go.mkdir()
    (go / "go.mod").write_text("module x\n", encoding="utf-8")
    shell._install_component_deps(go, 60)
    assert calls == []

    # Python: create a venv, then pip-install the requirements and pytest into it.
    calls.clear()
    py = tmp_path / "py"
    py.mkdir()
    (py / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    shell._install_component_deps(py, 60)
    assert any("venv" in command for _, command in calls)
    assert any(command[-2:] == ["-r", "requirements.txt"] for _, command in calls)
    assert any(command[-1] == "pytest" for _, command in calls)
