"""🧭 Product Manager / Product Owner.

Decides *what* to build and *why*. Turns the input spec into user stories, Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog — the contract the rest of the
team builds against.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..skills.common.authoring import extract_section, split_at_heading
from ..skills.registry import skill_names
from ..state import TeamState
from .base import generate, output_dir, relpath, with_skills

ROLE = "product_manager"

SYSTEM = """You are a pragmatic Product Manager on a cross-functional software team.
You convert raw specs into clear, buildable requirements. You write concise user
stories in the form 'As a <role>, I want <goal> so that <value>', concrete Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog. You do not write code.
Output GitHub-flavoured markdown only."""

DOCS_SYSTEM = """You are a Product Manager writing end-user documentation for a shipped
release. You produce a User Manual — for each feature, what it does and the step-by-step
way to use it, in plain language for non-technical users — followed by concise Release
Notes grouped as Added / Changed / Fixed. Use a top-level '## Release Notes' heading for
the release-notes section. Output GitHub-flavoured markdown only."""


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


def product_manager_docs_node(state: TeamState) -> TeamState:
    """Turn the shipped features into an end-user manual and release notes."""
    ui.announce(
        ROLE,
        "document",
        "Writing the user manual and release notes",
        ["write-user-manual", "track-metrics"],
    )
    user = (
        "Write end-user documentation for this shipped release. Produce a '## User Manual' "
        "section (how to use each feature, step by step, in plain language) followed by a "
        "'## Release Notes' section grouped as Added / Changed / Fixed.\n\n"
        f"### User stories\n{state.get('user_stories', '')}\n\n"
        f"### Acceptance criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"### API surface\n{state.get('api_spec', '')}\n"
    )
    doc = generate(
        "product_manager_docs",
        with_skills(DOCS_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest user manual and release notes writing best practices 2026",
        ],
    )

    # Peel the trailing Release Notes section into its own conventional file.
    manual, release_notes = split_at_heading(doc, "Release Notes")
    out = output_dir(state)
    written = [filesystem.write_doc(out, "user_manual.md", manual)]
    if release_notes:
        written.append(filesystem.write_doc(out, "release_notes.md", release_notes))
    ui.written(relpath(state, written))

    return {
        "user_manual": manual,
        "release_notes": release_notes,
        "current_phase": "document",
    }
