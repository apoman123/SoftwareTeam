"""Shared helpers for every character node.

A node typically: (1) renders a prompt from the current team state, (2) asks its role's
LLM (or the dry-run stub) for an artifact, (3) persists the artifact via skills, and (4)
returns a state delta. ``generate`` centralises the single LLM turn and ``emit_files``
centralises the generate-parse-persist cycle used by the code/artifact-producing nodes,
so every character behaves consistently and stays dry-run aware.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .. import ui
from ..llm import build_llm
from ..skills.common import filesystem, search
from ..skills.common.authoring import parse_file_blocks
from ..skills.registry import guidance_for
from ..state import FEATURE_MODE, TeamState


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


def research(state: TeamState, queries: list[str]) -> str:
    """Fetch the latest info from the web for ``queries`` and return a context block.

    Best-effort and side-effect free for the run: a no-op in dry-run or when search is
    disabled, and silent on any backend/network failure. The returned text is meant to be
    appended to a character's prompt so it can ground its work in current facts.

    Args:
        state: The shared team state (used to detect dry-run mode).
        queries: The search queries to run.

    Returns:
        A formatted block of search digests, or an empty string when nothing is found.
    """
    if state.get("dry_run") or not queries:
        return ""

    blocks: list[str] = []
    for query in queries:
        digest = search.web_search(query)
        if digest:
            blocks.append(f"#### Results for: {query}\n{digest}")
    if not blocks:
        return ""

    ui.note(f"web search: gathered latest info for {len(blocks)} of {len(queries)} queries")
    return "\n\n".join(blocks)


def generate(
    role: str,
    system_prompt: str,
    user_prompt: str,
    state: TeamState,
    research_queries: list[str] | None = None,
) -> str:
    """Run one LLM turn for ``role`` and return its text content.

    When ``research_queries`` are given (and not in dry-run), the latest matching web
    results are folded into the prompt so the character can use current information.

    Args:
        role: The tier key that selects the model (e.g. "software_engineer").
        system_prompt: The system message content.
        user_prompt: The human message content.
        state: The shared team state (carries dry-run mode).
        research_queries: Optional web queries to ground the generation.

    Returns:
        The model's response text.
    """
    findings = research(state, research_queries or [])
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
    response = llm.invoke(messages)
    if isinstance(response, AIMessage):
        return response.content if isinstance(response.content, str) else str(response.content)
    return getattr(response, "content", str(response))


def emit_files(
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
    text = generate(
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
