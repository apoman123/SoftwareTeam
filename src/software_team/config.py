"""Central configuration for the team.

Covers the LLM provider, per-role model selection, web search, paths, and loop caps.
All values are overridable through environment variables (see .env.example). The team
can run on a local Ollama server, the OpenAI API, the Anthropic API (Claude), Google
Gemini (google-genai), or a local GGUF model via llama.cpp — selected with
``SWTEAM_LLM_PROVIDER``. Each character node can also pull fresh facts from the internet
(e.g. the latest API of a library) through the configured web-search provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Load ``.env`` from the repo root into ``os.environ`` (real env vars win).

    The team is configured entirely through environment variables, and ``.env.example``
    documents them, but nothing was loading the file — so a ``.env`` selecting e.g. the
    ``llama_cpp`` provider was ignored and the defaults (Ollama) were used instead. This
    minimal parser avoids a hard dependency on python-dotenv. Lines that are blank, are
    comments (``#``), or are already set in the environment are skipped, so an explicit
    ``export`` always overrides the file.
    """
    env_path = repo_root() / ".env"
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        # Strip an inline comment that follows the value (only when unquoted).
        if value[:1] not in ("'", '"') and " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[key] = value


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Each graph node ("task role") is mapped to a model "tier". "coder" needs strong code
# + tool calling; "narrative" handles planning / design / ops prose. Unknown keys fall
# back to the narrative tier.
ROLE_TIERS: dict[str, str] = {
    # Interactive spec interview (proposes questions + writes the spec) — prose work.
    "spec_author": "narrative",
    "product_manager": "narrative",
    "ux_designer": "narrative",
    "tech_lead_design": "coder",
    "tech_lead_review": "coder",
    "qa_planning": "narrative",
    "software_engineer": "coder",
    "software_engineer_fix": "coder",
    "frontend_engineer": "coder",
    "devops_ci": "narrative",
    "devops_cd": "narrative",
    "operate": "narrative",
    # Document & Handoff — prose deliverables, so the narrative tier.
    "software_engineer_readme": "narrative",
    "qa_report": "narrative",
    "devops_docs": "narrative",
    "product_manager_docs": "narrative",
}

# Supported LLM backends. The default per-tier model for each, used unless overridden by
# SWTEAM_CODER_MODEL / SWTEAM_NARRATIVE_MODEL. For llama.cpp the "model" is the path to a
# local .gguf file, so there is no useful default — set it explicitly.
LLM_PROVIDERS = ("ollama", "openai", "anthropic", "google", "llama_cpp")

PROVIDER_DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "ollama": {"coder": "qwen2.5-coder:7b", "narrative": "llama3.1:8b"},
    "openai": {"coder": "gpt-4o", "narrative": "gpt-4o-mini"},
    # Anthropic Claude: Opus 4.8 for code (most capable), Sonnet 4.6 for prose
    # (best speed/intelligence balance). See https://docs.claude.com/en/docs/about-claude/models.
    "anthropic": {"coder": "claude-opus-4-8", "narrative": "claude-sonnet-4-6"},
    "google": {"coder": "gemini-1.5-pro", "narrative": "gemini-1.5-flash"},
    "llama_cpp": {"coder": "", "narrative": ""},
}


def _provider() -> str:
    provider = _env("SWTEAM_LLM_PROVIDER", "ollama").lower()
    return provider if provider in LLM_PROVIDERS else "ollama"


def _model(tier: str) -> str:
    """Resolve the model for a tier: explicit override wins, else the provider default."""
    override = _env(f"SWTEAM_{tier.upper()}_MODEL", "")
    if override:
        return override
    return PROVIDER_DEFAULT_MODELS[_provider()][tier]


