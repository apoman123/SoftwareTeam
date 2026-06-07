"""Tests for deterministic project triage (needs_frontend / needs_deployment)."""

from software_team import triage
from software_team.state import new_state


def test_frontend_detected_for_ui_products():
    assert triage.needs_frontend("Build a web app with a React dashboard for users.")
    assert triage.needs_frontend("A mobile app with several screens.")


def test_no_frontend_for_pure_api_or_library():
    assert not triage.needs_frontend("Build a REST API for tasks with input validation.")
    assert not triage.needs_frontend("A Python library for parsing CSV files.")


def test_frontend_hint_matches_whole_words_only():
    # "ui" must not be detected inside "build" / "requirements".
    assert not triage.needs_frontend("Build the backend per the requirements.")


def test_deployment_default_true_for_a_service():
    assert triage.needs_deployment("A REST API for managing tasks.")


def test_deployment_positive_signal_wins():
    assert triage.needs_deployment("A CLI that is also deployed to Kubernetes with Docker.")


def test_no_deployment_for_library_or_cli():
    assert not triage.needs_deployment("A Python library for parsing CSV files.")
    assert not triage.needs_deployment("A command-line tool that formats JSON.")


def test_backend_default_true_even_for_libraries():
    assert triage.needs_backend("A Python library for parsing CSV files.")
    assert triage.needs_backend("A REST API for tasks.")


def test_no_backend_for_static_or_frontend_only():
    assert not triage.needs_backend("A static website with a few pages.")
    assert not triage.needs_backend("Build a React app, frontend only.")


def test_negated_phrases_override_keyword_matches():
    # "no backend" must not be read as the keyword "backend"; same for deployment/frontend.
    assert triage.needs_backend("A web app, no backend.") is False
    assert triage.needs_deployment("A service, no deployment needed.") is False
    assert triage.needs_frontend("A REST API, no frontend.") is False


def test_new_state_records_capability_flags():
    state = new_state("spec.md", "Build a web app with a React UI, deployed to k8s.", "out")
    assert state["needs_frontend"] is True
    assert state["needs_backend"] is True
    assert state["needs_deployment"] is True

    api = new_state("spec.md", "A Python library for parsing CSV.", "out")
    assert api["needs_frontend"] is False
    assert api["needs_backend"] is True
    assert api["needs_deployment"] is False

    site = new_state("spec.md", "A static marketing website, frontend only, run locally.", "out")
    assert site["needs_frontend"] is True
    assert site["needs_backend"] is False
    assert site["needs_deployment"] is False
