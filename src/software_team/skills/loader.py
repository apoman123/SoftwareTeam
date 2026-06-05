"""Discover and parse SKILL.md skill files.

Skills live under ``skills/library/<character>/<skill-name>/SKILL.md`` following
Anthropic's Agent Skills convention. This loader reads each file's YAML frontmatter (`name`,
`description`, optional `tool`) and markdown body, binds any named tool, and groups the
results by character so each character loads exactly its corresponding skills.

Characters that author code (see ``CODE_AUTHORS``) additionally load the cross-cutting
``_foundation`` skills *first* — Karpathy's guidelines, then the Google style guide — so
their engineering baseline frames every role-specific skill that follows.

A third area, ``library/_shared/``, holds externally-sourced skills (each ``SKILL.md``
cites its upstream project and licence) that several — but not all — characters reuse.
``SHARED_SKILLS`` maps each character to the shared skills it loads, so a single on-disk
copy serves every character that needs it (e.g. the ``glab`` GitLab CLI skill is loaded by
both the Software Engineer and DevOps/SRE). They are composed *after* a character's own
role skills, as cross-cutting reference material.
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

# Externally-sourced skills (each SKILL.md cites its upstream project + MIT licence) kept
# in one place and loaded by the specific characters that need them. The mapping is the
# single source of truth for "which agent loads which shared skill"; the skills compose
# after a character's own role skills. Adding a name here makes that character load it —
# no other code change. Sources: jenkins-expert (0xfurai/claude-code-subagents);
# ci-cd-and-automation, security-and-hardening, git-workflow-and-versioning,
# code-review-and-quality, documentation-and-adrs, performance-optimization
# (addyosmani/agent-skills); gitlab-pipeline-watch, glab, commit-messages, mr-review,
# self-service-performance-testing (gitlab-org/ai/skills).
SHARED = LIBRARY / "_shared"
SHARED_SKILLS: dict[str, tuple[str, ...]] = {
    "tech_lead": ("code-review-and-quality", "documentation-and-adrs", "mr-review"),
    "software_engineer": ("git-workflow-and-versioning", "commit-messages", "glab"),
    "qa_engineer": ("performance-optimization", "self-service-performance-testing"),
    "devops_sre": (
        "jenkins-expert",
        "ci-cd-and-automation",
        "security-and-hardening",
        "gitlab-pipeline-watch",
        "glab",
    ),
}


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


def _shared_skills(character: str) -> list[Skill]:
    """Load the externally-sourced ``_shared`` skills assigned to ``character``.

    Args:
        character: The character key to look up in ``SHARED_SKILLS``.

    Returns:
        The character's shared skills that exist on disk, in ``SHARED_SKILLS`` order.
    """
    skills: list[Skill] = []
    for name in SHARED_SKILLS.get(character, ()):
        md = SHARED / name / "SKILL.md"
        if md.exists():
            skills.append(_parse_skill_md(md))
    return skills


def load_character_skills(character: str) -> list[Skill]:
    """Load and parse every ``SKILL.md`` for ``character``, sorted by skill directory.

    Composition order is: the shared ``_foundation`` skills first for code-authoring
    characters (``CODE_AUTHORS``) so their engineering baseline frames everything, then the
    character's own role skills, then any externally-sourced ``_shared`` skills assigned to
    it in ``SHARED_SKILLS``.

    Args:
        character: The character key whose skills to load.

    Returns:
        The character's composed skill list in load order.
    """
    role_skills: list[Skill] = []
    base = LIBRARY / character
    if base.exists():
        for skill_dir in sorted(path for path in base.iterdir() if path.is_dir()):
            md = skill_dir / "SKILL.md"
            if md.exists():
                role_skills.append(_parse_skill_md(md))
    foundation = _foundation_skills() if character in CODE_AUTHORS else []
    return foundation + role_skills + _shared_skills(character)


def load_all() -> dict[str, list[Skill]]:
    """Load every character's skills, keyed by character name."""
    return {character: load_character_skills(character) for character in CHARACTERS}
