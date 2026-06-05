"""Feature-request intake — where the team's work comes from.

The Product Manager can be handed work through two channels: a written **spec file**
(``--spec``) or a **prompt** typed straight on the command line (``--prompt``). Both
resolve to the same thing — the ``spec_text`` the PM turns into requirements — so the
rest of the pipeline neither knows nor cares which channel a request arrived through.

This module is the single place that knows about the two channels: it validates that
exactly one was supplied and normalises it into a :class:`FeatureRequest`.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path

# The channels a feature request can arrive through.
FILE = "file"
PROMPT = "prompt"

# Source label used when the request was typed as a prompt rather than read from a file.
PROMPT_LABEL = "<prompt>"

# Width of the prompt preview shown in the console.
_PREVIEW_WIDTH = 60


class IntakeError(ValueError):
    """A feature request could not be resolved (none supplied, both supplied, or empty)."""


@dataclass(frozen=True)
class FeatureRequest:
    """A unit of work handed to the Product Manager.

    Attributes:
        label: A human-readable source label — the spec file path, or ``<prompt>``.
        text: The spec / use-case text the PM turns into requirements.
        origin: The channel the request arrived through (``FILE`` or ``PROMPT``).
    """

    label: str
    text: str
    origin: str

    @property
    def display(self) -> str:
        """Return a short, source-appropriate label for console output.

        Returns:
            The file path for file requests, or a truncated, quoted preview of the
            prompt text for prompt requests.
        """
        if self.origin == PROMPT:
            preview = textwrap.shorten(self.text, width=_PREVIEW_WIDTH, placeholder="…")
            return f'"{preview}"'
        return self.label


def from_file(path: Path) -> FeatureRequest:
    """Build a feature request from a spec file.

    Args:
        path: Path to a readable spec / use-case file.

    Returns:
        A feature request carrying the file's text.
    """
    return FeatureRequest(label=str(path), text=path.read_text(encoding="utf-8"), origin=FILE)


def from_prompt(prompt: str) -> FeatureRequest:
    """Build a feature request from a direct command-line prompt.

    Args:
        prompt: The feature description typed by the user.

    Returns:
        A feature request carrying the (stripped) prompt text.

    Raises:
        IntakeError: If the prompt is blank once stripped.
    """
    text = prompt.strip()
    if not text:
        raise IntakeError("--prompt must not be empty.")
    return FeatureRequest(label=PROMPT_LABEL, text=text, origin=PROMPT)


def resolve(spec: Path | None, prompt: str | None) -> FeatureRequest:
    """Resolve the single feature request from the two mutually exclusive inputs.

    Exactly one of ``spec`` or ``prompt`` must be supplied; this is what lets the user
    drive the team either from a file or from a prompt.

    Args:
        spec: The ``--spec`` file path, if given.
        prompt: The ``--prompt`` text, if given.

    Returns:
        The resolved feature request.

    Raises:
        IntakeError: If neither or both inputs are supplied, or the prompt is blank.
    """
    if spec is not None and prompt is not None:
        raise IntakeError("Provide either --spec or --prompt, not both.")
    if spec is not None:
        return from_file(spec)
    if prompt is not None:
        return from_prompt(prompt)
    raise IntakeError("Provide a feature request via --spec <file> or --prompt <text>.")
