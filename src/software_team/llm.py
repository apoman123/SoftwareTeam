"""LLM factory.

Builds a chat model for a given role from whichever provider is configured
(``SWTEAM_LLM_PROVIDER``): a local **Ollama** server, the **OpenAI** API (or any
OpenAI-compatible endpoint), the **Anthropic** API (Claude), **Google Gemini**
(google-genai), or a local GGUF model via **llama.cpp**. In `--dry-run` mode it returns a
deterministic stub that produces canned, structurally-valid artifacts, so the whole graph
(and all file generation) can be exercised with no model server, provider package, or
network running.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompt_values import PromptValue

from .config import SETTINGS
from .dryrun import canned_response


def build_llm(role: str, dry_run: bool = False) -> Any:
    """Return a chat model for `role`.

    dry_run -> StubChatModel (no network). Otherwise the chat model for the configured
    provider, bound to the role's tier model. Provider packages are imported lazily so a
    dry run (and the other providers) work without every backend installed.
    """
    if dry_run:
        return StubChatModel(role=role)

    provider = SETTINGS.llm_provider
    model = SETTINGS.model_for(role)
    builder = _BUILDERS.get(provider)
    if builder is None:  # pragma: no cover - guarded by config normalisation
        raise ValueError(
            f"Unknown SWTEAM_LLM_PROVIDER '{provider}'. Choose one of: {', '.join(_BUILDERS)}."
        )
    return builder(model)


def _build_ollama(model: str) -> Any:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as e:  # pragma: no cover - import guard
        raise ImportError(
            "The 'ollama' provider needs langchain-ollama. Install it with "
            "`uv sync` (it is a base dependency)."
        ) from e

    return ChatOllama(
        model=model,
        base_url=SETTINGS.ollama_host,
        temperature=SETTINGS.temperature,
        # Ollama spells the generation cap "num_predict"; bounds each turn so a runaway
        # local model can't generate to the end of its context and stall the run.
        num_predict=SETTINGS.max_tokens,
    )


def _build_openai(model: str) -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ImportError(
            "The 'openai' provider needs langchain-openai. Install it with "
            "`uv sync --extra openai`."
        ) from e

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": SETTINGS.temperature,
        # Bound generation and add a deadline so a local OpenAI-compatible server (llama.cpp,
        # vLLM, LM Studio…) that loops or wedges fails fast instead of hanging the workflow.
        "max_tokens": SETTINGS.max_tokens,
        "timeout": SETTINGS.request_timeout,
    }
    if SETTINGS.openai_api_key:
        kwargs["api_key"] = SETTINGS.openai_api_key
    if SETTINGS.openai_base_url:
        # Lets the same provider drive any OpenAI-compatible server (vLLM, LM Studio…).
        kwargs["base_url"] = SETTINGS.openai_base_url
    return ChatOpenAI(**kwargs)


# Anthropic's Opus 4.7+ models removed the sampling parameters: sending ``temperature``
# (or top_p/top_k) returns HTTP 400. Only forward temperature to models that still accept
# it. See https://docs.claude.com/en/docs/about-claude/models/migration-guide.
_ANTHROPIC_NO_TEMPERATURE_PREFIXES = ("claude-opus-4-8", "claude-opus-4-7")


def _anthropic_accepts_temperature(model: str) -> bool:
    """Return whether ``model`` accepts a ``temperature`` parameter.

    Args:
        model: The Anthropic model id (e.g. "claude-opus-4-8").

    Returns:
        False for Opus 4.7/4.8 (which reject sampling params with a 400), else True.
    """
    return not model.startswith(_ANTHROPIC_NO_TEMPERATURE_PREFIXES)


def _build_anthropic(model: str) -> Any:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        raise ImportError(
            "The 'anthropic' provider needs langchain-anthropic. Install it with "
            "`uv sync --extra anthropic`."
        ) from e

    kwargs: dict[str, Any] = {
        "model": model,
        # Anthropic requires a max_tokens; honour the shared cap and add a request deadline.
        "max_tokens": SETTINGS.max_tokens,
        "timeout": SETTINGS.request_timeout,
    }
    if SETTINGS.anthropic_api_key:
        kwargs["api_key"] = SETTINGS.anthropic_api_key
    # Opus 4.7+ reject temperature/top_p/top_k (HTTP 400); only set it where accepted.
    if _anthropic_accepts_temperature(model):
        kwargs["temperature"] = SETTINGS.temperature
    return ChatAnthropic(**kwargs)


def _build_google(model: str) -> Any:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as e:
        raise ImportError(
            "The 'google' provider needs langchain-google-genai. Install it with "
            "`uv sync --extra google`."
        ) from e

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": SETTINGS.temperature,
        # Gemini spells the cap "max_output_tokens"; add a request deadline too.
        "max_output_tokens": SETTINGS.max_tokens,
        "timeout": SETTINGS.request_timeout,
    }
    if SETTINGS.google_api_key:
        kwargs["google_api_key"] = SETTINGS.google_api_key
    return ChatGoogleGenerativeAI(**kwargs)


def _build_llama_cpp(model: str) -> Any:
    if not model:
        raise ValueError(
            "The 'llama_cpp' provider needs a path to a local .gguf model. Set "
            "SWTEAM_CODER_MODEL (and SWTEAM_NARRATIVE_MODEL) to the file path(s)."
        )
    try:
        from langchain_community.chat_models import ChatLlamaCpp
    except ImportError as e:
        raise ImportError(
            "The 'llama_cpp' provider needs langchain-community and llama-cpp-python. "
            "Install them with `uv sync --extra llama-cpp`."
        ) from e

    return ChatLlamaCpp(
        model_path=model,
        temperature=SETTINGS.temperature,
        # In-process llama.cpp: cap tokens so a runaway/looping generation always terminates.
        max_tokens=SETTINGS.max_tokens,
    )


_BUILDERS = {
    "ollama": _build_ollama,
    "openai": _build_openai,
    "anthropic": _build_anthropic,
    "google": _build_google,
    "llama_cpp": _build_llama_cpp,
}


class StubChatModel(FakeListChatModel):
    """Offline stand-in for ChatOllama.

    It inspects the role + the last human message and returns a canned artifact so the
    pipeline can be verified end-to-end without Ollama. Inherits FakeListChatModel only
    for its interface; the response list is ignored in favour of `_call`.
    """

    role: str = "generic"

    def __init__(self, role: str = "generic", **kwargs: Any) -> None:
        """Initialise the stub for ``role`` (selects which canned artifact to return)."""
        super().__init__(responses=["stub"], role=role, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "stub-chat-model"

    def _call(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> str:
        prompt = ""
        for message in reversed(messages):
            if getattr(message, "type", None) in ("human", "system"):
                prompt = str(message.content)
                break
        return canned_response(self.role, prompt)

    async def _acall(self, messages, stop=None, run_manager=None, **kwargs: Any) -> str:
        return self._call(messages, stop=stop, run_manager=run_manager, **kwargs)

    def invoke(self, value: Any, config: Any = None, **kwargs: Any) -> AIMessage:  # type: ignore[override]
        """Return a canned ``AIMessage`` for ``value`` (messages, prompt value, or string)."""
        if isinstance(value, PromptValue):
            messages = value.to_messages()
        elif isinstance(value, str):
            messages = [HumanMessage(content=value)]
        else:
            messages = value if isinstance(value, list) else [value]
        return AIMessage(content=self._call(messages))
