"""Shared helpers for every character node.

A node typically: (1) renders a prompt from the current team state, (2) asks its role's
LLM (or the dry-run stub) for an artifact, (3) persists the artifact via skills, and (4)
returns a state delta. ``generate`` centralises the single LLM turn and ``emit_files``
centralises the generate-parse-persist cycle used by the code/artifact-producing nodes,
so every character behaves consistently and stays dry-run aware.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .. import observability, ui
from ..llm import build_llm
from ..skills.common import filesystem, search
from ..skills.common.authoring import parse_file_blocks
from ..skills.registry import guidance_for
from ..state import FEATURE_MODE, TeamState

# Per-query and total caps (characters) on the web-research block folded into a prompt.
# Prompt-processing (prefill) is the dominant cost on a local CPU-offloaded model, and it
# grows with every token of context, so an unbounded pile of search snippets slows *every*
# turn. Bounding the research keeps the grounding useful while protecting prefill latency.
_RESEARCH_PER_QUERY_CHARS = 1200
_RESEARCH_TOTAL_CHARS = 4000


def with_skills(persona: str, character: str) -> str:
    """Compose a character's persona with the best-practice guidance from its skills.

    Args:
        persona: The character's base system prompt.
        character: The character key whose SKILL.md guidance should be appended.

    Returns:
        The persona, optionally extended with the composed skill guidance.
    """
    guidance = guidance_for(character)
    if not guidance:
        return persona
    return f"{persona}\n\nApply these skills and the technique behind each:\n{guidance}"


def feature_brief(state: TeamState) -> str:
    """Return the existing-software context block for an incremental feature run.

    In ``build`` mode (the default) this is empty, so every node behaves exactly as it
    does for a greenfield run. In ``feature`` mode it returns the rendered baseline digest
    of the already-developed software plus the instruction to integrate the requested
    feature into it — extend and modify what exists rather than rebuild the project. Nodes
    append it to their user prompt so the framing is consistent across the whole team.

    Args:
        state: The shared team state (carries the mode and the rendered baseline).

    Returns:
        The context block to append to a node's prompt, or "" in build mode.
    """
    if state.get("mode") != FEATURE_MODE:
        return ""
    return (
        "\n\nThe software below already exists and is in production. Treat the request "
        "above as a NEW feature to integrate into it: build on what is there, change only "
        "what the feature needs, preserve existing behaviour and unchanged files, and do "
        "not rebuild the project from scratch.\n\n" + state.get("baseline", "")
    )


# Languages, frameworks and runtimes recognised in a free-text spec so that — before the
# Tech Lead has chosen a stack — research and code generation can ground in the technology
# the stakeholder actually asked for instead of a hardcoded default. Lower-cased; matched
# as whole tokens (see ``_requested_stack``). Order longest/most-specific first so e.g.
# "javascript" wins over "java" and "golang" over "go".
_KNOWN_TECH: tuple[str, ...] = (
    "node.js",
    "nodejs",
    "typescript",
    "javascript",
    "nestjs",
    "next.js",
    "express",
    "react",
    "angular",
    "svelte",
    "vue",
    "deno",
    "bun",
    "fastapi",
    "django",
    "flask",
    "python",
    "golang",
    "go",
    "gin",
    "rust",
    "actix",
    "axum",
    "spring",
    "kotlin",
    "ktor",
    "scala",
    "java",
    "asp.net",
    ".net",
    "c#",
    "c++",
    "laravel",
    "rails",
    "ruby",
    "php",
    "phoenix",
    "elixir",
)


def _requested_stack(state: TeamState) -> str:
    """Detect any language/framework the stakeholder named in the spec or stories.

    Scans the raw spec and the PM's stories (case-insensitively) for known technologies so
    a stated constraint such as "use Node.js" survives even before the Tech Lead has picked
    a stack. Matches whole tokens so "go" is not found inside "goal".

    Args:
        state: The shared team state (reads ``spec_text`` then ``user_stories``).

    Returns:
        The recognised technologies, space-joined in first-seen order, or "" if none.
    """
    text = f"{state.get('spec_text', '')}\n{state.get('user_stories', '')}".lower()
    found: list[str] = []
    for tech in _KNOWN_TECH:
        # Bound by alphanumerics only so "go" is not found inside "goal"/"google" but a
        # token at a sentence end ("Express.") or before punctuation still matches.
        pattern = rf"(?<![a-z0-9]){re.escape(tech)}(?![a-z0-9])"
        if tech not in found and re.search(pattern, text):
            found.append(tech)
    return " ".join(found)


def stack_hint(state: TeamState) -> str:
    """Return a short label of the project's stack to ground research and code generation.

    Prefers the Tech Lead's chosen ``tech_stack`` once it exists; otherwise falls back to
    any stack the stakeholder explicitly requested in the spec. Returns "" when neither is
    known yet, so callers stay language-agnostic and supply their own generic fallback.

    Args:
        state: The shared team state.

    Returns:
        A concise stack descriptor (<= 120 chars), or "" when none is known yet.
    """
    stack = (state.get("tech_stack") or "").strip()
    if stack:
        first_line = next((line.strip(" -*#") for line in stack.splitlines() if line.strip()), "")
        return (first_line or stack)[:120]
    return _requested_stack(state)


@observability.traceable(run_type="tool", name="web_research")
async def research(state: TeamState, queries: list[str]) -> str:
    """Fetch the latest info from the web for ``queries`` concurrently and return a block.

    The queries are independent network calls, so they run in parallel (each blocking
    ``web_search`` is dispatched to a worker thread and awaited together) instead of one
    after another — the research step then takes about as long as its slowest query, not
    their sum. Each digest is truncated and the whole block is capped (see the module
    constants) to keep prefill fast on a local model.

    Best-effort and side-effect free for the run: a no-op in dry-run or when search is
    disabled, and silent on any backend/network failure. The returned text is meant to be
    appended to a character's prompt so it can ground its work in current facts.

    Args:
        state: The shared team state (used to detect dry-run mode).
        queries: The search queries to run.

    Returns:
        A formatted, size-bounded block of search digests, or "" when nothing is found.
    """
    if state.get("dry_run") or not queries:
        return ""

    digests = await asyncio.gather(*(asyncio.to_thread(search.web_search, q) for q in queries))

    blocks: list[str] = []
    used = 0
    for query, digest in zip(queries, digests, strict=True):
        if not digest:
            continue
        digest = digest[:_RESEARCH_PER_QUERY_CHARS]
        if used + len(digest) > _RESEARCH_TOTAL_CHARS:
            digest = digest[: _RESEARCH_TOTAL_CHARS - used]
        if not digest:
            break
        blocks.append(f"#### Results for: {query}\n{digest}")
        used += len(digest)
    if not blocks:
        return ""

    ui.note(f"web search: gathered latest info for {len(blocks)} of {len(queries)} queries")
    return "\n\n".join(blocks)


async def generate(
    role: str,
    system_prompt: str,
    user_prompt: str,
    state: TeamState,
    research_queries: list[str] | None = None,
) -> str:
    """Run one async LLM turn for ``role`` and return its text content.

    The turn is awaited (``astream``/``ainvoke``), so a node never blocks the event loop
    while the model works — on a tool-calling backend that supports concurrency the team can
    overlap independent calls. When ``research_queries`` are given (and not in dry-run), the
    latest matching web results are gathered concurrently and folded into the prompt so the
    character can use current information. The turn is named/tagged for LangSmith so it shows
    up per character in the trace.

    Args:
        role: The tier key that selects the model (e.g. "software_engineer").
        system_prompt: The system message content.
        user_prompt: The human message content.
        state: The shared team state (carries dry-run mode).
        research_queries: Optional web queries to ground the generation.

    Returns:
        The model's response text.
    """
    findings = await research(state, research_queries or [])
    if findings:
        user_prompt = (
            f"{user_prompt}\n\n"
            "### Latest information from the web (verify and use where relevant; "
            "prefer these current details over older recollection)\n"
            f"{findings}"
        )

    llm = build_llm(role, dry_run=state.get("dry_run", False))
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    config = observability.run_config(
        role,
        tags=[role, state.get("current_phase", "")],
        metadata={
            "swteam.role": role,
            "swteam.phase": state.get("current_phase", ""),
            "swteam.mode": state.get("mode", "build"),
        },
    )
    return await _arun_turn(llm, messages, dry_run=state.get("dry_run", False), config=config)


def _content_text(content: Any) -> str:
    """Flatten an LLM message/chunk ``content`` into plain text.

    Providers return ``content`` as a string, or as a list of content blocks (e.g. dicts
    carrying a ``text`` field — Anthropic does this while streaming). Normalise both to one
    string so the rest of the pipeline always works with text.

    Args:
        content: A message/chunk ``content`` (str, list of blocks, or other).

    Returns:
        The concatenated text, or "" when there is none.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
        return "".join(parts)
    return "" if content is None else str(content)


