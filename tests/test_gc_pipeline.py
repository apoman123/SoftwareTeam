"""End-to-end tests of the garbage-collection graph in dry-run mode."""

import asyncio

from software_team import project
from software_team.dryrun import SWE_FILES
from software_team.graph import build_gc_graph
from software_team.skills.common import filesystem
from software_team.state import new_gc_state

_DIRTY = "def helper():\n    # TODO: tidy this up\n    print('debug')\n    return 1\n"

_CLEAN_CALC = "\n".join(
    ["def add(a, b):", "    return a + b", "", "", "def sub(a, b):", "    return a - b"]
    + [f"# helper line {n}" for n in range(8)]
)


def _run_gc(workspace: str):
    existing = project.load(workspace)
    state = new_gc_state(
        workspace, workspace, source_files=existing.source_files, baseline=existing.brief()
    )
    state["dry_run"] = True
    return asyncio.run(build_gc_graph().ainvoke(state, config={"recursion_limit": 60}))


def test_gc_pipeline_scans_requests_fixes_and_verifies(tmp_path):
    filesystem.write_files(str(tmp_path), SWE_FILES)
    (tmp_path / "app" / "extra.py").write_text(_DIRTY)  # planted technical debt

    final = _run_gc(str(tmp_path))

    # The scan found issues, submitted them, the engineer fixed, and the Tech Lead verified.
    assert final["gc_findings"] > 0
    assert final["fix_iters"] >= 1
    assert final["review_status"] == "approve"  # dry-run review + passing tests
    assert (tmp_path / "docs" / "garbage_collection.md").exists()
    assert (tmp_path / "docs" / "gc_request.md").exists()


def test_gc_pipeline_short_circuits_on_a_clean_project(tmp_path):
    filesystem.write_files(
        str(tmp_path),
        {
            "app/__init__.py": "",
            "app/calc.py": _CLEAN_CALC,
            "tests/test_calc.py": (
                "from app.calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
            ),
            "README.md": "Run the calculator in `app/calc.py`.",
        },
    )

    final = _run_gc(str(tmp_path))

    # Nothing to collect: the run reports a clean scan and never enters the fix loop.
    assert final["gc_findings"] == 0
    assert final.get("fix_iters", 0) == 0
    assert (tmp_path / "docs" / "garbage_collection.md").exists()
    assert not (tmp_path / "docs" / "gc_request.md").exists()
