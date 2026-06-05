"""Discover and parse SKILL.md skill files.

Skills live under ``skills/library/<character>/<skill-name>/SKILL.md`` following
Anthropic's Agent Skills convention. This loader reads each file's YAML frontmatter (`name`,
`description`, optional `tool`) and markdown body, binds any named tool, and groups the
results by character so each character loads exactly its corresponding skills.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .base import Skill
from .common.tools import resolve_tool

LIBRARY = Path(__file__).resolve().parent / "library"

CHARACTERS = [
    "product_manager",
    "ux_designer",
    "tech_lead",
    "software_engineer",
    "qa_engineer",
    "devops_sre",
]


def _parse_skill_md(md_path: Path) -> Skill:
    text = md_path.read_text(encoding="utf-8")
    meta: dict = {}
    body = text
    if text.lstrip().startswith("---"):
        # Frontmatter is delimited by the first two '---' lines.
        _, frontmatter, body = text.split("---", 2)
        meta = yaml.safe_load(frontmatter) or {}
        body = body.strip()
    name = str(meta.get("name") or md_path.parent.name)
    return Skill(
        name=name,
        description=str(meta.get("description", "")).strip(),
        body=body,
        tool=resolve_tool(meta.get("tool")),
        path=str(md_path),
    )


def load_character_skills(character: str) -> list[Skill]:
    """Load and parse every ``SKILL.md`` for ``character``, sorted by skill directory."""
    base = LIBRARY / character
    if not base.exists():
        return []
    skills: list[Skill] = []
    for skill_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        md = skill_dir / "SKILL.md"
        if md.exists():
            skills.append(_parse_skill_md(md))
    return skills


def load_all() -> dict[str, list[Skill]]:
    """Load every character's skills, keyed by character name."""
    return {character: load_character_skills(character) for character in CHARACTERS}