async def _arun_turn(
    llm: Any, messages: list[BaseMessage], *, dry_run: bool, config: dict[str, Any] | None = None
) -> str:
    """Execute one async chat turn, streaming the response unless in dry-run.

    Streaming is what keeps the run from *looking* idle on a slow local model: tokens are
    rendered as they arrive (continuous progress instead of a multi-minute silent block),
    and the HTTP read-timeout then bounds the gap *between* tokens rather than the whole
    response — so a slow but healthy generation no longer trips the deadline (only a truly
    wedged server does, after the timeout's worth of silence). Awaiting ``astream`` also
    frees the event loop between tokens. Falls back to a single ``ainvoke`` if the model
    cannot stream; the dry-run stub is synchronous and offline, so it just invokes.

    Args:
        llm: The chat model (a real provider client, or the dry-run stub).
        messages: The system + human messages for the turn.
        dry_run: Whether this is a dry run (skip streaming and the live progress display).
        config: Optional LangSmith run config (run name / tags / metadata) for the call.

    Returns:
        The model's full response text.
    """
    if not dry_run:
        try:
            pieces: list[str] = []
            chars = 0
            with ui.generating() as progress:
                async for chunk in llm.astream(messages, config=config):
                    piece = _content_text(getattr(chunk, "content", ""))
                    if not piece:
                        continue
                    pieces.append(piece)
                    chars += len(piece)
                    progress(chars)
            if pieces:
                return "".join(pieces)
            # An empty stream (rare; some OpenAI-compatible shims) — fall through to invoke.
        except (NotImplementedError, AttributeError):
            # Model doesn't support streaming — fall back to one blocking call.
            pass
        response = await llm.ainvoke(messages, config=config)
        return _content_text(getattr(response, "content", response))

    # Dry-run stub: synchronous, offline, instant — no streaming display needed.
    response = llm.invoke(messages)
    return _content_text(getattr(response, "content", response))


