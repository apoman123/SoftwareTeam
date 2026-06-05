"""Tests for the multi-provider LLM factory, focused on the Anthropic provider."""

from software_team.config import LLM_PROVIDERS, PROVIDER_DEFAULT_MODELS, Settings
from software_team.llm import _BUILDERS, StubChatModel, _anthropic_accepts_temperature, build_llm


def test_anthropic_is_a_registered_provider():
    assert "anthropic" in LLM_PROVIDERS
    assert "anthropic" in _BUILDERS
    defaults = PROVIDER_DEFAULT_MODELS["anthropic"]
    assert defaults["coder"] == "claude-opus-4-8"
    assert defaults["narrative"] == "claude-sonnet-4-6"


def test_settings_resolve_anthropic_models_per_tier(monkeypatch):
    monkeypatch.setenv("SWTEAM_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("SWTEAM_CODER_MODEL", raising=False)
    monkeypatch.delenv("SWTEAM_NARRATIVE_MODEL", raising=False)
    settings = Settings()
    assert settings.llm_provider == "anthropic"
    # software_engineer is a "coder" tier; product_manager is "narrative".
    assert settings.model_for("software_engineer") == "claude-opus-4-8"
    assert settings.model_for("product_manager") == "claude-sonnet-4-6"


def test_anthropic_temperature_gating():
    # Opus 4.7/4.8 removed sampling params — temperature must not be sent (HTTP 400).
    assert not _anthropic_accepts_temperature("claude-opus-4-8")
    assert not _anthropic_accepts_temperature("claude-opus-4-7")
    # Sonnet 4.6, older Opus, and Haiku still accept temperature.
    assert _anthropic_accepts_temperature("claude-sonnet-4-6")
    assert _anthropic_accepts_temperature("claude-opus-4-5")
    assert _anthropic_accepts_temperature("claude-haiku-4-5")


def test_dry_run_returns_stub_regardless_of_provider(monkeypatch):
    monkeypatch.setenv("SWTEAM_LLM_PROVIDER", "anthropic")
    llm = build_llm("software_engineer", dry_run=True)
    assert isinstance(llm, StubChatModel)
