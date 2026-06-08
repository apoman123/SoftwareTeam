"""LangSmith observability — tracing, named runs, and rich run metadata.

LangSmith is wired in three layers:

* ``configure_langsmith`` turns tracing on by exporting the canonical ``LANGSMITH_*`` (and
  legacy ``LANGCHAIN_*``) environment variables the LangChain/LangGraph SDK reads, from this
  project's settings — so a single ``SWTEAM_LANGSMITH_TRACING=true`` (plus an API key)
  lights up tracing for the whole pipeline with no per-call code.
* ``run_config`` builds a ``RunnableConfig`` that names and tags each run (the graph run and
  every character's LLM call), so the LangSmith trace tree is readable and filterable per
  character / phase / mode, and ready for monitoring, datasets and evaluation.
* ``traceable`` decorates non-LLM steps (e.g. web research) so they appear as child runs in
  the same trace. It degrades to a no-op decorator if ``langsmith`` is not installed.

Tracing is fully opt-in: with it disabled these helpers are cheap no-ops, so the team runs
exactly as before (and in ``--dry-run``) without LangSmith.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .config import SETTINGS

try:  # langsmith ships with langchain, but degrade gracefully if it is ever absent.
    from langsmith import traceable as _traceable
except Exception:  # noqa: BLE001 - observability must never break a run

    def _traceable(*d_args: Any, **d_kwargs: Any) -> Any:
        """No-op stand-in for ``langsmith.traceable`` when langsmith is unavailable."""
        if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
            return d_args[0]

        def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return _decorator


traceable = _traceable


def configure_langsmith() -> bool:
    """Enable LangSmith tracing from settings by exporting the SDK's environment variables.

    Reads the resolved ``langsmith_*`` settings and, when tracing is on, exports both the
    current ``LANGSMITH_*`` names and their legacy ``LANGCHAIN_*`` aliases so any SDK version
    activates. Safe to call once at startup, before the graph runs.

    Returns:
        True if tracing was enabled, else False.
    """
    if not SETTINGS.langsmith_tracing:
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_PROJECT"] = SETTINGS.langsmith_project
    os.environ["LANGCHAIN_PROJECT"] = SETTINGS.langsmith_project
    if SETTINGS.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = SETTINGS.langsmith_api_key
        os.environ["LANGCHAIN_API_KEY"] = SETTINGS.langsmith_api_key
    if SETTINGS.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = SETTINGS.langsmith_endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = SETTINGS.langsmith_endpoint
    return True


def run_config(
    name: str,
    *,
    tags: list[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a ``RunnableConfig`` that names, tags and annotates a run for LangSmith.

    Args:
        name: The run name shown in the LangSmith trace (e.g. the character/role).
        tags: Extra tags to attach (``"software-team"`` is always included).
        metadata: Extra key/value metadata to attach to the run.

    Returns:
        A config dict suitable for ``Runnable.ainvoke``/``astream`` or ``graph.ainvoke``.
    """
    run_metadata: dict[str, Any] = {"swteam.provider": SETTINGS.llm_provider}
    if metadata:
        run_metadata.update(metadata)
    return {
        "run_name": name,
        "tags": ["software-team", *(tags or [])],
        "metadata": run_metadata,
    }
