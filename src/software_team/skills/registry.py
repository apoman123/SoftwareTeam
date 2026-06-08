"""Skill registry — loads every character's SKILL.md library and exposes lookups.

Skills are authored as SKILL.md files under ``skills/library/<character>/`` and loaded
at import time. The agents use these lookups to compose prompts and bind tools; the CLI
(`software-team skills`) and README render the catalogue.
"""

from __future__ import annotations

from .base import Skill, compose_guidance
from .loader import CHARACTERS, load_all

ROLE_SKILLS: dict[str, list[Skill]] = load_all()


def skills_for(role: str) -> list[Skill]:
    """Return the loaded skills for ``role`` (empty if the role is unknown)."""
    return ROLE_SKILLS.get(role, [])


def skill_names(role: str) -> list[str]:
    """Return the names of ``role``'s skills, for display/announcements."""
    return [skill.name for skill in skills_for(role)]


def tools_for(role: str) -> list[object]:
    """Return the executable (tool-backed) skills for a role, for ReAct binding."""
    return [skill.tool for skill in skills_for(role) if skill.tool is not None]


def guidance_for(role: str) -> str:
    """The composed instructions from all of a role's SKILL.md skills."""
    return compose_guidance(skills_for(role))


def skill_guidance(role: str, skill_name: str) -> str:
    """The composed instructions from a single named skill of a role.

    Lets a step load *one specific* skill's guidance on its own (rather than the role's
    whole set) — e.g. the interactive spec generator loads only ``elicit-requirements``
    before it writes the spec.

    Args:
        role: The character whose library to look in (e.g. ``product_manager``).
        skill_name: The skill's ``name`` (its SKILL.md frontmatter / directory name).

    Returns:
        The skill's composed guidance, or "" if the role has no such skill.
    """
    for skill in skills_for(role):
        if skill.name == skill_name:
            return compose_guidance([skill])
    return ""


def skills_catalog() -> str:
    """A human-readable catalogue of every character's skills."""
    lines: list[str] = []
    for role in CHARACTERS:
        lines.append(f"### {role}")
        for skill in skills_for(role):
            lines.append(f"- `{skill.name}` ({skill.kind}): {skill.description}")
        lines.append("")
    return "\n".join(lines)
