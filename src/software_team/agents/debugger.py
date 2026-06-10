"""🐛 Debugger — find and fix bugs in already-developed software.

The build pipeline's bug-fix loop only triggers when QA's own freshly written tests go red.
A user who *runs* the generated project and hits bugs needs something more direct: point the
team at the existing workspace and have the Software Engineer run the suite, diagnose the
root cause (guided by the reported symptom), fix it, and re-run until the suite is green —
without re-doing planning, architecture, or deployment.

These nodes drive that focused ``test -> diagnose -> fix`` loop (wired in
``graph.build_debug_graph``). The fix step reuses the file-block protocol, so it can rewrite,
add, or delete files exactly like every other code-producing node; the loop is bounded by
``SWTEAM_MAX_FIX_ITERS`` so it always terminates, honestly reporting anything still failing.
"""

from __future__ import annotations

import asyncio

from .. import ui
from ..config import SETTINGS
from ..skills.common import filesystem, shell
from ..state import TeamState
from .base import emit_files, generate, output_dir, relpath, stack_hint, with_skills
from .software_engineer import FILE_PROTOCOL, _code_listing

ROLE = "software_engineer_debug"
SKILLS_CHARACTER = "software_engineer"  # reuse the engineer's fix-bug / write-code skills

DEBUG_SYSTEM = f"""You are a Software Engineer debugging already-developed software that has
bugs. Work from the reported symptom and the failing test output to find the ROOT CAUSE — not
the surface symptom — and correct it with the smallest change that is genuinely right. If a
reported bug is not yet covered by a test, FIRST add a test that reproduces it, then fix the
code so that test passes. Re-emit ONLY the files you change or add, keep every other feature
working with its tests passing, and do not rebuild the project. {FILE_PROTOCOL}"""

REPORT_SYSTEM = """You are a Software Engineer writing a short debug report after a debugging
session. Summarise, in this order: the reported symptom (or note there was none and you fixed
failing tests), the root cause you found, the fix you made (name the files you changed), and
the final test status — be honest if anything is still failing. Output GitHub-flavoured
markdown only (no file blocks)."""


async def debug_tests_node(state: TeamState) -> TeamState:
    """Run the existing project's test suite to surface the bugs (the loop's gate)."""
    ui.announce(
        SKILLS_CHARACTER, "debug", "Running the test suite to surface the bugs", ["run-tests"]
    )
    # Install the project's deps first (live runs) so its imports resolve, then run the suite.
    # Offloaded to a thread so the (blocking) subprocess run never stalls the event loop.
    outcome = await asyncio.to_thread(
        shell.run_test_suites, output_dir(state), install=not state.get("dry_run", False)
    )
    passed = outcome.passed
    verdict = "[green]passed[/green]" if passed else "[red]failed[/red]"
    ran = ", ".join(run.component for run in outcome.runs) or "none"
    skipped = f"; skipped: {', '.join(outcome.skipped)}" if outcome.skipped else ""
    ui.note(f"tests → {verdict} (ran: {ran}{skipped})")
    return {
        "test_results": outcome.summary(),
        "tests_passed": passed,
        "current_phase": "debug",
    }


async def debugger_fix_node(state: TeamState) -> TeamState:
    """Diagnose the failure (and the reported symptom) and re-emit corrected files."""
    iters = state.get("fix_iters", 0) + 1
    ui.announce(
        SKILLS_CHARACTER,
        "debug",
        f"Diagnosing and fixing the root cause (pass {iters})",
        ["fix-bug", "run-tests"],
    )
    bug = (state.get("bug_report") or "").strip()
    reported = f"### Reported symptom\n{bug}\n\n" if bug else ""
    # When the suite is green but a symptom was reported, the bug is simply untested: ask for
    # a reproducing test before the fix.
    test_output = state.get("test_results", "").strip() or (
        "(the suite passes, so the reported bug is not yet covered — add a test that "
        "reproduces it, then fix it)"
    )
    user = (
        "Debug this project: find and fix the root cause of the failure(s) below.\n\n"
        f"{reported}"
        f"### Test output\n{test_output}\n\n"
        f"### Current files\n{_code_listing(state.get('source_files', {}))}\n\n"
        f"{FILE_PROTOCOL}"
    )
    files = await emit_files(
        state,
        model_role=ROLE,
        character=SKILLS_CHARACTER,
        system_prompt=DEBUG_SYSTEM,
        user_prompt=user,
        research_queries=[
            f"common bugs and debugging tips for {stack_hint(state) or 'the project stack'} 2026",
        ],
    )
    return {"source_files": files, "fix_iters": iters, "current_phase": "debug"}


async def debug_report_node(state: TeamState) -> TeamState:
    """Write a short debug report: the symptom, the root cause, the fix, and the final status."""
    ui.announce(SKILLS_CHARACTER, "document", "Writing the debug report", ["write-test-report"])
    bug = (state.get("bug_report") or "").strip() or "(none — fixed the failing tests)"
    listing = "\n".join(sorted(state.get("source_files", {})))
    user = (
        "Write the debug report for this session.\n\n"
        f"### Reported symptom\n{bug}\n\n"
        f"### Fix passes run\n{state.get('fix_iters', 0)}\n\n"
        f"### Final test status (tests_passed={state.get('tests_passed', False)})\n"
        f"{state.get('test_results', '')}\n\n"
        f"### Project files\n{listing}\n"
    )
    doc = await generate("debug_report", with_skills(REPORT_SYSTEM, SKILLS_CHARACTER), user, state)
    path = filesystem.write_doc(output_dir(state), "debug_report.md", doc)
    ui.written(relpath(state, [path]))
    return {"debug_report": doc, "current_phase": "document"}


def route_after_debug_tests(state: TeamState) -> str:
    """Loop to a fix while the suite is red (within the cap), with one pass for a reported bug.

    Returns ``"debugger_fix"`` to keep debugging, or ``"debug_report"`` to finish:

    * the bug-fix loop is bounded by ``SWTEAM_MAX_FIX_ITERS`` so it always terminates;
    * a red suite sends work to the fix node;
    * a green suite still gets one diagnose pass when the user reported a symptom that no
      test has reproduced yet (otherwise the run would end without addressing the report).
    """
    if state.get("fix_iters", 0) >= SETTINGS.max_fix_iters:
        return "debug_report"
    if not state.get("tests_passed", False):
        return "debugger_fix"
    if (state.get("bug_report") or "").strip() and state.get("fix_iters", 0) == 0:
        return "debugger_fix"
    return "debug_report"
