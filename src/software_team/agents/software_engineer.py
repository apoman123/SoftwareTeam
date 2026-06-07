"""💻 Software Engineer.

Turns the design into working code and unit tests, and — living the "you build it, you
run it" ethos — fixes bugs when QA's test run goes red. Emits files using the file-block
protocol so one response can create a whole project; the node persists them to the
workspace.
"""

from __future__ import annotations

from .. import ui
from ..skills.common import filesystem
from ..skills.registry import skill_names
from ..state import FEATURE_MODE, TeamState
from .base import emit_files, feature_brief, generate, output_dir, relpath, with_skills

ROLE = "software_engineer"

FILE_PROTOCOL = (
    "Emit every file in this exact format, one block per file:\n"
    "<<<FILE relative/path.py >>>\n<file contents>\n<<<END>>>\n"
    "Do not wrap blocks in markdown fences."
)

BUILD_SYSTEM = f"""You are a Software Engineer. You write clean, idiomatic programming languages and
matching unit tests. Keep pure business logic in a framework-free module so it is easy
to unit test, and put the web framework in a thin adapter. Include a requirements.txt.
{FILE_PROTOCOL}"""

FIX_SYSTEM = f"""You are a Software Engineer fixing failing tests. Read the unit test
output, find the root cause, and re-emit ONLY the files you change with corrected
contents. {FILE_PROTOCOL}"""

README_SYSTEM = """You are a Software Engineer writing the repository README — the
project's front door for other engineers and users. Explain what the project does, the
prerequisites and versions, how to set it up locally (create a virtual environment, then
install the pinned dependencies from requirements.txt), how to run it, and how to call
its API with copy-pasteable examples. Output GitHub-flavoured markdown only (no file
blocks)."""


def _code_listing(files: dict[str, str]) -> str:
    """Render the current project files as fenced blocks for an edit/fix prompt."""
    return "\n\n".join(f"# {path}\n```\n{content}\n```" for path, content in files.items())


def _stack_hint(state: TeamState) -> str:
    """Return a short keyword hint of the chosen stack, for grounding code-gen searches."""
    stack = (state.get("tech_stack") or "").strip()
    if not stack:
        return "Python FastAPI"
    first_line = next((line.strip(" -*#") for line in stack.splitlines() if line.strip()), "")
    return (first_line or stack)[:120]


def _build_research_queries(state: TeamState) -> list[str]:
    """Return the web queries that ground the build node in current library APIs."""
    hint = _stack_hint(state)
    return [
        f"latest API and recommended usage for {hint} 2026",
        "latest FastAPI and Pydantic v2 version and best practices 2026",
    ]


def software_engineer_node(state: TeamState) -> TeamState:
    """Implement the service plus unit tests from the architecture and acceptance criteria."""
    ui.announce(
        ROLE,
        "code",
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
    if state.get("mode") == FEATURE_MODE:
        # Extending existing software: show the current code and re-emit only what changes.
        user += (
            "\n\nThis is an existing codebase. Re-emit ONLY the files you change to add the "
            "feature, plus any new files; do not touch unrelated files.\n\n"
            f"### Current source files\n{_code_listing(state.get('source_files', {}))}"
        )
    if state.get("review_status") == "changes" and state.get("review_notes"):
        user += f"\n\n### Address this review feedback\n{state['review_notes']}"
    user += feature_brief(state)

    files = emit_files(
        state,
        model_role=ROLE,
        character=ROLE,
        system_prompt=BUILD_SYSTEM,
        user_prompt=user,
        research_queries=_build_research_queries(state),
    )
    unit_tests = "\n\n".join(content for path, content in files.items() if "test" in path)
    return {"source_files": files, "unit_tests": unit_tests, "current_phase": "code"}


def software_engineer_fix_node(state: TeamState) -> TeamState:
    """Read the failing pytest output and re-emit corrected files (bounded hotfix loop)."""
    iters = state.get("fix_iters", 0) + 1
    ui.announce(
        ROLE, "deploy", f"Fixing failing tests (hotfix pass {iters})", ["fix-bug", "run-tests"]
    )
    user = (
        "The test suite failed. Fix the code.\n\n"
        f"### pytest output\n{state.get('test_results', '')}\n\n"
        f"### Current files\n{_code_listing(state.get('source_files', {}))}\n\n"
        f"{FILE_PROTOCOL}"
    )
    files = emit_files(
        state,
        model_role="software_engineer_fix",
        character=ROLE,
        system_prompt=FIX_SYSTEM,
        user_prompt=user,
        research_queries=[
            f"latest API and recommended usage for {_stack_hint(state)} 2026",
        ],
    )
    return {"source_files": files, "fix_iters": iters, "current_phase": "deploy"}


def software_engineer_readme_node(state: TeamState) -> TeamState:
    """Write the repository README: purpose, local setup, run instructions, and API usage."""
    ui.announce(ROLE, "document", "Writing the repository README", ["write-readme"])
    files = state.get("source_files", {})
    listing = "\n".join(sorted(files))
    user = (
        "Write the repository README.md for the project below. Include, with concrete "
        "commands: a short overview, prerequisites and versions, local setup (create a "
        "virtual environment, then `pip install -r requirements.txt`), how to run it "
        "(e.g. `uvicorn app.main:app --reload`), an API usage section with example "
        "`curl` calls, and how to run the tests.\n\n"
        f"### Architecture & API\n{state.get('architecture', '')}\n\n"
        f"### Project files\n{listing}\n\n"
        f"### Dependencies (requirements.txt)\n{files.get('requirements.txt', '')}\n"
    ) + feature_brief(state)
    doc = generate(
        "software_engineer_readme",
        with_skills(README_SYSTEM, ROLE),
        user,
        state,
        research_queries=[
            f"latest README conventions and {_stack_hint(state)} quickstart commands 2026",
        ],
    )
    path = filesystem.write_file(output_dir(state), "README.md", doc)
    ui.written(relpath(state, [path]))
    return {"readme": doc, "current_phase": "document"}
