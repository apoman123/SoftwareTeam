"""Authoring helpers shared by agents and the dry-run stub.

Pure text utilities: a small "file block" protocol the code-producing agents use to emit
multiple files in one response, plus extractors for fenced code blocks and markdown
sections.
"""

from __future__ import annotations

import re

FILE_OPEN = "<<<FILE"
FILE_CLOSE = "<<<END>>>"

_BLOCK_RE = re.compile(r"<<<FILE\s+(?P<path>[^\n>]+?)\s*>>>\n(?P<body>.*?)\n<<<END>>>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?P<lang>[a-zA-Z0-9_+-]*)\n(?P<body>.*?)```", re.DOTALL)


def file_block(path: str, content: str) -> str:
    """Render one file in the block protocol used by code-producing agents."""
    return f"{FILE_OPEN} {path} >>>\n{content.rstrip()}\n{FILE_CLOSE}"


def file_blocks(files: dict[str, str]) -> str:
    """Render a ``{path: content}`` map as a sequence of file blocks."""
    return "\n\n".join(file_block(path, content) for path, content in files.items())


def parse_file_blocks(text: str) -> dict[str, str]:
    """Extract {path: content} from a response using the file-block protocol."""
    out: dict[str, str] = {}
    for match in _BLOCK_RE.finditer(text or ""):
        path = match.group("path").strip()
        out[path] = match.group("body")
    return out


def extract_fenced(text: str, lang: str | None = None) -> str | None:
    """Return the first fenced code block, optionally filtered by language tag."""
    for match in _FENCE_RE.finditer(text or ""):
        if lang is None or match.group("lang").lower() == lang.lower():
            return match.group("body").strip()
    return None


def extract_section(text: str, heading: str) -> str | None:
    """Return the markdown section body following a `## heading` line."""
    pattern = re.compile(
        rf"^#{{1,6}}\s*{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#{{1,6}}\s|\Z)",
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text or "")
    return match.group("body").strip() if match else None


def split_at_heading(text: str, heading: str) -> tuple[str, str]:
    """Split markdown at a `## heading`, peeling a trailing section into its own piece.

    Unlike :func:`extract_section`, this keeps everything from the heading to the end of
    the document (including any sub-headings such as ``### Added``), which is what a
    standalone trailing section like Release Notes needs.

    Args:
        text: The markdown document to split.
        heading: The heading text to split on (matched case-insensitively).

    Returns:
        A ``(before, section)`` pair: the text before the heading and the heading plus
        everything after it. When the heading is absent, ``section`` is empty and
        ``before`` is the whole document.
    """
    pattern = re.compile(rf"^#{{1,6}}\s*{re.escape(heading)}\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(text or "")
    if not match:
        return (text or "").strip(), ""
    return text[: match.start()].strip(), text[match.start() :].strip()
