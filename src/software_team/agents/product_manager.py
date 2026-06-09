"""🧭 Product Manager / Product Owner.

Decides *what* to build and *why*. Turns the input spec into user stories, Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog — the contract the rest of the
team builds against.
"""

from __future__ import annotations

from .. import ui
from ..config import SETTINGS
from ..skills.common import filesystem
from ..skills.common.authoring import extract_section, parse_list_items, split_at_heading
from ..skills.registry import skill_names
from ..state import TeamState
from .base import feature_brief, generate, output_dir, relpath, with_skills

ROLE = "product_manager"

# Used when the model emits no parseable feature plan: the team still builds the whole
# specification, just as a single feature (so the feature loop degenerates to one pass).
_FALLBACK_FEATURE = "Implement the full specification described in the acceptance criteria."

SYSTEM = """You are a pragmatic Product Manager on a cross-functional software team.
You convert raw specs into clear, buildable requirements. You write concise user
stories in the form 'As a <role>, I want <goal> so that <value>', concrete Gherkin
acceptance criteria, and a MoSCoW-prioritised backlog. You also break the work into a
'Feature Plan': an ordered list of small, independently buildable features (most foundational
first), because the team builds and reviews one feature at a time. You do not write code.
Output GitHub-flavoured markdown only."""

DOCS_SYSTEM = """You are a Product Manager writing end-user documentation for a shipped
release. You produce a User Manual — for each feature, what it does and the step-by-step
way to use it, in plain language for non-technical users — followed by concise Release
Notes grouped as Added / Changed / Fixed. Use a top-level '## Release Notes' heading for
the release-notes section. Output GitHub-flavoured markdown only."""


async def product_manager_node(state: TeamState) -> TeamState:
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
        "## Feature Plan (an ordered list of small, independently buildable features, most "
        "foundational first; the team builds and reviews them one at a time)\n"
    ) + feature_brief(state)
    doc = await generate(
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

    features = _parse_features(doc)
    ui.note(f"feature plan: [bold]{len(features)}[/bold] feature(s) to build one at a time")

    delta: TeamState = {
        "user_stories": doc,
        "acceptance_criteria": extract_section(doc, "Acceptance Criteria") or doc,
        "backlog": extract_section(doc, "Prioritised Backlog (MoSCoW)")
        or extract_section(doc, "Prioritised Backlog")
        or doc,
        "features": features,
        "feature_cursor": 0,
        "current_phase": "plan",
    }
    # Hand any sample images the spec shipped with to the UI/UX Designer (carried forward in
    # state so the designer can study them when describing the screens).
    images = state.get("spec_images") or []
    if images:
        ui.note(f"handing [bold]{len(images)}[/bold] sample image(s) to the UI/UX designer")
        delta["spec_images"] = list(images)
    return delta


def _parse_features(doc: str) -> list[str]:
    """Extract the ordered, buildable features from the backlog's ``## Feature Plan``.

    Falls back to a single feature covering the whole spec when the model emitted no
    parseable plan, and caps the list at ``SETTINGS.max_features`` (the configurable
    ``SWTEAM_MAX_FEATURES``) so the build loop always terminates within the graph's recursion
    budget.

    Args:
        doc: The Product Manager's full backlog markdown.

    Returns:
        At least one feature, in build order.
    """
    section = extract_section(doc, "Feature Plan") or ""
    features = parse_list_items(section)[: SETTINGS.max_features]
    return features or [_FALLBACK_FEATURE]


async def product_manager_docs_node(state: TeamState) -> TeamState:
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
    ) + feature_brief(state)
    doc = await generate(
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
