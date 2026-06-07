"""🧠 Tech Lead / Architect — also the team's supervisor.

Two responsibilities map to two graph nodes:
  * design  — choose the stack and define architecture, the API contract and DB schema.
  * review  — review the engineer's code and approve or request changes.

As supervisor it also owns the routing decisions (the `route_workflow` skill): whether
to loop back for changes/bug-fixes or advance to the next phase, bounded by iteration
caps so the pipeline always terminates.
"""

from __future__ import annotations

from .. import ui
from ..config import SETTINGS
from ..skills.common import filesystem
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

REVIEW_SYSTEM = """You are a Senior Tech Lead doing code review. Judge correctness,
separation of concerns, input validation, error handling and test coverage. Begin your
response with exactly one line 'REVIEW_STATUS: approve' or 'REVIEW_STATUS: changes',
then bullet-point findings. Approve unless there is a real defect."""


def tech_lead_design_node(state: TeamState) -> TeamState:
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
    doc = generate(
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


def tech_lead_review_node(state: TeamState) -> TeamState:
    """Review the engineer's code and record an approve/changes verdict (bounded by a cap)."""
    iters = state.get("review_iters", 0) + 1
    ui.announce(ROLE, "code", f"Code review (pass {iters})", ["review-code", "route-workflow"])
    files = state.get("source_files", {})
    listing = "\n\n".join(f"# {path}\n```\n{content}\n```" for path, content in files.items())
    user = (
        "Review this code against the requirements and acceptance criteria.\n\n"
        f"### Acceptance Criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"### Code\n{listing}\n"
    ) + feature_brief(state)
    verdict = generate(
        "tech_lead_review",
        with_skills(REVIEW_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            f"latest {stack_hint(state) or 'software'} security and code review best "
            "practices 2026",
        ],
    )
    status = "changes" if "review_status: changes" in verdict.lower() else "approve"
    ui.note(f"verdict: [bold]{status}[/bold]")
    return {"review_notes": verdict, "review_status": status, "review_iters": iters}


# --- Supervisor routing (the `route_workflow` skill) ---
#
# Beyond the two feedback loops (review changes, failing tests), routing is capability-aware:
# the deterministic ``needs_frontend`` / ``needs_deployment`` flags (set by ``triage``) let
# the supervisor skip phases a project does not need — no UX/frontend for a pure API, and no
# containerisation/CI-CD/operate/infra-docs for a library or CLI.


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


def route_after_build(state: TeamState) -> str:
    """Build the frontend after the backend when a UI is needed, else go to review."""
    return "frontend_engineer" if state.get("needs_frontend") else "tech_lead_review"


def route_after_review(state: TeamState) -> str:
    """Loop back for changes (within the cap); else go to CI, or skip straight to testing."""
    if (
        state.get("review_status") == "changes"
        and state.get("review_iters", 0) < SETTINGS.max_review_iters
    ):
        return "software_engineer"
    return "devops_ci" if state.get("needs_deployment") else "qa_test"


def route_after_tests(state: TeamState) -> str:
    """Loop back to a bug-fix on failure (within the cap); else deploy, or skip to docs."""
    if not state.get("tests_passed", False) and state.get("fix_iters", 0) < SETTINGS.max_fix_iters:
        return "software_engineer_fix"
    return "devops_cd" if state.get("needs_deployment") else "software_engineer_readme"


def route_after_qa_report(state: TeamState) -> str:
    """Write infra docs when the project deploys, else go straight to the user manual."""
    return "devops_docs" if state.get("needs_deployment") else "product_manager_docs"
