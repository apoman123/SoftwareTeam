"""🧭 Product Manager / Product Owner.

Decides *what* to build and *why*. Turns the input spec into user stories, Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog — the contract the rest of the
team builds against.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..skills.common.authoring import extract_section
from ..skills.registry import skill_names
from ..state import TeamState
from .base import generate, output_dir, relpath, with_skills

ROLE = "product_manager"

SYSTEM = """You are a pragmatic Product Manager on a cross-functional software team.
You convert raw specs into clear, buildable requirements. You write concise user
stories in the form 'As a <role>, I want <goal> so that <value>', concrete Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog. You do not write code.
Output GitHub-flavoured markdown only."""


def product_manager_node(state: TeamState) -> TeamState:
    """Turn the spec into user stories, Gherkin acceptance criteria, and a MoSCoW backlog."""
    ui.announce(
        ROLE,
        "plan",
        "Turning the spec into user stories, acceptance criteria and a prioritised backlog",
        skill_names(ROLE),
    )
    spec = state.get("spec_text", "")
    user = (
        "Here is the product spec / use-cases from the stakeholder:\n\n"
        f"{spec}\n\n"
        "Produce a markdown document with these sections:\n"
        "## Goal\n## User Stories (US-n, story format)\n"
        "## Acceptance Criteria (Gherkin) with a ```gherkin block\n"
        "## Prioritised Backlog (MoSCoW)\n"
    )
    doc = generate(
        ROLE,
        with_skills(SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest best practices for writing user stories and acceptance criteria 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "product_backlog.md", doc)
    ui.written(relpath(state, [path]))
    return {
        "user_stories": doc,
        "acceptance_criteria": extract_section(doc, "Acceptance Criteria") or doc,
        "backlog": extract_section(doc, "Prioritised Backlog (MoSCoW)")
        or extract_section(doc, "Prioritised Backlog")
        or doc,
        "current_phase": "plan",
    }
