"""Tests for the Tech Lead supervisor routing: iteration caps + capability gating."""

from software_team.agents.tech_lead import (
    route_after_build,
    route_after_planning,
    route_after_product_manager,
    route_after_qa_report,
    route_after_review,
    route_after_tests,
)
from software_team.config import SETTINGS


def test_review_loops_back_on_changes_within_cap():
    state = {"review_status": "changes", "review_iters": 1, "needs_deployment": True}
    assert SETTINGS.max_review_iters >= 2
    assert route_after_review(state) == "software_engineer"


def test_review_advances_to_ci_when_deploying():
    state = {"review_status": "approve", "review_iters": 0, "needs_deployment": True}
    assert route_after_review(state) == "devops_ci"


def test_review_advances_when_cap_reached():
    state = {
        "review_status": "changes",
        "review_iters": SETTINGS.max_review_iters,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "devops_ci"


def test_review_skips_ci_when_not_deploying():
    state = {"review_status": "approve", "review_iters": 0, "needs_deployment": False}
    assert route_after_review(state) == "qa_test"


def test_tests_loop_back_on_failure_within_cap():
    state = {"tests_passed": False, "fix_iters": 0, "needs_deployment": True}
    assert route_after_tests(state) == "software_engineer_fix"


def test_tests_advance_to_cd_when_deploying():
    assert (
        route_after_tests({"tests_passed": True, "fix_iters": 0, "needs_deployment": True})
        == "devops_cd"
    )


def test_tests_skip_deploy_when_not_deploying():
    state = {"tests_passed": True, "fix_iters": 0, "needs_deployment": False}
    assert route_after_tests(state) == "software_engineer_readme"


def test_planning_routes_to_backend_by_default():
    assert (
        route_after_planning({"needs_backend": True, "needs_frontend": True}) == "software_engineer"
    )


def test_planning_skips_to_frontend_when_no_backend():
    state = {"needs_backend": False, "needs_frontend": True}
    assert route_after_planning(state) == "frontend_engineer"


def test_planning_skips_to_review_when_nothing_to_build():
    state = {"needs_backend": False, "needs_frontend": False}
    assert route_after_planning(state) == "tech_lead_review"


def test_pm_routes_to_ux_only_when_frontend_needed():
    assert route_after_product_manager({"needs_frontend": True}) == "ux_designer"
    assert route_after_product_manager({"needs_frontend": False}) == "tech_lead_design"


def test_build_routes_to_frontend_only_when_frontend_needed():
    assert route_after_build({"needs_frontend": True}) == "frontend_engineer"
    assert route_after_build({"needs_frontend": False}) == "tech_lead_review"


def test_qa_report_routes_to_infra_docs_only_when_deploying():
    assert route_after_qa_report({"needs_deployment": True}) == "devops_docs"
    assert route_after_qa_report({"needs_deployment": False}) == "product_manager_docs"
