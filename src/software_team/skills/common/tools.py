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

from . import filesystem, search, shell

TOOL_REGISTRY: dict[str, object] = {
    "write_source_file": filesystem.write_source_file,
    "read_source_file": filesystem.read_source_file,
    "list_project_files": filesystem.list_project_files,
    "run_tests": shell.run_tests,
    "run_shell": shell.run_shell,
    "web_search": search.web_search_tool,
}


def resolve_tool(name: str | None) -> object | None:
    """Resolve a tool name from SKILL.md frontmatter to its registered LangChain tool.

    Args:
        name: The tool name from a skill's ``tool:`` frontmatter, or ``None``.

    Returns:
        The registered tool, or ``None`` when ``name`` is falsy.

    Raises:
        KeyError: If ``name`` is given but not present in the registry.
    """
    if not name:
        return None
    if name not in TOOL_REGISTRY:
        raise KeyError(f"SKILL.md references unknown tool '{name}'. Known: {sorted(TOOL_REGISTRY)}")
    return TOOL_REGISTRY[name]


def tool_names() -> list[str]:
    """Return the sorted names of all registered tools."""
    return sorted(TOOL_REGISTRY)
