"""CLI entrypoint.

    software-team run --spec examples/sample_spec.md [--out workspace] [--dry-run]
    software-team skills        # print each character's skill set

`--dry-run` swaps every LLM for a deterministic stub so the full pipeline and file
generation can be exercised with no Ollama server running.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from .config import SETTINGS
from .graph import build_graph
from .skills.common import filesystem
from .skills.registry import skills_catalog
from .state import TeamState, new_state

app = typer.Typer(add_completion=False, help="Multi-agent software team (LangGraph + Ollama).")
console = Console()


@app.command()
def run(
    spec: Path = typer.Option(
        ..., "--spec", "-s", exists=True, readable=True, help="Spec/use-case file"
    ),
    out: Path = typer.Option(Path("workspace"), "--out", "-o", help="Output workspace directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use canned outputs (no Ollama needed)"),
) -> None:
    """Drive a feature through the full SDLC and generate the project + DevOps artifacts."""
    spec_text = spec.read_text(encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)

    if dry_run:
        mode = "[yellow]dry-run[/yellow]"
    else:
        search = SETTINGS.search_provider if SETTINGS.search_enabled else "off"
        mode = (
            f"provider=[cyan]{SETTINGS.llm_provider}[/cyan] "
            f"coder=[cyan]{SETTINGS.coder_model}[/cyan] "
            f"narrative=[cyan]{SETTINGS.narrative_model}[/cyan] "
            f"search=[cyan]{search}[/cyan]"
        )
    console.rule(f"[bold]Software Team[/bold] · spec=[green]{spec}[/green] · {mode}")

    state = new_state(str(spec), spec_text, str(out))
    state["dry_run"] = dry_run

    graph = build_graph()
    final = graph.invoke(state, config={"recursion_limit": 50})

    _summary(final, out)


@app.command()
def skills() -> None:
    """Print the skill set assigned to each character."""
    console.print(Markdown("# Team Skills\n\n" + skills_catalog()))


def _summary(state: TeamState, out: Path) -> None:
    """Print a run summary: loop counts, test/deploy status, and the generated artifacts."""
    console.rule("[bold]Run complete[/bold]")
    console.print(
        f"Review passes: [cyan]{state.get('review_iters', 0)}[/cyan]"
        f" · Bug-fix passes: [cyan]{state.get('fix_iters', 0)}[/cyan]"
    )
    status = "[green]passed[/green]" if state.get("tests_passed") else "[red]failed[/red]"
    console.print(
        f"Tests: {status} · Deploy status: [bold]{state.get('deploy_status', 'n/a')}[/bold]"
    )

    files = filesystem.list_tree(str(out))
    console.print(f"\n[bold]{len(files)} artifacts generated in[/bold] [green]{out}/[/green]:")
    for path in files:
        console.print(f"  • {path}")


if __name__ == "__main__":
    app()
