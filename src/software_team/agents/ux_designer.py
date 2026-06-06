"""🎨 UI/UX Designer.

Owns look & feel and the user's journey. Produces user flows, ASCII/markdown
wireframes, and component/state specs from the PM's stories. For pure backend/API work
this role keeps it lightweight (a reference client + flow), as a real team would.
"""

from __future__ import annotations

from pathlib import Path

from .. import ui
from ..skills.common import design_system, filesystem
from ..skills.registry import skill_names
from ..state import TeamState
from .base import feature_brief, generate, output_dir, relpath, with_skills

ROLE = "ux_designer"

SYSTEM = """You are a UI/UX Designer on a cross-functional team. You map user flows and
sketch wireframes in ASCII/markdown (no image tools). You note empty/error/loading
states. You design to the recommended design system you are given — its page pattern,
visual style, semantic colour tokens, and font pairing — and you honour its
anti-patterns. If the product is an API or backend service, you keep the UX minimal:
describe the primary user journey and a small reference client. Output markdown only."""


def _design_query(state: TeamState) -> str:
    """Build the design-system query from the product brief.

    Args:
        state: The shared team state (uses the PM stories, then the raw spec).

    Returns:
        A short product/industry description for the design-system engine.
    """
    text = state.get("user_stories") or state.get("spec_text") or ""
    return " ".join(text.split())[:200]


def _project_name(state: TeamState) -> str:
    """Derive a readable project label for the design-system header.

    Uses the spec file's stem when the request came from a file; otherwise falls back to a
    generic label (a ``--prompt`` request has no file name).

    Args:
        state: The shared team state (carries the spec source path).

    Returns:
        A title-cased project name.
    """
    source = state.get("spec_path", "")
    stem = Path(source).stem
    if not stem or "<" in source:  # e.g. the "<prompt>" source label
        return "Project"
    return stem.replace("_", " ").replace("-", " ").title()


def ux_designer_node(state: TeamState) -> TeamState:
    """Design the user flow, ASCII wireframes, and component/state notes from the PM stories.

    First runs the deterministic design-system engine to recommend a page pattern, visual
    style, semantic colour tokens, typography and anti-patterns; persists it as
    ``docs/design_system.md`` and folds it into the brief so the UX is grounded in a
    concrete system rather than ad-hoc choices.
    """
    ui.announce(
        ROLE,
        "plan",
        "Designing the user flow and wireframes",
        skill_names(ROLE),
    )
    system_md = design_system.generate_design_system(_design_query(state), _project_name(state))
    ds_path = filesystem.write_doc(output_dir(state), "design_system.md", system_md)
    ui.written(relpath(state, [ds_path]))

    user = (
        "Based on these product requirements, design the UX.\n\n"
        f"{state.get('user_stories', '')}\n\n"
        "Design to this recommended design system (use its pattern, style, colour tokens, "
        "and font pairing; honour its anti-patterns):\n\n"
        f"{system_md}\n\n"
        "Produce markdown with:\n## User Flow (numbered)\n"
        "## Wireframe (ASCII inside a code block)\n## Component / State Notes\n"
    ) + feature_brief(state)
    doc = generate(
        ROLE,
        with_skills(SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest WCAG accessibility guidelines 2026",
            "current UX usability best practices 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "ux_design.md", doc)
    ui.written(relpath(state, [path]))
    return {"design_system": system_md, "ux_design": doc, "current_phase": "plan"}
