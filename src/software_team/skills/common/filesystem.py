"""Filesystem capabilities — persist artifacts and source files into the workspace.

Exposed both as plain functions (used by the deterministic orchestration) and as
LangChain `@tool`s (so a tool-capable model can call them in a ReAct loop). All writes
are confined to the run's output directory.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool


def _safe_join(base: Path, rel: str) -> Path:
    """Resolve `rel` under `base`, refusing path traversal outside the workspace."""
    target = (base / rel).resolve()
    base_resolved = base.resolve()
    if base_resolved != target and base_resolved not in target.parents:
        raise ValueError(f"Refusing to write outside workspace: {rel}")
    return target


def write_file(output_dir: str, rel_path: str, content: str) -> str:
    """Write a single file under output_dir. Returns the absolute path written."""
    base = Path(output_dir)
    target = _safe_join(base, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = content if content.endswith("\n") else content + "\n"
    target.write_text(text, encoding="utf-8")
    return str(target)


def write_files(output_dir: str, files: dict[str, str]) -> list[str]:
    """Write a ``{path: content}`` map and return the list of paths written."""
    return [write_file(output_dir, path, content) for path, content in files.items()]


def delete_files(output_dir: str, rel_paths: list[str] | tuple[str, ...]) -> list[str]:
    """Delete files under ``output_dir`` and return the relative paths actually removed.

    Used by "remove a feature" runs to take a file out of the project entirely. Paths are
    confined to the workspace (the same traversal guard as writes), a path that does not
    exist is skipped silently, and any directory left empty by the deletion is pruned so the
    tree does not keep hollow folders.

    Args:
        output_dir: The workspace directory the project lives in.
        rel_paths: Project-relative paths to delete.

    Returns:
        The relative paths that were present and removed (skipping any that were absent).
    """
    base = Path(output_dir)
    removed: list[str] = []
    for rel_path in rel_paths:
        target = _safe_join(base, rel_path)
        if not target.is_file():
            continue
        target.unlink()
        removed.append(rel_path)
        # Prune now-empty parent directories, but never the workspace root itself.
        parent = target.parent
        while parent != base.resolve() and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return removed


def write_doc(output_dir: str, name: str, content: str) -> str:
    """Write a markdown design/ops document under docs/."""
    return write_file(output_dir, f"docs/{name}", content)


def read_file(output_dir: str, rel_path: str) -> str:
    """Read a file under ``output_dir``, returning an empty string if it is absent."""
    target = _safe_join(Path(output_dir), rel_path)
    return target.read_text(encoding="utf-8") if target.exists() else ""


def list_tree(output_dir: str) -> list[str]:
    """Return sorted relative paths of every file under output_dir."""
    base = Path(output_dir)
    if not base.exists():
        return []
    ignore = {"__pycache__", ".pytest_cache"}
    return sorted(
        str(path.relative_to(base))
        for path in base.rglob("*")
        if path.is_file()
        and path.suffix != ".pyc"
        and not any(part in ignore for part in path.parts)
    )


# --- LangChain tool wrappers (for ReAct-style agents on tool-capable models) ---


@tool
def write_source_file(output_dir: str, rel_path: str, content: str) -> str:
    """Write a source/code file at rel_path (relative to the project workspace)."""
    return write_file(output_dir, rel_path, content)


@tool
def read_source_file(output_dir: str, rel_path: str) -> str:
    """Read a source file at rel_path (relative to the project workspace)."""
    return read_file(output_dir, rel_path)


@tool
def list_project_files(output_dir: str) -> list[str]:
    """List every file currently in the project workspace."""
    return list_tree(output_dir)
