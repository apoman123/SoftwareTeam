"""Tool registry — resolves the `tool:` named in a SKILL.md frontmatter.

The executable side of skills lives here as LangChain `@tool`s (filesystem + shell).
A skill becomes "tool-backed" by naming one of these in its frontmatter, e.g.

    ---
    name: run-tests
    description: ...
    tool: run_tests
    ---
"""

from __future__ import annotations

from . import filesystem, shell

TOOL_REGISTRY: dict[str, object] = {
    "write_source_file": filesystem.write_source_file,
    "read_source_file": filesystem.read_source_file,
    "list_project_files": filesystem.list_project_files,
    "run_tests": shell.run_tests,
    "run_shell": shell.run_shell,
}


def resolve_tool(name: str | None) -> object | None:
    if not name:
        return None
    if name not in TOOL_REGISTRY:
        raise KeyError(f"SKILL.md references unknown tool '{name}'. Known: {sorted(TOOL_REGISTRY)}")
    return TOOL_REGISTRY[name]


def tool_names() -> list[str]:
    return sorted(TOOL_REGISTRY)
