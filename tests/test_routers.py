"""Tests for the Tech Lead supervisor routing: iteration caps + capability gating."""

from software_team.agents.garbage_collector import route_after_gc_review, route_after_gc_scan
from software_team.agents.tech_lead import (
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


# --- Feature loop: build/review one feature at a time ---


def test_review_builds_next_feature_when_more_remain():
    # Backend stage, feature 0 of 2 approved -> build the next backend feature.
    state = {
        "review_status": "approve",
        "review_iters": 0,
        "build_stage": "backend",
        "features": ["f0", "f1"],
        "feature_cursor": 0,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "software_engineer"


def test_review_changes_redoes_current_backend_feature():
    state = {
        "review_status": "changes",
        "review_iters": 0,
        "build_stage": "backend",
        "features": ["f0", "f1"],
        "feature_cursor": 1,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "software_engineer"


def test_review_builds_frontend_after_last_backend_feature():
    # Last backend feature approved and the product needs a UI not yet built -> frontend.
    state = {
        "review_status": "approve",
        "review_iters": 0,
        "build_stage": "backend",
        "features": ["f0", "f1"],
        "feature_cursor": 1,
        "needs_frontend": True,
        "frontend_built": False,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "frontend_engineer"


def test_review_changes_redoes_frontend_in_frontend_stage():
    state = {
        "review_status": "changes",
        "review_iters": 0,
        "build_stage": "frontend",
        "features": ["f0"],
        "feature_cursor": 0,
        "needs_frontend": True,
        "frontend_built": True,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "frontend_engineer"


def test_review_advances_past_built_frontend():
    # Frontend approved (already built) -> leave the build phase for CI.
    state = {
        "review_status": "approve",
        "review_iters": 0,
        "build_stage": "frontend",
        "features": ["f0"],
        "feature_cursor": 0,
        "needs_frontend": True,
        "frontend_built": True,
        "needs_deployment": True,
    }
    assert route_after_review(state) == "devops_ci"


def test_qa_report_routes_to_infra_docs_only_when_deploying():
    assert route_after_qa_report({"needs_deployment": True}) == "devops_docs"
    assert route_after_qa_report({"needs_deployment": False}) == "product_manager_docs"


# --- Garbage-collection routing ---


def test_gc_scan_submits_to_tech_lead_only_when_findings():
    assert route_after_gc_scan({"gc_findings": 3}) == "tech_lead_gc_request"
    assert route_after_gc_scan({"gc_findings": 0}) == "end"


def test_gc_review_loops_to_fix_on_changes_within_cap():
    assert route_after_gc_review({"review_status": "changes", "fix_iters": 0}) == "gc_fix"


def test_gc_review_ends_on_approve_or_when_cap_reached():
    assert route_after_gc_review({"review_status": "approve", "fix_iters": 0}) == "end"
    state = {"review_status": "changes", "fix_iters": SETTINGS.max_fix_iters}
    assert route_after_gc_review(state) == "end"
