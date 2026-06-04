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
from .base import generate, output_dir, relpath, with_skills

ROLE = "tech_lead"

DESIGN_SYSTEM = """You are a Senior Tech Lead / Architect. You make pragmatic technology
choices and design for testability, scalability and operability. You produce an
architecture overview (with a mermaid diagram), an OpenAPI 3 contract in a ```yaml
block, and a SQL schema in a ```sql block. Prefer separating pure business logic from
the web framework. Output markdown only."""

REVIEW_SYSTEM = """You are a Senior Tech Lead doing code review. Judge correctness,
separation of concerns, input validation, error handling and test coverage. Begin your
response with exactly one line 'REVIEW_STATUS: approve' or 'REVIEW_STATUS: changes',
then bullet-point findings. Approve unless there is a real defect."""


def tech_lead_design_node(state: dict) -> dict:
    ui.announce(
        ROLE, "plan",
        "Selecting the stack and designing architecture, API contract and DB schema",
        ["select-tech-stack", "design-architecture", "define-api-spec", "design-db-schema"],
    )
    user = (
        "Design the system for these requirements and UX.\n\n"
        f"### Requirements\n{state.get('user_stories', '')}\n\n"
        f"### UX\n{state.get('ux_design', '')}\n\n"
        "Produce markdown with: ## Tech Stack, ## Architecture (mermaid), "
        "## API Specification (```yaml OpenAPI), ## Data Schema (```sql)."
    )
    doc = generate("tech_lead_design", with_skills(DESIGN_SYSTEM, ROLE), user, state)

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


def tech_lead_review_node(state: dict) -> dict:
    iters = state.get("review_iters", 0) + 1
    ui.announce(ROLE, "code", f"Code review (pass {iters})", ["review-code", "route-workflow"])
    files = state.get("source_files", {})
    listing = "\n\n".join(f"# {p}\n```\n{c}\n```" for p, c in files.items())
    user = (
        "Review this code against the requirements and acceptance criteria.\n\n"
        f"### Acceptance Criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"### Code\n{listing}\n"
    )
    verdict = generate("tech_lead_review", with_skills(REVIEW_SYSTEM, ROLE), user, state)
    status = "changes" if "review_status: changes" in verdict.lower() else "approve"
    ui.note(f"verdict: [bold]{status}[/bold]")
    return {"review_notes": verdict, "review_status": status, "review_iters": iters}


# --- Supervisor routing (the `route_workflow` skill) ---

def route_after_review(state: dict) -> str:
    """Loop back to the engineer for changes, or advance to CI."""
    if state.get("review_status") == "changes" and state.get("review_iters", 0) < SETTINGS.max_review_iters:
        return "software_engineer"
    return "devops_ci"


def route_after_tests(state: dict) -> str:
    """Loop back to a bug-fix if tests fail, or advance to CD."""
    if not state.get("tests_passed", False) and state.get("fix_iters", 0) < SETTINGS.max_fix_iters:
        return "software_engineer_fix"
    return "devops_cd"
