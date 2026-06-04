"""🎨 UI/UX Designer.

Owns look & feel and the user's journey. Produces user flows, ASCII/markdown
wireframes, and component/state specs from the PM's stories. For pure backend/API work
this role keeps it lightweight (a reference client + flow), as a real team would.
"""

from __future__ import annotations

from .. import ui
from ..skills import filesystem
from ..skills.registry import skill_names
from .base import generate, output_dir, relpath

ROLE = "ux_designer"

SYSTEM = """You are a UI/UX Designer on a cross-functional team. You map user flows and
sketch wireframes in ASCII/markdown (no image tools). You note empty/error/loading
states. If the product is an API or backend service, you keep the UX minimal: describe
the primary user journey and a small reference client. Output markdown only."""


def ux_designer_node(state: dict) -> dict:
    ui.announce(
        ROLE, "plan",
        "Designing the user flow and wireframes",
        skill_names(ROLE),
    )
    user = (
        "Based on these product requirements, design the UX.\n\n"
        f"{state.get('user_stories', '')}\n\n"
        "Produce markdown with:\n## User Flow (numbered)\n"
        "## Wireframe (ASCII inside a code block)\n## Component / State Notes\n"
    )
    doc = generate(ROLE, SYSTEM, user, state)
    path = filesystem.write_doc(output_dir(state), "ux_design.md", doc)
    ui.written(relpath(state, [path]))
    return {"ux_design": doc, "current_phase": "plan"}
