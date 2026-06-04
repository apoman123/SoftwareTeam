"""LLM factory.

Builds a ChatOllama instance for a given role. In `--dry-run` mode it returns a
deterministic stub that produces canned, structurally-valid artifacts, so the whole
graph (and all file generation) can be exercised with no model server running.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage

from .config import SETTINGS
from .dryrun import canned_response


def build_llm(role: str, dry_run: bool = False) -> Any:
    """Return a chat model for `role`.

    dry_run -> StubChatModel (no network). Otherwise a ChatOllama bound to the role's
    configured model.
    """
    if dry_run:
        return StubChatModel(role=role)

    # Imported lazily so --dry-run works even if langchain-ollama isn't installed.
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=SETTINGS.model_for(role),
        base_url=SETTINGS.ollama_host,
        temperature=SETTINGS.temperature,
    )


class StubChatModel(FakeListChatModel):
    """Offline stand-in for ChatOllama.

    It inspects the role + the last human message and returns a canned artifact so the
    pipeline can be verified end-to-end without Ollama. Inherits FakeListChatModel only
    for its interface; the response list is ignored in favour of `_call`.
    """

    role: str = "generic"

    def __init__(self, role: str = "generic", **kwargs: Any) -> None:
        super().__init__(responses=["stub"], **kwargs)
        # FakeListChatModel stores fields via pydantic; set after init.
        object.__setattr__(self, "role", role)

    @property
    def _llm_type(self) -> str:
        return "stub-chat-model"

    def _call(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> str:
        prompt = ""
        for m in reversed(messages):
            if getattr(m, "type", None) in ("human", "system"):
                prompt = str(m.content)
                break
        return canned_response(self.role, prompt)

    async def _acall(self, messages, stop=None, run_manager=None, **kwargs: Any) -> str:
        return self._call(messages, stop=stop, run_manager=run_manager, **kwargs)

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> AIMessage:  # type: ignore[override]
        msgs = input if isinstance(input, list) else [input]
        # Normalise (string prompt -> human message handled by base), so reuse _call.
        from langchain_core.prompt_values import PromptValue

        if isinstance(input, PromptValue):
            msgs = input.to_messages()
        elif isinstance(input, str):
            from langchain_core.messages import HumanMessage

            msgs = [HumanMessage(content=input)]
        return AIMessage(content=self._call(msgs))
