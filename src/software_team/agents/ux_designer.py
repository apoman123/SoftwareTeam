"""🎨 UI/UX Designer.

Owns look & feel and the user's journey. Describes the UI and the user experience in
words for the Tech Lead — user flows, screen layouts, and component/state specs derived
from the PM's stories. It never draws: no wireframes, ASCII art, diagrams, or images. For
pure backend/API work this role keeps it lightweight (a reference client + flow), as a
real team would.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..skills.registry import skill_names
from ..state import TeamState
from .base import feature_brief, generate, output_dir, relpath, with_skills

ROLE = "ux_designer"

SYSTEM = """You are a UI/UX Designer on a cross-functional team. You hand the Tech Lead a
written description of the UI and the user experience — you never draw. Produce no
wireframes, ASCII art, diagrams, or images; describe each screen's layout, content
hierarchy, and primary action in words instead. You map the user flow and call out
empty/error/loading states, and you specify each component's states, validation, and
copy. When sample images are provided (mock-ups, screenshots, or brand references), study
them and ground your description in what they show — layout, hierarchy, colour/typography
cues, and components — and note where the spec text and the images differ. If the product
is an API or backend service, keep the UX minimal: describe the primary user journey and a
small reference client. Output markdown only."""


async def ux_designer_node(state: TeamState) -> TeamState:
    """Describe the user flow, screen layouts, and component/state specs for the Tech Lead.

    Works from the PM's user stories and writes a written UX description (no drawings) to
    ``docs/ux_design.md`` so the Tech Lead can design the architecture against it.

    Args:
        state: The shared team state (reads the PM stories; carries dry-run mode and the
            output directory).

    Returns:
        A state delta with the rendered ``ux_design`` markdown and the current phase.
    """
    images = state.get("spec_images") or []
    headline = "Describing the UI and UX design for the tech lead"
    if images:
        headline += f" (with {len(images)} sample image(s) from the spec)"
    ui.announce(ROLE, "plan", headline, skill_names(ROLE))

    image_note = (
        "\n\nThe stakeholder provided sample image(s) below (mock-ups / screenshots / brand "
        "references). Study them and ground your description in what they show."
        if images
        else ""
    )
    user = (
        "Based on these product requirements, describe the UX in words for the Tech "
        "Lead. Do not draw anything — no wireframes, ASCII art, or diagrams.\n\n"
        f"{state.get('user_stories', '')}\n\n"
        "Produce markdown with:\n"
        "## User Flow (numbered, end-to-end; call out decision points and error paths)\n"
        "## Screen & Layout Description (describe each key screen in words: purpose, "
        "layout regions in reading order, content hierarchy, the single primary action, "
        "and responsive behaviour)\n"
        "## Component & State Specs (per component: default/hover/focus/loading/empty/"
        "error/success states, validation rules, and the exact empty and error copy)\n"
        "## Usability & Accessibility Notes (Nielsen heuristics, WCAG POUR, and the key "
        "UI quality checks)\n"
    ) + image_note + feature_brief(state)
    doc = await generate(
        ROLE,
        with_skills(SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest WCAG accessibility guidelines 2026",
            "current UX usability best practices 2026",
        ],
        images=list(images),
    )
    path = filesystem.write_doc(output_dir(state), "ux_design.md", doc)
    ui.written(relpath(state, [path]))
    return {"ux_design": doc, "current_phase": "plan"}
