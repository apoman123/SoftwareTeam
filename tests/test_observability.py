"""Tests for the LangSmith observability layer (run config, env wiring, traceable shim)."""

import os

from software_team import observability


def test_run_config_names_tags_and_annotates():
    config = observability.run_config(
        "software_engineer", tags=["software_engineer", "code"], metadata={"k": "v"}
    )
    assert config["run_name"] == "software_engineer"
    assert "software-team" in config["tags"]
    assert "code" in config["tags"]
    assert config["metadata"]["k"] == "v"
    # The provider is always annotated so traces are filterable by backend.
    assert "swteam.provider" in config["metadata"]


def test_configure_langsmith_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(observability.SETTINGS, "langsmith_tracing", False)
    assert observability.configure_langsmith() is False


def test_configure_langsmith_exports_canonical_env(monkeypatch):
    # setenv so monkeypatch restores these on teardown even though configure sets them directly.
    for key in (
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
    ):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(observability.SETTINGS, "langsmith_tracing", True)
    monkeypatch.setattr(observability.SETTINGS, "langsmith_project", "proj-x")
    monkeypatch.setattr(observability.SETTINGS, "langsmith_api_key", "ls-key")
    monkeypatch.setattr(observability.SETTINGS, "langsmith_endpoint", "")

    assert observability.configure_langsmith() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"  # legacy alias for older SDKs
    assert os.environ["LANGSMITH_PROJECT"] == "proj-x"
    assert os.environ["LANGSMITH_API_KEY"] == "ls-key"


def test_traceable_works_as_bare_and_parameterised_decorator():
    @observability.traceable
    def bare(x):
        return x + 1

    @observability.traceable(run_type="tool", name="doubler")
    def parameterised(x):
        return x * 2

    assert bare(1) == 2
    assert parameterised(3) == 6
