"""The Skill abstraction.

Following the Agent Skills convention (a `SKILL.md` per skill: YAML frontmatter with a
verb-based `name` and a "use when" `description`, plus a markdown body of instructions),
a loaded Skill carries that parsed metadata and body. The body is composed into the
owning character's system prompt at runtime, so the SKILL.md files genuinely drive
behaviour. Skills that perform real I/O also bind a LangChain `tool` (named in the
frontmatter) so a tool-capable model can invoke them in a ReAct loop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str = ""
    tool: object | None = None
    path: str | None = None

    @property
    def kind(self) -> str:
        return "tool" if self.tool is not None else "reasoning"


def compose_guidance(skills: list[Skill]) -> str:
    """Combine each skill's instructions into one prompt section.

    Per the progressive-disclosure principle we inject the concise body of each of a
    character's skills (they are short by design), prefixed by the skill name.
    """
    parts: list[str] = []
    for s in skills:
        body = s.body.strip()
        if body:
            parts.append(f"### {s.name}\n{body}")
    return "\n\n".join(parts)
