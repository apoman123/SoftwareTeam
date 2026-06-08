"""Interactive spec generation — create a spec from a prompt, or revise an existing one.

The team normally starts from a spec file or a prompt (see ``intake``). This module adds a
third, *assisted* path the ``spec`` command drives. It works two ways:

* **generate** — from a rough one-line idea, write a complete spec from scratch.
* **revise** — take an existing markdown spec and improve it (make requirements testable,
  fill gaps, capture the technology, flag remaining unknowns as open questions).

Either way the Product Manager **talks to the user**: it runs a short, bounded *conversation*
— asking about the details of the user's needs and the technology to use, then reading the
answers and asking follow-up questions when something important is still missing — before
writing the spec. It loads two skills *before* writing: ``elicit-requirements`` (a structured
requirements-elicitation pipeline) so the interview and the document follow real practice
(problem before solution, testable requirements, the stack captured explicitly, ambiguities
flagged rather than assumed), and ``research-the-market`` — backed by web search — so the
spec is grounded in current facts (today's stable version of the requested stack, recommended
options when the user has no preference, domain/compliance considerations) rather than the
local model's stale training data. The web search is best-effort and a no-op offline.

In ``--dry-run`` or when not attached to a terminal it skips the interactive prompts and
produces a spec deterministically/offline, so the command stays scriptable in CI.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from .agents import base
from .config import SETTINGS
from .skills.registry import skill_guidance
from .state import TeamState

# The two ways the spec command runs.
GENERATE = "generate"  # write a new spec from a prompt
REVISE = "revise"  # improve an existing spec file

# The skills loaded before the spec is written, both from the Product Manager's library and
# composed into the system prompt for the authoring step: ``elicit-requirements`` (a
# structured requirements-elicitation pipeline) so the interview and the spec follow its
# method, and ``research-the-market`` so the agent grounds the spec in current web facts.
ELICIT_SKILL = "elicit-requirements"
RESEARCH_SKILL = "research-the-market"
ELICIT_CHARACTER = "product_manager"

# The model "role" (narrative tier) used for proposing questions and writing/revising specs.
ROLE = "spec_author"

# A fixed backbone of questions for a from-scratch spec, guaranteed to cover the two
# dimensions the feature is about: the **details of the user's needs** and the **technology**
# to use. Tailored, model-proposed questions (and follow-ups) are added on top when running
# interactively.
MANDATORY_QUESTIONS: tuple[str, ...] = (
    "Who are the primary users, and what problem should this solve for them?",
    "What are the must-have features or core use cases for the first version?",
    "Any non-functional needs — expected scale, performance, security, or compliance?",
    "Which technology should it use (language, framework, datastore, deploy target), "
    "or do you have no preference?",
    "Is there anything explicitly out of scope for now?",
)

# Recorded for any question the user skips, so the spec flags it as an open question rather
# than inventing an answer.
_UNANSWERED = "(not specified)"

PROPOSE_SYSTEM = """You are a Product Manager preparing to write a spec. Given a one-line
product idea, output a SHORT list (at most three) of the most useful clarifying questions to
ask the stakeholder before writing the spec — focus on the real needs and the technology they
want to use. Output ONLY the questions, one per line, each ending in a question mark; no
preamble, no numbering, no commentary."""

GAP_SYSTEM = """You are a Product Manager reviewing an existing spec in order to improve it.
Read it and identify the most important gaps, ambiguities, or weaknesses — for example: a
missing or non-measurable goal, undefined users, requirements that are not testable, missing
non-functional requirements, no stated technology/stack, or unclear scope. Output up to three
short questions to ask the author that would resolve the biggest gaps. Output ONLY the
questions, one per line, each ending in a question mark; no preamble, no numbering."""

FOLLOWUP_SYSTEM = """You are a Product Manager mid-interview, gathering exactly what you need
to write a high-quality spec. Given the request (or existing spec) and the answers so far,
decide whether any critical information is still missing — unclear scope, an untestable
requirement, a missing non-functional need, or an undecided technology. If so, output at most
two more short questions, one per line, each ending in a question mark. If you already have
enough to write a solid spec, output nothing at all."""

SPEC_SYSTEM = """You are a Product Manager turning a stakeholder's rough idea and their
interview answers into a clear, buildable spec. Capture WHAT is needed, not how to build it.
Treat any technology the stakeholder named as a binding constraint and record it under a
'## Technology' heading; if they stated no preference, say so and leave the choice to the
Tech Lead. Anything the stakeholder did not answer becomes an explicit open question — never
invent details. Output GitHub-flavoured markdown only, with these sections in order:
'# Spec: <short title>', '## Background', '## Use cases' (numbered, one per core capability),
'## Functional requirements', '## Non-functional requirements', '## Technology',
'## Out of scope', and '## Open questions' (only if any remain)."""

REVISE_SYSTEM = """You are a Product Manager improving an existing spec. Produce a BETTER,
complete version of it: keep the author's intent and any sound structure, but make every
requirement testable and unambiguous, fill gaps using the interview answers (add any missing
Background, Use cases, Functional requirements, Non-functional requirements, Technology, and
Out of scope sections), and turn anything still unknown into an explicit Open question rather
than inventing it. Preserve a stated technology choice as binding. Output the COMPLETE revised
spec as GitHub-flavoured markdown with those sections — not a diff, change list, or
commentary."""


def _parse_questions(text: str, *, limit: int) -> list[str]:
    """Extract clean question lines from a model response (robust to a weak local model).

    Keeps only lines that read as questions (end in "?"), stripping any bullet/number/quote
    decoration the model added, and caps the count.

    Args:
        text: The raw model output.
        limit: The maximum number of questions to keep.

    Returns:
        Up to ``limit`` question strings, in order.
    """
    questions: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*#0123456789.) ").strip().strip('"').strip()
        if line.endswith("?") and len(line) > 1:
            questions.append(line)
        if len(questions) >= limit:
            break
    return questions


def _render_qa(qa: list[tuple[str, str]]) -> str:
    """Render collected ``(question, answer)`` pairs as a markdown list for a prompt."""
    return "\n".join(f"- **{question}** {answer}" for question, answer in qa) or "(none)"


def _authoring_system(base_system: str) -> str:
    """Compose ``base_system`` with the spec-authoring skills' guidance, if present.

    This is what "loads the skills before generating the spec": the bodies of
    ``elicit-requirements`` (the interview/spec method) and ``research-the-market`` (ground
    the spec in current web facts) are folded into the system prompt used for the
    authoring/revision turn.
    """
    bodies = [skill_guidance(ELICIT_CHARACTER, skill) for skill in (ELICIT_SKILL, RESEARCH_SKILL)]
    guidance = "\n\n".join(body for body in bodies if body)
    if guidance:
        return f"{base_system}\n\nApply these skills and the method behind them:\n{guidance}"
    return base_system


def _spec_topic(source_text: str) -> str:
    """Extract a short topic label from the idea (generate) or the spec title (revise).

    Args:
        source_text: The one-line idea, or the existing spec markdown.

    Returns:
        The first meaningful line (a leading ``# Spec:`` title is unwrapped), capped to a
        short length suitable for a search query, or "" when nothing usable is found.
    """
    for raw in source_text.splitlines():
        line = raw.strip().lstrip("#").strip()
        if not line:
            continue
        if line.lower().startswith("spec:"):
            line = line[len("spec:") :].strip()
        return line[:80]
    return ""


def _research_queries(source_text: str, qa: list[tuple[str, str]]) -> list[str]:
    """Build up to two web queries to ground the spec in current facts.

    The Product Manager searches the internet before writing so the Technology section and
    any best practices reflect today's reality rather than the local model's stale training
    data. Queries are derived from the idea/spec *and* the interview answers — the
    stakeholder may name the technology only in an answer. Best-effort: ``base.generate``
    ignores these in dry-run or when web search is disabled.

    Args:
        source_text: The one-line idea (generate) or the existing spec (revise).
        qa: The collected ``(question, answer)`` interview pairs.

    Returns:
        Up to two search queries, or an empty list when there is nothing to ground on.
    """
    answers = " ".join(answer for _, answer in qa if answer and answer != _UNANSWERED)
    stack = base.detect_stack(f"{source_text}\n{answers}")
    topic = _spec_topic(source_text)
    year = datetime.date.today().year
    queries: list[str] = []
    if stack:
        queries.append(f"{stack} latest stable version and best practices {year}")
    elif topic:
        queries.append(f"recommended technology stack for {topic} {year}")
    if topic:
        queries.append(f"{topic} requirements and compliance considerations")
    return queries[:2]


async def _seed_questions(source_text: str, *, mode: str, state: TeamState) -> list[str]:
    """Ask the model for tailored opening questions for the interview (best-effort).

    For ``GENERATE`` these are extra questions about the idea; for ``REVISE`` they target the
    gaps in the existing spec. A no-op in dry-run. Unusable output yields an empty list.

    Args:
        source_text: The prompt (generate) or the existing spec (revise).
        mode: ``GENERATE`` or ``REVISE``.
        state: The run state (carries dry-run mode).

    Returns:
        Up to three tailored questions, or an empty list.
    """
    if state.get("dry_run"):
        return []
    if mode == REVISE:
        text = await base.generate(ROLE, GAP_SYSTEM, f"Existing spec:\n\n{source_text}", state)
    else:
        text = await base.generate(ROLE, PROPOSE_SYSTEM, f"Product idea: {source_text}", state)
    return _parse_questions(text, limit=3)


async def followup_questions(
    source_text: str, qa: list[tuple[str, str]], *, state: TeamState, limit: int = 2
) -> list[str]:
    """Ask the model whether more questions are needed given the answers so far.

    This is what makes the interview a *conversation*: after each round the agent reviews the
    answers and asks targeted follow-ups, or signals it has enough by returning nothing. A
    no-op in dry-run.

    Args:
        source_text: The prompt or existing spec under discussion.
        qa: The ``(question, answer)`` pairs gathered so far.
        state: The run state (carries dry-run mode).
        limit: The maximum number of follow-up questions to request.

    Returns:
        Up to ``limit`` follow-up questions, or an empty list when the agent is satisfied.
    """
    if state.get("dry_run"):
        return []
    user = (
        f"### Context\n{source_text}\n\n"
        f"### Answers so far\n{_render_qa(qa)}\n\n"
        "Any more questions before writing the spec?"
    )
    text = await base.generate(ROLE, FOLLOWUP_SYSTEM, user, state)
    return _parse_questions(text, limit=limit)


def ask_questions(
    questions: list[str], *, interactive: bool, console: Console | None
) -> list[tuple[str, str]]:
    """Put each question to the user (when interactive) and collect the answers.

    When not interactive (dry-run, ``--no-interactive``, or no TTY) the questions are not
    asked; each is recorded as unanswered so the spec turns them into open questions.

    Args:
        questions: The questions to ask, in order.
        interactive: Whether to actually prompt the user on the terminal.
        console: The Rich console to prompt through (unused when not interactive).

    Returns:
        A list of ``(question, answer)`` pairs.
    """
    pairs: list[tuple[str, str]] = []
    for question in questions:
        if interactive:
            answer = Prompt.ask(f"[bold cyan]?[/bold cyan] {question}", default="", console=console)
            answer = answer.strip() or _UNANSWERED
        else:
            answer = _UNANSWERED
        pairs.append((question, answer))
    return pairs


async def converse(
    source_text: str, *, mode: str, state: TeamState, interactive: bool, console: Console | None
) -> list[tuple[str, str]]:
    """Run the bounded interview conversation and return the collected answers.

    The agent opens with a set of questions (the fixed needs/technology backbone for a new
    spec, or gap-driven questions for a revision), then — interactively — reviews the answers
    and asks follow-up questions for up to ``SETTINGS.max_interview_rounds`` rounds, so the
    conversation adapts to what the user says yet always terminates. Non-interactively it asks
    nothing and records the backbone (if any) as unanswered.

    Args:
        source_text: The prompt (generate) or the existing spec (revise).
        mode: ``GENERATE`` or ``REVISE``.
        state: The run state (carries dry-run mode).
        interactive: Whether to actually talk to the user on the terminal.
        console: The Rich console for the conversation.

    Returns:
        The collected ``(question, answer)`` pairs.
    """
    pending = list(MANDATORY_QUESTIONS) if mode == GENERATE else []
    if interactive:
        seeded = await _seed_questions(source_text, mode=mode, state=state)
        pending = (pending + seeded) if mode == GENERATE else (seeded or pending)

    qa: list[tuple[str, str]] = []
    asked: set[str] = set()
    rounds = max(1, SETTINGS.max_interview_rounds)
    for round_index in range(rounds):
        new = [q for q in pending if q not in asked]
        if not new:
            break
        if interactive and console is not None:
            note = "A few questions about your needs and the technology…"
            if round_index > 0:
                note = "A couple of follow-ups based on your answers…"
            console.print(f"[dim]{note}[/dim]")
        qa += ask_questions(new, interactive=interactive, console=console)
        asked.update(new)
        # Follow-ups only make sense interactively, and only while rounds remain.
        if not interactive or round_index + 1 >= rounds:
            break
        pending = await followup_questions(source_text, qa, state=state)
        if not pending:
            break
    return qa


async def author_spec(prompt: str, qa: list[tuple[str, str]], state: TeamState) -> str:
    """Write a new spec from the prompt + interview answers, grounded in the elicit skill.

    Args:
        prompt: The stakeholder's one-line idea.
        qa: The collected ``(question, answer)`` pairs.
        state: The run state (carries dry-run mode).

    Returns:
        The spec as markdown.
    """
    user = (
        "Write the spec from the stakeholder's request and their interview answers.\n\n"
        f"### Initial request\n{prompt}\n\n"
        f"### Interview answers\n{_render_qa(qa)}\n"
    )
    return await base.generate(
        ROLE,
        _authoring_system(SPEC_SYSTEM),
        user,
        state,
        research_queries=_research_queries(prompt, qa),
    )


async def revise_spec(existing_spec: str, qa: list[tuple[str, str]], state: TeamState) -> str:
    """Improve an existing spec using the interview answers, grounded in the elicit skill.

    Args:
        existing_spec: The current spec markdown to improve.
        qa: The collected ``(question, answer)`` pairs.
        state: The run state (carries dry-run mode).

    Returns:
        The full revised spec as markdown.
    """
    user = (
        "Improve the spec below using the interview answers. Return the FULL revised spec.\n\n"
        f"### Existing spec to improve\n{existing_spec}\n\n"
        f"### Interview answers\n{_render_qa(qa)}\n"
    )
    return await base.generate(
        ROLE,
        _authoring_system(REVISE_SYSTEM),
        user,
        state,
        research_queries=_research_queries(existing_spec, qa),
    )


async def generate_spec(
    source_text: str,
    *,
    mode: str = GENERATE,
    state: TeamState,
    interactive: bool,
    console: Console | None,
) -> str:
    """Run the interview and return the authored (or revised) spec markdown.

    Args:
        source_text: The prompt (generate) or the existing spec (revise).
        mode: ``GENERATE`` or ``REVISE``.
        state: The run state (carries dry-run mode).
        interactive: Whether to talk to the user on the terminal.
        console: The Rich console for the interview.

    Returns:
        The spec as markdown.
    """
    qa = await converse(
        source_text, mode=mode, state=state, interactive=interactive, console=console
    )
    if mode == REVISE:
        return await revise_spec(source_text, qa, state)
    return await author_spec(source_text, qa, state)


async def generate_spec_file(
    source_text: str,
    out_path: Path,
    *,
    mode: str = GENERATE,
    interactive: bool,
    dry_run: bool,
    console: Console | None,
) -> tuple[Path, str]:
    """Generate or revise a spec from ``source_text`` and write it to ``out_path``.

    Args:
        source_text: The prompt (generate) or the existing spec text (revise).
        out_path: Where to write the resulting spec file (parent dirs are created).
        mode: ``GENERATE`` (from a prompt) or ``REVISE`` (improve an existing spec).
        interactive: Whether to run the interview on the terminal.
        dry_run: Whether to use the offline canned spec (no model needed).
        console: The Rich console for the interview.

    Returns:
        A ``(path, spec_text)`` tuple for the written file.
    """
    state: TeamState = {"dry_run": dry_run, "spec_text": source_text, "current_phase": "spec"}
    spec = await generate_spec(
        source_text, mode=mode, state=state, interactive=interactive, console=console
    )
    out_path = Path(out_path)
    if out_path.parent != Path():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(spec if spec.endswith("\n") else spec + "\n", encoding="utf-8")
    return out_path, spec
