"""Discover and parse SKILL.md skill files.

Skills live under ``skills/library/<character>/<skill-name>/SKILL.md`` following
Anthropic's Agent Skills convention. This loader reads each file's YAML frontmatter (`name`,
`description`, optional `tool`) and markdown body, binds any named tool, and groups the
results by character so each character loads exactly its corresponding skills.

Characters that author code (see ``CODE_AUTHORS``) additionally load the cross-cutting
``_foundation`` skills *first* — Karpathy's guidelines, then the Google style guide — so
their engineering baseline frames every role-specific skill that follows.
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

# Characters that write source, test, or infrastructure code. They share an engineering
# baseline composed ahead of their own skills (see FOUNDATION_SKILLS).
CODE_AUTHORS = frozenset({"software_engineer", "qa_engineer", "devops_sre"})

# Cross-cutting skills every code author loads first, in this order: think the right way
# about the change (Karpathy), then write it to the Google style guide. They live in
# ``library/_foundation/`` rather than under any single character because they are shared.
FOUNDATION = LIBRARY / "_foundation"
FOUNDATION_SKILLS = ("karpathy-guidelines", "follow-google-style")


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


def _foundation_skills() -> list[Skill]:
    """Load the shared ``_foundation`` skills in ``FOUNDATION_SKILLS`` order.

    Returns:
        The foundation skills that exist on disk, ordered so ``karpathy-guidelines``
        comes before ``follow-google-style``.
    """
    skills: list[Skill] = []
    for name in FOUNDATION_SKILLS:
        md = FOUNDATION / name / "SKILL.md"
        if md.exists():
            skills.append(_parse_skill_md(md))
    return skills


def load_character_skills(character: str) -> list[Skill]:
    """Load and parse every ``SKILL.md`` for ``character``, sorted by skill directory.

    Code-authoring characters (``CODE_AUTHORS``) get the shared ``_foundation`` skills
    prepended, so their engineering baseline is composed before their own skills.

    Args:
        character: The character key whose skills to load.

    Returns:
        The character's skills; for code authors, the foundation skills come first.
    """
    base = LIBRARY / character
    if not base.exists():
        return []
    skills: list[Skill] = []
    for skill_dir in sorted(path for path in base.iterdir() if path.is_dir()):
        md = skill_dir / "SKILL.md"
        if md.exists():
            skills.append(_parse_skill_md(md))
    if character in CODE_AUTHORS:
        return _foundation_skills() + skills
    return skills


def load_all() -> dict[str, list[Skill]]:
    """Load every character's skills, keyed by character name."""
    return {character: load_character_skills(character) for character in CHARACTERS}
