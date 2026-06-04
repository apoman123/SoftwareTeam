"""Tests for the Tech Lead supervisor routing + iteration caps."""

from software_team.agents.tech_lead import route_after_review, route_after_tests
from software_team.config import SETTINGS


def test_review_loops_back_on_changes_within_cap():
    state = {"review_status": "changes", "review_iters": 1}
    assert SETTINGS.max_review_iters >= 2
    assert route_after_review(state) == "software_engineer"


def test_review_advances_when_cap_reached():
    state = {"review_status": "changes", "review_iters": SETTINGS.max_review_iters}
    assert route_after_review(state) == "devops_ci"


def test_review_advances_on_approve():
    assert route_after_review({"review_status": "approve", "review_iters": 0}) == "devops_ci"


def test_tests_loop_back_on_failure_within_cap():
    state = {"tests_passed": False, "fix_iters": 0}
    assert route_after_tests(state) == "software_engineer_fix"


def test_tests_advance_when_cap_reached():
    state = {"tests_passed": False, "fix_iters": SETTINGS.max_fix_iters}
    assert route_after_tests(state) == "devops_cd"


def test_tests_advance_on_pass():
    assert route_after_tests({"tests_passed": True, "fix_iters": 0}) == "devops_cd"