@dataclass
class Settings:
    """Resolved runtime settings, populated from the environment at construction."""

    # --- LLM provider selection ---
    llm_provider: str = field(default_factory=_provider)
    coder_model: str = field(default_factory=lambda: _model("coder"))
    narrative_model: str = field(default_factory=lambda: _model("narrative"))
    temperature: float = field(default_factory=lambda: _env_float("SWTEAM_TEMPERATURE", 0.2))
    # Hard cap on tokens generated per LLM turn. Without it a local model can fall into a
    # degenerate repetition loop (e.g. repeating a list item or table row) and emit tokens up to
    # the full context window, which looks like the run "hanging". Bounds every turn so it
    # always terminates; raise it for code-heavy runs that legitimately emit large files.
    max_tokens: int = field(default_factory=lambda: _env_int("SWTEAM_MAX_TOKENS", 8192))
    # Per-request timeout (seconds). Turns serve as an inactivity deadline: because nodes
    # stream the response, this bounds the gap *between* tokens, not the whole generation —
    # so a slow but healthy local model keeps running while a wedged/OOM-killed server, which
    # goes silent, fails fast instead of leaving the client blocked forever.
    request_timeout: float = field(
        default_factory=lambda: _env_float("SWTEAM_REQUEST_TIMEOUT", 600.0)
    )

    # --- Ollama ---
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))

    # --- OpenAI (and OpenAI-compatible endpoints) ---
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", ""))

    # --- Anthropic Claude ---
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY", ""))

    # --- Google Gemini (google-genai) ---
    google_api_key: str = field(
        default_factory=lambda: _env("GOOGLE_API_KEY", _env("GEMINI_API_KEY", ""))
    )

    # --- Web search (latest info for every character) ---
    search_provider: str = field(
        default_factory=lambda: _env("SWTEAM_SEARCH_PROVIDER", "duckduckgo").lower()
    )
    search_max_results: int = field(
        default_factory=lambda: _env_int("SWTEAM_SEARCH_MAX_RESULTS", 4)
    )
    tavily_api_key: str = field(default_factory=lambda: _env("TAVILY_API_KEY", ""))

    # --- Loop caps (prevent infinite review / bug-fix loops) ---
    max_review_iters: int = field(default_factory=lambda: _env_int("SWTEAM_MAX_REVIEW_ITERS", 2))
    max_fix_iters: int = field(default_factory=lambda: _env_int("SWTEAM_MAX_FIX_ITERS", 2))
    # Max rounds of the interactive spec interview (each round the agent may ask follow-up
    # questions based on the answers so far). Bounds the conversation so it always ends.
    max_interview_rounds: int = field(
        default_factory=lambda: _env_int("SWTEAM_MAX_INTERVIEW_ROUNDS", 3)
    )

    # --- LangSmith observability (tracing, named runs, metadata) ---
    # Opt-in. Our ``SWTEAM_LANGSMITH_*`` names win, then the SDK's own ``LANGSMITH_*`` /
    # legacy ``LANGCHAIN_*`` env vars, so either configuration style works. When on,
    # ``observability.configure_langsmith`` exports the canonical vars the SDK reads.
    langsmith_tracing: bool = field(
        default_factory=lambda: _env_bool(
            "SWTEAM_LANGSMITH_TRACING",
            _env_bool("LANGSMITH_TRACING", _env_bool("LANGCHAIN_TRACING_V2", False)),
        )
    )
    langsmith_api_key: str = field(
        default_factory=lambda: _env(
            "SWTEAM_LANGSMITH_API_KEY", _env("LANGSMITH_API_KEY", _env("LANGCHAIN_API_KEY", ""))
        )
    )
    langsmith_project: str = field(
        default_factory=lambda: _env(
            "SWTEAM_LANGSMITH_PROJECT",
            _env("LANGSMITH_PROJECT", _env("LANGCHAIN_PROJECT", "software-team")),
        )
    )
    langsmith_endpoint: str = field(
        default_factory=lambda: _env(
            "SWTEAM_LANGSMITH_ENDPOINT", _env("LANGSMITH_ENDPOINT", _env("LANGCHAIN_ENDPOINT", ""))
        )
    )

    def model_for(self, role: str) -> str:
        """Return the model name for ``role`` based on its tier (coder vs narrative)."""
        tier = ROLE_TIERS.get(role, "narrative")
        return self.coder_model if tier == "coder" else self.narrative_model

    @property
    def search_enabled(self) -> bool:
        """Return whether web search is configured (not disabled/off/none)."""
        return self.search_provider not in ("", "none", "off", "disabled")

    @property
    def graph_recursion_limit(self) -> int:
        """A LangGraph superstep budget that scales with the feedback-loop caps.

        The review loop re-runs build -> (frontend) -> review and the fix loop re-runs
        test -> fix, so raising ``SWTEAM_MAX_REVIEW_ITERS`` / ``SWTEAM_MAX_FIX_ITERS`` can
        push the worst-case path past a fixed budget and abort a *healthy* run partway with
        a recursion error. Derive the limit from the caps (plus headroom for the fixed
        plan/deploy/document phases) so turning the caps up never starves the graph.

        Returns:
            The recursion limit to pass to ``graph.invoke``.
        """
        return 40 + self.max_review_iters * 4 + self.max_fix_iters * 3


def repo_root() -> Path:
    """Return the repository root (three parents up from this file)."""
    return Path(__file__).resolve().parents[2]


_load_dotenv()
SETTINGS = Settings()
