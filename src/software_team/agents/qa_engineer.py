"""🧪 QA Engineer / SDET.

Gets involved early (deriving test cases from acceptance criteria), then authors
end-to-end tests and actually runs the suite against the built project — this is the
quality gate that can send work back to the engineer.
"""

from __future__ import annotations

import asyncio

from .. import ui
from ..skills.common import filesystem, shell
from ..skills.registry import skill_names
from ..state import TeamState
from .base import (
    emit_files,
    feature_brief,
    generate,
    output_dir,
    relpath,
    stack_hint,
    with_skills,
)

ROLE = "qa_engineer"

PLAN_SYSTEM = """You are a QA Engineer / SDET. From acceptance criteria you derive
explicit, traceable test cases (TC-n -> US-n), enumerate edge cases and failure modes,
and sketch a performance/load scenario. Output markdown only."""

E2E_SYSTEM = """You are an SDET writing automated end-to-end / API tests. Use the test
framework idiomatic to the project's stack (e.g. pytest + FastAPI TestClient for Python,
Jest/Supertest for Node.js, `go test` for Go) and make the suite runnable with that
stack's standard test command. Cover the happy path and edge cases (invalid input, missing
resources). Emit each test file as:
<<<FILE tests/<test file for the stack> >>>
<contents>
<<<END>>>"""

REPORT_SYSTEM = """You are a QA Engineer / SDET writing the test report. Summarise the
coverage (which test cases map to which user stories, unit vs end-to-end), the result of
the latest run (pass/fail and how to reproduce it), and the residual risks or gaps. Be
honest about what is untested. Output markdown only."""


async def qa_planning_node(state: TeamState) -> TeamState:
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
    ) + feature_brief(state)
    doc = await generate(
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


async def qa_test_node(state: TeamState) -> TeamState:
    """Author E2E tests, run the full suite, and report whether it passed (the quality gate)."""
    ui.announce(
        ROLE,
        "deploy",
        "Writing E2E tests and running the suite against Staging",
        skill_names(ROLE),
    )
    out = output_dir(state)

    # 1) Author E2E tests from the plan + the built code, in the project's stack.
    listing = "\n".join(state.get("source_files", {}).keys())
    user = (
        "Write end-to-end tests for this project using its stack's test framework.\n\n"
        f"### Tech Stack\n{state.get('tech_stack', '')}\n\n"
        f"### Test plan\n{state.get('test_plan', '')}\n\n"
        f"### Files in the project\n{listing}\n"
    ) + feature_brief(state)
    e2e_files = await emit_files(
        state,
        model_role=ROLE,
        character=ROLE,
        system_prompt=E2E_SYSTEM,
        user_prompt=user,
        research_queries=[
            "latest end-to-end and API testing frameworks for "
            f"{stack_hint(state) or 'web services'} 2026",
        ],
    )

    # 2) Run every component's suite (backend at the root, plus frontend/ when present).
    #    Install each component's deps first (live runs) so its third-party imports resolve;
    #    offloaded to a thread so the (blocking) subprocess run never stalls the event loop.
    outcome = await asyncio.to_thread(
        shell.run_test_suites, out, install=not state.get("dry_run", False)
    )
    passed = outcome.passed
    verdict = "[green]passed[/green]" if passed else "[red]failed[/red]"
    ran = ", ".join(run.component for run in outcome.runs) or "none"
    skipped = f"; skipped: {', '.join(outcome.skipped)}" if outcome.skipped else ""
    ui.note(f"tests → {verdict} (ran: {ran}{skipped})")

    return {
        "source_files": e2e_files,
        "test_results": outcome.summary(),
        "tests_passed": passed,
        "current_phase": "deploy",
    }


async def qa_report_node(state: TeamState) -> TeamState:
    """Compile the test report: coverage, the latest run's result, and residual risk."""
    ui.announce(ROLE, "document", "Compiling the test report", ["write-test-report"])
    test_files = "\n".join(path for path in sorted(state.get("source_files", {})) if "test" in path)
    user = (
        "Write the test report for this project.\n\n"
        f"### Test plan\n{state.get('test_plan', '')}\n\n"
        f"### Test files\n{test_files}\n\n"
        f"### Latest run result (tests_passed={state.get('tests_passed', False)})\n"
        f"{state.get('test_results', '')}\n"
    ) + feature_brief(state)
    doc = await generate(
        "qa_report",
        with_skills(REPORT_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            "latest software test reporting and coverage best practices 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "test_report.md", doc)
    ui.written(relpath(state, [path]))
    return {"test_report": doc, "current_phase": "document"}
