"""Console reporting — show which character is acting and which skills they use."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

console = Console()

ROLE_LABELS = {
    "product_manager": "🧭 Product Manager",
    "ux_designer": "🎨 UI/UX Designer",
    "tech_lead": "🧠 Tech Lead / Architect",
    "software_engineer": "💻 Software Engineer",
    "qa_engineer": "🧪 QA / SDET",
    "devops_sre": "🚀 DevOps / SRE",
}

PHASE_LABELS = {
    "plan": "Plan & Design",
    "code": "Code & Build",
    "deploy": "Deploy & Release",
    "operate": "Operate & Monitor",
}


def announce(role: str, phase: str, action: str, skills: list[str]) -> None:
    label = ROLE_LABELS.get(role, role)
    phase_label = PHASE_LABELS.get(phase, phase)
    skill_str = ", ".join(f"[cyan]{s}[/cyan]" for s in skills) if skills else "—"
    console.print(
        Panel(
            f"[bold]{action}[/bold]\nskills: {skill_str}",
            title=f"{label}  ·  [dim]{phase_label}[/dim]",
            border_style="blue",
            expand=False,
        )
    )


def note(message: str) -> None:
    console.print(f"  [dim]›[/dim] {message}")


def written(paths: list[str]) -> None:
    for p in paths:
        console.print(f"    [green]✓[/green] {p}")
