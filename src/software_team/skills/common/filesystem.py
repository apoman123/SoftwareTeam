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
    """Write a {path: content} map. Returns the list of paths written."""
    return [write_file(output_dir, p, c) for p, c in files.items()]


def write_doc(output_dir: str, name: str, content: str) -> str:
    """Write a markdown design/ops document under docs/."""
    return write_file(output_dir, f"docs/{name}", content)


def read_file(output_dir: str, rel_path: str) -> str:
    target = _safe_join(Path(output_dir), rel_path)
    return target.read_text(encoding="utf-8") if target.exists() else ""


def list_tree(output_dir: str) -> list[str]:
    """Return sorted relative paths of every file under output_dir."""
    base = Path(output_dir)
    if not base.exists():
        return []
    ignore = {"__pycache__", ".pytest_cache"}
    return sorted(
        str(p.relative_to(base))
        for p in base.rglob("*")
        if p.is_file()
        and p.suffix != ".pyc"
        and not any(part in ignore for part in p.parts)
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
