"""🖥️ Frontend Engineer.

Builds the user-facing frontend from the UX description and the API contract, in the
frontend stack the architecture chose — but only when the project needs a UI (the
``needs_frontend`` capability flag; see ``triage``). Emits files under ``frontend/`` so the
UI sits alongside the backend service in the same workspace. It reuses the Software
Engineer's skill set (engineering foundation + write-code/write-unit-tests), since a
frontend engineer is still a software engineer; the node just focuses the prompt on the UI.
"""

from __future__ import annotations

from .. import ui
from ..skills.registry import skill_names
from ..state import FEATURE_MODE, TeamState
from .base import emit_files, feature_brief, stack_hint
from .software_engineer import FILE_PROTOCOL, _code_listing

ROLE = "frontend_engineer"

# Reuse the engineering skill set: a frontend engineer is still a software engineer.
SKILLS_CHARACTER = "software_engineer"

FRONTEND_SYSTEM = f"""You are a Frontend Engineer. You build the user-facing application
described by the UX, wired to the backend through the documented API contract. Implement it
in the frontend framework chosen in the architecture (e.g. React, Vue, Svelte) with its
standard tooling and a matching test setup. Put every file under a `frontend/` directory and
include the frontend dependency manifest (e.g. frontend/package.json). Build accessible,
responsive screens that match the UX and call the backend API; keep components small and
state handling clear. {FILE_PROTOCOL}"""


async def frontend_engineer_node(state: TeamState) -> TeamState:
    """Implement the frontend (under ``frontend/``) from the UX and the API contract.

    Reached only when ``needs_frontend`` is set, so pure API/backend or library projects
    skip it entirely. Emitted files merge into ``source_files`` so the Tech Lead reviews and
    QA tests the frontend alongside the backend.

    Args:
        state: The shared team state (reads UX, tech stack, API spec, acceptance criteria).

    Returns:
        A state delta with the written files merged into ``source_files``.
    """
    ui.announce(
        ROLE,
        "code",
        "Implementing the frontend from the UX and API contract",
        skill_names(SKILLS_CHARACTER),
    )
    user = (
        "Build the frontend for this product using the frontend stack chosen in the "
        "architecture. Put every file under `frontend/`.\n\n"
        f"### Tech Stack\n{state.get('tech_stack', '')}\n\n"
        f"### UX (screens, flows, components, states)\n{state.get('ux_design', '')}\n\n"
        "### Backend API contract (call the backend through this)\n"
        f"{state.get('api_spec') or state.get('architecture', '')}\n\n"
        f"### Acceptance Criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"{FILE_PROTOCOL}"
    )
    if state.get("mode") == FEATURE_MODE:
        user += (
            "\n\nThis is an existing codebase. Re-emit ONLY the frontend files you change to "
            "add the feature, plus any new files; do not touch unrelated files.\n\n"
            f"### Current source files\n{_code_listing(state.get('source_files', {}))}"
        )
    user += feature_brief(state)

    files = await emit_files(
        state,
        model_role=ROLE,
        character=SKILLS_CHARACTER,
        system_prompt=FRONTEND_SYSTEM,
        user_prompt=user,
        research_queries=[
            "latest setup, routing and testing for "
            f"{stack_hint(state) or 'a modern frontend framework'} 2026",
        ],
    )
    return {"source_files": files, "current_phase": "code"}
