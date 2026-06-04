"""Authoring helpers shared by agents and the dry-run stub.

These are pure text utilities: a small "file block" protocol the code-producing agents
use to emit multiple files in one response, plus extractors for fenced code blocks.
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
    return "\n\n".join(file_block(p, c) for p, c in files.items())


def parse_file_blocks(text: str) -> dict[str, str]:
    """Extract {path: content} from a response using the file-block protocol."""
    out: dict[str, str] = {}
    for m in _BLOCK_RE.finditer(text or ""):
        path = m.group("path").strip()
        out[path] = m.group("body")
    return out


def extract_fenced(text: str, lang: str | None = None) -> str | None:
    """Return the first fenced code block, optionally filtered by language tag."""
    for m in _FENCE_RE.finditer(text or ""):
        if lang is None or m.group("lang").lower() == lang.lower():
            return m.group("body").strip()
    return None


def extract_section(text: str, heading: str) -> str | None:
    """Return the markdown section body following a `## heading` line."""
    pattern = re.compile(
        rf"^#{{1,6}}\s*{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#{{1,6}}\s|\Z)",
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(text or "")
    return m.group("body").strip() if m else None
