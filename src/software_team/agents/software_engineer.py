"""💻 Software Engineer.

Turns the design into working code and unit tests, and — living the "you build it, you
run it" ethos — fixes bugs when QA's test run goes red. Emits files using the file-block
protocol so one response can create a whole project; the node persists them to the
workspace.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..skills.common.authoring import parse_file_blocks
from ..skills.registry import skill_names
from .base import generate, output_dir, relpath, with_skills

ROLE = "software_engineer"

FILE_PROTOCOL = (
    "Emit every file in this exact format, one block per file:\n"
    "<<<FILE relative/path.py >>>\n<file contents>\n<<<END>>>\n"
    "Do not wrap blocks in markdown fences."
)

BUILD_SYSTEM = f"""You are a Software Engineer. You write clean, idiomatic Python and
matching unit tests. Keep pure business logic in a framework-free module so it is easy
to unit test, and put the web framework in a thin adapter. Include a requirements.txt.
{FILE_PROTOCOL}"""

FIX_SYSTEM = f"""You are a Software Engineer fixing failing tests. Read the pytest
output, find the root cause, and re-emit ONLY the files you change with corrected
contents. {FILE_PROTOCOL}"""


def _persist_blocks(state: dict, text: str) -> dict[str, str]:
    files = parse_file_blocks(text)
    if files:
        written = filesystem.write_files(output_dir(state), files)
        ui.written(relpath(state, written))
    else:
        ui.note("[yellow]no file blocks parsed from model output[/yellow]")
    return files


def software_engineer_node(state: dict) -> dict:
    ui.announce(
        ROLE, "code",
        "Implementing the service and unit tests",
        skill_names(ROLE),
    )
    user = (
        "Implement the service described below. Provide application code, unit tests "
        "(pytest) for the business logic, and requirements.txt.\n\n"
        f"### Architecture & API\n{state.get('architecture', '')}\n\n"
        f"### Acceptance Criteria\n{state.get('acceptance_criteria', '')}\n\n"
        f"{FILE_PROTOCOL}"
    )
    if state.get("review_status") == "changes" and state.get("review_notes"):
        user += f"\n\n### Address this review feedback\n{state['review_notes']}"

    text = generate(ROLE, with_skills(BUILD_SYSTEM, ROLE), user, state)
    files = _persist_blocks(state, text)
    unit_tests = "\n\n".join(c for p, c in files.items() if "test" in p)
    return {"source_files": files, "unit_tests": unit_tests, "current_phase": "code"}


def software_engineer_fix_node(state: dict) -> dict:
    iters = state.get("fix_iters", 0) + 1
    ui.announce(ROLE, "deploy", f"Fixing failing tests (hotfix pass {iters})", ["fix-bug", "run-tests"])
    listing = "\n\n".join(f"# {p}\n```\n{c}\n```" for p, c in state.get("source_files", {}).items())
    user = (
        "The test suite failed. Fix the code.\n\n"
        f"### pytest output\n{state.get('test_results', '')}\n\n"
        f"### Current files\n{listing}\n\n"
        f"{FILE_PROTOCOL}"
    )
    text = generate("software_engineer_fix", with_skills(FIX_SYSTEM, ROLE), user, state)
    files = _persist_blocks(state, text)
    return {"source_files": files, "fix_iters": iters, "current_phase": "deploy"}
