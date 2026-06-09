"""🧠 Tech Lead / Architect — also the team's supervisor.

Two responsibilities map to two graph nodes:
  * design  — choose the stack and define architecture, the API contract and DB schema.
  * review  — review the engineer's code and approve or request changes.

As supervisor it also owns the routing decisions (the `route_workflow` skill): whether
to loop back for changes/bug-fixes or advance to the next phase, bounded by iteration
caps so the pipeline always terminates.
"""

from __future__ import annotations

import asyncio

from .. import ui
from ..config import SETTINGS
from ..skills.common import filesystem, lint, shell
from ..skills.common.authoring import extract_fenced, extract_section
from ..state import TeamState
from .base import feature_brief, generate, output_dir, relpath, stack_hint, with_skills

ROLE = "tech_lead"

DESIGN_SYSTEM = """You are a Senior Tech Lead / Architect. You make pragmatic technology
choices and design for testability, scalability and operability. Honour any technology
constraint the stakeholder states in the requirements — the programming language,
framework, runtime, database or platform they ask for is binding; only when the
requirements are silent do you choose the stack yourself and justify it. State the chosen
stack explicitly under a '## Tech Stack' heading. You produce an architecture overview
(with a mermaid diagram), an API contract (an OpenAPI 3 ```yaml block for an HTTP/REST API,
or the equivalent interface definition for the chosen style), and the data schema in a
fenced block (```sql for a relational database, or the equivalent for the chosen
datastore). Prefer separating pure business logic from the delivery framework. Output
markdown only."""

REVIEW_SYSTEM = """You are a Senior Tech Lead doing code review and acting as the quality
gate. You verify two things: that the code is **without bugs** and that it **follows the
spec**. You are given the actual output of running the project's test suite and its linter.
Treat any failing test as a blocking defect that must be fixed (request changes). For each
linter finding, give the engineer a **specific, constructive suggestion** of how to fix it
(name the file/symbol and the concrete change) — linting is advisory, so it does not by
itself force changes, but request changes if a finding reveals a real defect. Beyond that,
judge correctness, separation of concerns, input validation, error handling, and whether the
feature under review satisfies its acceptance criteria. Begin your response with exactly one
line 'REVIEW_STATUS: approve' or 'REVIEW_STATUS: changes', then bullet-point findings (put
the lint fix suggestions under a '## Lint fix suggestions' heading). Approve only when the
tests pass and the feature meets its acceptance criteria."""


async def tech_lead_design_node(state: TeamState) -> TeamState:
    """Select the stack and design the architecture, OpenAPI contract, and DB schema."""
    ui.announce(
        ROLE,
        "plan",
        "Selecting the stack and designing architecture, API contract and DB schema",
        ["select-tech-stack", "design-architecture", "define-api-spec", "design-db-schema"],
    )
    requested = stack_hint(state)
    constraint = (
        "\n\nThe stakeholder explicitly asks for this technology — treat it as a binding "
        f"constraint and design around it: {requested}."
        if requested
        else ""
    )
    user = (
        "Design the system for these requirements and UX.\n\n"
        "### Original requirements (honour any stack / language / platform constraint "
        f"stated here)\n{state.get('spec_text', '')}\n\n"
        f"### Requirements (user stories)\n{state.get('user_stories', '')}\n\n"
        f"### UX\n{state.get('ux_design', '')}"
        f"{constraint}\n\n"
        "Produce markdown with: ## Tech Stack, ## Architecture (mermaid), "
        "## API Specification (```yaml OpenAPI for an HTTP API), ## Data Schema (```sql, or "
        "the equivalent for the chosen datastore)."
    ) + feature_brief(state)
    target = requested or "the most suitable backend language and web framework"
    doc = await generate(
        "tech_lead_design",
        with_skills(DESIGN_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            f"latest stable versions and best practices for {target} 2026",
            "current REST API and OpenAPI 3 design best practices 2026",
        ],
    )

    out = output_dir(state)
    written = [filesystem.write_doc(out, "architecture.md", doc)]
    api_yaml = extract_fenced(doc, "yaml")
    db_sql = extract_fenced(doc, "sql")
    if api_yaml:
        written.append(filesystem.write_doc(out, "openapi.yaml", api_yaml))
    if db_sql:
        written.append(filesystem.write_doc(out, "schema.sql", db_sql))
    ui.written(relpath(state, written))

    return {
        "architecture": doc,
        "tech_stack": extract_section(doc, "Tech Stack") or "",
        "api_spec": api_yaml or "",
        "db_schema": db_sql or "",
        "current_phase": "plan",
    }


