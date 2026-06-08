"""Console reporting — show which character is acting and which skills they use."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel

console = Console()

ROLE_LABELS = {
    "product_manager": "🧭 Product Manager",
    "ux_designer": "🎨 UI/UX Designer",
    "tech_lead": "🧠 Tech Lead / Architect",
    "software_engineer": "💻 Software Engineer",
    "frontend_engineer": "🖥️ Frontend Engineer",
    "qa_engineer": "🧪 QA / SDET",
    "devops_sre": "🚀 DevOps / SRE",
}

PHASE_LABELS = {
    "plan": "Plan & Design",
    "code": "Code & Build",
    "deploy": "Deploy & Release",
    "operate": "Operate & Monitor",
    "document": "Document & Handoff",
}


def announce(role: str, phase: str, action: str, skills: list[str]) -> None:
    """Print a panel naming the acting character, the phase, the action, and its skills."""
    label = ROLE_LABELS.get(role, role)
    phase_label = PHASE_LABELS.get(phase, phase)
    skill_str = ", ".join(f"[cyan]{name}[/cyan]" for name in skills) if skills else "—"
    console.print(
        Panel(
            f"[bold]{action}[/bold]\nskills: {skill_str}",
            title=f"{label}  ·  [dim]{phase_label}[/dim]",
            border_style="blue",
            expand=False,
        )
    )


def note(message: str) -> None:
    """Print a dim, indented progress note."""
    console.print(f"  [dim]›[/dim] {message}")


def written(paths: list[str]) -> None:
    """Print a green checkmark line for each written path."""
    for path in paths:
        console.print(f"    [green]✓[/green] {path}")


@contextmanager
def generating(label: str = "generating") -> Iterator[Callable[[int], None]]:
    """Show a live spinner that grows with streamed output, then a one-line done summary.

    A character's LLM turn can run for minutes on a slow local model; without visible
    progress the run looks frozen ("idle"). This yields an ``update(chars)`` callback the
    caller invokes as streamed text accumulates, so the spinner reports size and elapsed
    time the whole time the model is working. On a clean exit that produced output it prints
    the total and the duration; if the stream yielded nothing (or raised — e.g. streaming
    unsupported) it stays silent so the caller's fallback path can report instead.

    Args:
        label: Short verb shown in the spinner (e.g. "generating").

    Yields:
        An ``update(chars)`` callback to report the running output size.
    """
    start = time.monotonic()
    produced = {"chars": 0}
    with console.status(f"[dim]💭 {label}…[/dim]", spinner="dots") as status:

        def update(chars: int) -> None:
            produced["chars"] = chars
            elapsed = time.monotonic() - start
            status.update(f"[dim]💭 {label}… {chars:,} chars · {elapsed:0.0f}s[/dim]")

        yield update

    if produced["chars"]:
        note(f"generated {produced['chars']:,} chars in {time.monotonic() - start:0.0f}s")
