"""End-to-end tests of the focused debugging graph in dry-run mode."""

import asyncio

from software_team import project
from software_team.dryrun import SWE_FILES
from software_team.graph import build_debug_graph
from software_team.skills.common import filesystem
from software_team.state import new_debug_state

# The dry-run fix restores the known-good service, so break it the same way the fix repairs
# it: drop the empty-title validation so a unit test (test_create_empty_title_rejected) fails.
_BROKEN_SERVICE = SWE_FILES["app/service.py"].replace(
    '        title = (title or "").strip()\n'
    "        if not title:\n"
    '            raise TaskError("title must not be empty")\n'
    "        task = Task(id=next(self._ids), title=title)\n",
    '        title = (title or "").strip()\n        task = Task(id=next(self._ids), title=title)\n',
)


def _run_debug(workspace: str, bug: str = ""):
    existing = project.load(workspace)
    state = new_debug_state(
        workspace,
        workspace,
        source_files=existing.source_files,
        baseline=existing.brief(),
        bug_report=bug,
    )
    state["dry_run"] = True
    return asyncio.run(build_debug_graph().ainvoke(state, config={"recursion_limit": 60}))


def test_debug_pipeline_fixes_a_regression_and_reports(tmp_path):
    filesystem.write_files(str(tmp_path), SWE_FILES)
    # Plant a regression so the suite goes red, then let the debug loop diagnose and fix it.
    assert SWE_FILES["app/service.py"] != _BROKEN_SERVICE  # guard: the planted break took
    (tmp_path / "app" / "service.py").write_text(_BROKEN_SERVICE)

    # No reported symptom: a fix pass can only happen because the suite genuinely went red,
    # so fix_iters >= 1 proves the red -> fix -> green loop (not just a one-off diagnosis).
    final = _run_debug(str(tmp_path))

    # Ran the suite, fixed the root cause, and the suite is green again.
    assert final["fix_iters"] >= 1
    assert final["tests_passed"] is True
    # The fix restored the dropped validation on disk.
    assert "must not be empty" in (tmp_path / "app" / "service.py").read_text()
    assert (tmp_path / "docs" / "debug_report.md").exists()


def test_debug_pipeline_reports_clean_when_tests_pass(tmp_path):
    filesystem.write_files(str(tmp_path), SWE_FILES)

    final = _run_debug(str(tmp_path))

    # A green suite with no reported symptom goes straight to the report, never fixing.
    assert final["tests_passed"] is True
    assert final.get("fix_iters", 0) == 0
    assert (tmp_path / "docs" / "debug_report.md").exists()


def test_debug_pipeline_diagnoses_a_reported_symptom_on_green_suite(tmp_path):
    filesystem.write_files(str(tmp_path), SWE_FILES)

    final = _run_debug(str(tmp_path), bug="intermittent 500 on create")

    # Even on a green suite a reported symptom earns exactly one diagnosis pass (no infinite
    # loop): the bug may simply be untested, so the engineer looks once, then reports.
    assert final["fix_iters"] == 1
    assert final["tests_passed"] is True
    assert (tmp_path / "docs" / "debug_report.md").exists()