async def tech_lead_review_node(state: TeamState) -> TeamState:
    """Verify the code as the quality gate: run the tests, check the spec, then rule.

    "Is it without bug?" is answered by actually running the project's test suite (a failing
    suite forces a ``changes`` verdict, regardless of the model's opinion); "does it follow
    our spec?" is answered by the model judging the code against the acceptance criteria for
    the feature under review. Bounded by the per-feature review cap so the loop terminates.
    """
    iters = state.get("review_iters", 0) + 1
    feature = _current_feature(state)
    headline = (
        f"Reviewing feature: {feature} (pass {iters})" if feature else f"Code review (pass {iters})"
    )
    ui.announce(ROLE, "code", headline, ["review-code", "route-workflow"])

    # Run the real test suite and the linter so the verdict is grounded in whether the code
    # works and is clean, not just how it reads. Offloaded to threads so the blocking
    # subprocesses never stall the loop.
    out = output_dir(state)
    outcome = await asyncio.to_thread(shell.run_test_suites, out)
    lint_outcome = await asyncio.to_thread(lint.run_linters, out)
    tests_failed = any(not run.result.ok for run in outcome.runs)
    ran = ", ".join(run.component for run in outcome.runs) or "none"
    test_verdict = "[red]failed[/red]" if tests_failed else "[green]passed[/green]"
    ui.note(f"tests → {test_verdict} (ran: {ran})")
    lint_verdict = (
        "[green]clean[/green]"
        if lint_outcome.clean
        else f"[yellow]{lint_outcome.components_with_issues} component(s) with issues[/yellow]"
    )
    ui.note(f"lint → {lint_verdict}")

    files = state.get("source_files", {})
    listing = "\n\n".join(f"# {path}\n```\n{content}\n```" for path, content in files.items())
    focus = f"### Feature under review\n{feature}\n\n" if feature else ""
    user = (
        "Review this code against the requirements and acceptance criteria, against the "
        "result of actually running its test suite, and against the linter diagnostics "
        "(turn each lint finding into a constructive fix suggestion).\n\n"
        f"{focus}"
        f"### Acceptance Criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"### Test suite result (just executed)\n{outcome.summary()}\n\n"
        f"### Linter diagnostics (just executed)\n{lint_outcome.summary()}\n\n"
        f"### Code\n{listing}\n"
    ) + feature_brief(state)
    verdict = await generate(
        "tech_lead_review",
        with_skills(REVIEW_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            f"latest {stack_hint(state) or 'software'} security and code review best "
            "practices 2026",
        ],
    )
    # Failing tests are a defect: force "changes" even if the model would have approved. Lint
    # is advisory — it informs the review's suggestions but never forces changes on its own.
    status = (
        "changes"
        if tests_failed or "review_status: changes" in verdict.lower()
        else "approve"
    )
    ui.note(f"verdict: [bold]{status}[/bold]")
    review_notes = (
        f"{verdict}\n\n### Test suite result\n{outcome.summary()}"
        f"\n\n### Linter diagnostics\n{lint_outcome.summary()}"
    )
    return {"review_notes": review_notes, "review_status": status, "review_iters": iters}


def _current_feature(state: TeamState) -> str:
    """Return the feature currently under review (empty when there is no feature plan)."""
    features = state.get("features") or []
    cursor = state.get("feature_cursor", 0)
    return features[cursor] if 0 <= cursor < len(features) else ""


# --- Supervisor routing (the `route_workflow` skill) ---
#
# Beyond the three feedback loops (review changes, the one-feature-at-a-time build loop, and
# failing tests), routing is capability-aware: the deterministic ``needs_frontend`` /
# ``needs_deployment`` flags (set by ``triage``) let the supervisor skip phases a project does
# not need — no UX/frontend for a pure API, and no containerisation/CI-CD/operate/infra-docs
# for a library or CLI.


def route_after_product_manager(state: TeamState) -> str:
    """Design the UX first when the product has a UI, else go straight to architecture."""
    return "ux_designer" if state.get("needs_frontend") else "tech_lead_design"


def route_after_planning(state: TeamState) -> str:
    """Build the backend when needed; else jump to the frontend, or straight to review.

    Backend is the default. A purely frontend/static product (``needs_backend`` false) skips
    the Software Engineer and goes straight to the Frontend Engineer (or, in the degenerate
    case of neither, to review).
    """
    if state.get("needs_backend", True):
        return "software_engineer"
    return "frontend_engineer" if state.get("needs_frontend") else "tech_lead_review"


def route_after_review(state: TeamState) -> str:
    """Drive the one-feature-at-a-time build loop after each Tech Lead verdict.

    On "changes" (within the per-feature review cap) loop back to whoever produced the code
    under review — the frontend engineer while building the UI, otherwise the software
    engineer. On approval (or once the cap is hit), advance the loop: build the next backend
    feature if any remain, then the frontend if the product needs one and it has not been
    built yet, and only then leave the build phase for CI (or straight to the test gate when
    the project does not deploy).
    """
    stage = state.get("build_stage", "backend")
    if (
        state.get("review_status") == "changes"
        and state.get("review_iters", 0) < SETTINGS.max_review_iters
    ):
        return "frontend_engineer" if stage == "frontend" else "software_engineer"

    features = state.get("features") or []
    if stage == "backend" and state.get("feature_cursor", 0) + 1 < len(features):
        return "software_engineer"
    if state.get("needs_frontend") and not state.get("frontend_built"):
        return "frontend_engineer"
    return "devops_ci" if state.get("needs_deployment") else "qa_test"


def route_after_tests(state: TeamState) -> str:
    """Loop back to a bug-fix on failure (within the cap); else deploy, or skip to docs."""
    if not state.get("tests_passed", False) and state.get("fix_iters", 0) < SETTINGS.max_fix_iters:
        return "software_engineer_fix"
    return "devops_cd" if state.get("needs_deployment") else "software_engineer_readme"


def route_after_qa_report(state: TeamState) -> str:
    """Write infra docs when the project deploys, else go straight to the user manual."""
    return "devops_docs" if state.get("needs_deployment") else "product_manager_docs"
