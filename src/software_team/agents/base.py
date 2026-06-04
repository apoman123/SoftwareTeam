"""Shared helpers for every character node.

A node typically: (1) renders a prompt from current team state, (2) asks its role's LLM
(or the dry-run stub) for an artifact, (3) persists the artifact via skills, and (4)
returns a state delta. `generate` centralises the LLM call so all characters behave
consistently and remain dry-run aware.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..llm import build_llm
from ..skills.registry import guidance_for


def with_skills(persona: str, character: str) -> str:
    """Compose a character's persona with the best-practice guidance from its skills."""
    guidance = guidance_for(character)
    if not guidance:
        return persona
    return f"{persona}\n\nApply these skills and the technique behind each:\n{guidance}"


def generate(role: str, system_prompt: str, user_prompt: str, state: dict) -> str:
    """Run one LLM turn for `role` and return its text content."""
    llm = build_llm(role, dry_run=state.get("dry_run", False))
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    resp = llm.invoke(messages)
    if isinstance(resp, AIMessage):
        return resp.content if isinstance(resp.content, str) else str(resp.content)
    return getattr(resp, "content", str(resp))


def output_dir(state: dict) -> str:
    return state.get("output_dir", "workspace")


def relpath(state: dict, abs_paths: list[str]) -> list[str]:
    """Make absolute written paths nice to display (relative to the workspace)."""
    base = Path(output_dir(state)).resolve()
    out = []
    for p in abs_paths:
        try:
            out.append(os.path.relpath(p, base))
        except ValueError:
            out.append(p)
    return out