async def emit_files(
    state: TeamState,
    *,
    model_role: str,
    character: str,
    system_prompt: str,
    user_prompt: str,
    research_queries: list[str] | None = None,
) -> dict[str, str]:
    """Generate a file-block response, persist the files, and report them.

    This is the shared generate -> parse -> write cycle used by every node that produces
    source/config files (software engineer, QA E2E tests, DevOps artifacts).

    Args:
        state: The shared team state (carries dry-run mode and the output directory).
        model_role: The tier key that selects the model (e.g. "devops_ci").
        character: The character key whose skill guidance grounds the system prompt.
        system_prompt: The character's base persona/system instructions.
        user_prompt: The task-specific instructions.
        research_queries: Optional web queries to ground the generation.

    Returns:
        A ``{relative_path: content}`` map of the files written; empty when the model
        emitted no file blocks.
    """
    text = await generate(
        model_role,
        with_skills(system_prompt, character),
        user_prompt,
        state,
        research_queries=research_queries,
    )
    files = parse_file_blocks(text)
    if files:
        ui.written(relpath(state, filesystem.write_files(output_dir(state), files)))
    else:
        ui.note("[yellow]no file blocks parsed from model output[/yellow]")
    return files


def output_dir(state: TeamState) -> str:
    """Return the run's output workspace directory, defaulting to ``workspace``."""
    return state.get("output_dir", "workspace")


def relpath(state: TeamState, abs_paths: list[str]) -> list[str]:
    """Make absolute written paths nice to display (relative to the workspace).

    Args:
        state: The shared team state (provides the workspace base directory).
        abs_paths: Absolute paths to relativise.

    Returns:
        The paths relative to the workspace, falling back to the original on failure.
    """
    base = Path(output_dir(state)).resolve()
    out = []
    for path in abs_paths:
        try:
            out.append(os.path.relpath(path, base))
        except ValueError:
            out.append(path)
    return out
