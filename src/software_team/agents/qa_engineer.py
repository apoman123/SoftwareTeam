"""🧪 QA Engineer / SDET.

Gets involved early (deriving test cases from acceptance criteria), then authors
end-to-end tests and actually runs the suite against the built project — this is the
quality gate that can send work back to the engineer.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem, shell
from ..skills.registry import skill_names
from ..state import TeamState
from .base import emit_files, generate, output_dir, relpath, with_skills

ROLE = "qa_engineer"

PLAN_SYSTEM = """You are a QA Engineer / SDET. From acceptance criteria you derive
explicit, traceable test cases (TC-n -> US-n), enumerate edge cases and failure modes,
and sketch a performance/load scenario. Output markdown only."""

E2E_SYSTEM = """You are an SDET writing automated end-to-end / API tests with pytest.
Cover the happy path and edge cases (invalid input, missing resources). If the app uses
FastAPI, use its TestClient and guard the import with pytest.importorskip('fastapi').
Emit each test file as:
<<<FILE tests/test_e2e.py >>>
<contents>
<<<END>>>"""


def qa_planning_node(state: TeamState) -> TeamState:
    """Derive a traceable test plan (cases, edge cases, perf sketch) from acceptance criteria."""
    ui.announce(
        ROLE,
        "plan",
        "Deriving test cases and edge cases from acceptance criteria",
        ["design-test-cases", "analyze-edge-cases", "plan-performance-tests"],
    )
    user = (
        "Derive a test plan from these acceptance criteria.\n\n"
        f"{state.get('acceptance_criteria', '')}\n\n"
        "Sections: ## Test Cases, ## Edge Cases, ## Performance / Load (sketch)."
    )
    doc = generate(
        "qa_planning",
        with_skills(PLAN_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest software test design techniques and QA best practices 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "test_plan.md", doc)
    ui.written(relpath(state, [path]))
    return {"test_plan": doc, "current_phase": "plan"}


def qa_test_node(state: TeamState) -> TeamState:
    """Author E2E tests, run the full suite, and report whether it passed (the quality gate)."""
    ui.announce(
        ROLE,
        "deploy",
        "Writing E2E tests and running the suite against Staging",
        skill_names(ROLE),
    )
    out = output_dir(state)

    # 1) Author E2E tests from the plan + the built code.
    listing = "\n".join(state.get("source_files", {}).keys())
    user = (
        "Write end-to-end tests for this project.\n\n"
        f"### Test plan\n{state.get('test_plan', '')}\n\n"
        f"### Files in the project\n{listing}\n"
    )
    e2e_files = emit_files(
        state,
        model_role=ROLE,
        character=ROLE,
        system_prompt=E2E_SYSTEM,
        user_prompt=user,
        research_queries=[
            "latest pytest and FastAPI TestClient API 2026",
        ],
    )

    # 2) Run the whole suite.
    result = shell.run_pytest(out)
    passed = result.ok
    verdict = "[green]passed[/green]" if passed else "[red]failed[/red]"
    ui.note(f"pytest exit={result.returncode} → {verdict}")

    return {
        "source_files": e2e_files,
        "test_results": result.summary(),
        "tests_passed": passed,
        "current_phase": "deploy",
    }
