"""🧹 Garbage collection — scan a whole project for rot and drive a Tech-Lead-gated fix.

The maintenance counterpart to the build pipeline. A deterministic scan
(:mod:`software_team.skills.common.gc`) sweeps the project for documentation
inconsistencies, architecture violations, and technical debt; the findings are *submitted to
the Tech Lead*, who triages them into a prioritised fix request; the Software Engineer applies
the fixes; and the existing Tech Lead review (which runs the tests and the linter) verifies the
result, looping within the bug-fix cap. See ``graph.build_gc_graph``.
"""

from __future__ import annotations

from langgraph.graph import END

from .. import ui
from ..config import SETTINGS
from ..skills.common import filesystem, gc
from ..skills.registry import skill_names
from ..state import TeamState
from .base import emit_files, feature_brief, generate, output_dir, relpath, with_skills
from .software_engineer import FILE_PROTOCOL, _code_listing

REQUEST_SYSTEM = """You are a Senior Tech Lead triaging the output of an automated
garbage-collection scan (documentation inconsistencies, architecture violations, technical
debt). Turn the findings into a prioritised fix request (a work order) for the engineer:
order the issues by risk/impact, group related ones, and for each say concretely what to
change. The clean-up must not change intended behaviour and must keep every test passing. Do
not write code. Output markdown only."""

FIX_SYSTEM = f"""You are a Software Engineer carrying out a garbage-collection clean-up. Apply
the Tech Lead's fix request: reconcile the docs with the code, move misplaced code to the
right layer, and clear the technical debt — WITHOUT changing intended behaviour, keeping every
test passing. Re-emit ONLY the files you change with corrected contents, and delete a whole
dead file with a deletion directive. {FILE_PROTOCOL}"""


async def gc_scan_node(state: TeamState) -> TeamState:
    """Scan the whole workspace for rot and write the report submitted to the Tech Lead."""
    ui.announce(
        "tech_lead",
        "gc",
        "Scanning the project for doc inconsistencies, architecture violations and tech debt",
        ["collect-garbage"],
    )
    findings = gc.scan_workspace(output_dir(state))
    report = gc.scan_report(findings)
    path = filesystem.write_doc(output_dir(state), "garbage_collection.md", report)
    ui.written(relpath(state, [path]))
    if findings:
        ui.note(f"submitting [bold]{len(findings)}[/bold] finding(s) to the tech lead")
    else:
        ui.note("[green]no issues found[/green] — nothing to collect")
    return {"gc_findings": len(findings), "gc_report": report, "current_phase": "gc"}


async def tech_lead_gc_request_node(state: TeamState) -> TeamState:
    """Triage the scan findings into a prioritised fix request (the work order for the engineer)."""
    ui.announce(
        "tech_lead",
        "gc",
        "Triaging the findings into a prioritised fix request",
        ["collect-garbage", "route-workflow"],
    )
    user = (
        "Triage this garbage-collection scan into a prioritised fix request for the engineer. "
        "Order the issues by risk, group related ones, and state concretely what to change for "
        "each. The clean-up must not change behaviour and must keep all tests passing.\n\n"
        f"### Scan report\n{state.get('gc_report', '')}\n"
    ) + feature_brief(state)
    doc = await generate(
        "tech_lead_gc_request",
        with_skills(REQUEST_SYSTEM, "tech_lead"),
        user,
        state,
        research_queries=[
            "latest refactoring and technical-debt prioritisation best practices 2026",
        ],
    )
    path = filesystem.write_doc(output_dir(state), "gc_request.md", doc)
    ui.written(relpath(state, [path]))
    return {"gc_request": doc, "current_phase": "gc"}


async def gc_fix_node(state: TeamState) -> TeamState:
    """Apply the Tech Lead's fix request to the codebase (re-emit only the changed files)."""
    iters = state.get("fix_iters", 0) + 1
    ui.announce(
        "software_engineer",
        "gc",
        f"Applying the garbage-collection fixes (pass {iters})",
        skill_names("software_engineer"),
    )
    user = (
        "Apply the Tech Lead's garbage-collection fix request below to the codebase. Fix the "
        "documentation inconsistencies, architecture violations, and technical debt without "
        "changing intended behaviour; keep every test passing.\n\n"
        f"### Fix request\n{state.get('gc_request', '')}\n\n"
        f"### Current source files\n{_code_listing(state.get('source_files', {}))}\n\n"
        f"{FILE_PROTOCOL}"
    ) + feature_brief(state)
    files = await emit_files(
        state,
        model_role="software_engineer",
        character="software_engineer",
        system_prompt=FIX_SYSTEM,
        user_prompt=user,
    )
    return {"source_files": files, "fix_iters": iters, "current_phase": "gc"}


def route_after_gc_scan(state: TeamState) -> str:
    """Submit to the Tech Lead when the scan found issues; otherwise the project is clean."""
    return "tech_lead_gc_request" if state.get("gc_findings", 0) > 0 else "end"


def route_after_gc_review(state: TeamState) -> str:
    """Loop back to another fix pass while review requests changes (within the cap), else end."""
    if (
        state.get("review_status") == "changes"
        and state.get("fix_iters", 0) < SETTINGS.max_fix_iters
    ):
        return "gc_fix"
    return "end"


# Routing targets mapped to graph nodes (``"end"`` -> the graph's END sentinel).
GC_SCAN_ROUTES = {"tech_lead_gc_request": "tech_lead_gc_request", "end": END}
GC_REVIEW_ROUTES = {"gc_fix": "gc_fix", "end": END}
