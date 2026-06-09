"""Tests for the one-feature-at-a-time build loop and the Tech Lead's test-run quality gate."""

import asyncio

from software_team.agents.tech_lead import tech_lead_review_node
from software_team.graph import build_graph
from software_team.skills.common.authoring import parse_list_items
from software_team.state import new_state


def test_parse_list_items_handles_ordered_bulleted_and_empty():
    ordered = "1. first\n2) second\n3. third"
    assert parse_list_items(ordered) == ["first", "second", "third"]

    bulleted = "- alpha\n* beta\n+ gamma"
    assert parse_list_items(bulleted) == ["alpha", "beta", "gamma"]

    # Prose without list markers yields nothing.
    assert parse_list_items("just a paragraph, no list here") == []
    assert parse_list_items("") == []


def test_build_loop_builds_every_feature_one_at_a_time(tmp_path):
    # A plain backend spec: no UI, no deploy, so the run is just the feature build loop + QA.
    spec = "A Python REST API service for managing tasks. Run locally, no deployment."
    state = new_state("spec.md", spec, str(tmp_path))
    state["dry_run"] = True

    final = asyncio.run(build_graph().ainvoke(state, config={"recursion_limit": 60}))

    # The PM decomposed the spec into more than one feature (see dryrun._PM_DOC).
    assert len(final["features"]) >= 2
    # The loop built each feature exactly once, in order, and walked to the last one.
    assert final["feature_log"] == final["features"]
    assert final["feature_cursor"] == len(final["features"]) - 1

    # Each feature was reviewed and approved, and the real test suite passed.
    assert final["review_status"] == "approve"
    assert final["tests_passed"] is True


def test_tech_lead_review_forces_changes_when_tests_fail(tmp_path):
    # A workspace whose test suite genuinely fails — the review must catch it as a defect,
    # even though the dry-run review model is canned to "approve".
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_fail.py").write_text("def test_broken():\n    assert False\n")

    state = new_state("spec.md", "A small service.", str(tmp_path))
    state["dry_run"] = True
    state["features"] = ["A feature"]
    state["feature_cursor"] = 0
    state["acceptance_criteria"] = "It works."
    state["source_files"] = {"tests/test_fail.py": "def test_broken():\n    assert False\n"}

    result = asyncio.run(tech_lead_review_node(state))

    assert result["review_status"] == "changes"
    assert "Test suite result" in result["review_notes"]
