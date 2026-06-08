"""CLI entrypoint.

    software-team spec --prompt "A recipe sharing app" [--out spec.md]   # interview -> spec file
    software-team spec --spec draft.md --out better.md                   # revise an existing spec
    software-team run --spec examples/sample_spec.md [--out workspace] [--dry-run]
    software-team run --prompt "Build a URL shortener with click analytics"
    software-team feature --into workspace --prompt "Add task due dates"
    software-team skills        # print each character's skill set

The team can be handed work in two ways: a written spec **file** (``--spec``) or a
**prompt** typed directly on the command line (``--prompt``). Exactly one is required.
``run`` builds a project from scratch; ``feature`` integrates a new request into a project
the team has already developed (point ``--into`` at a previous run's workspace). ``spec``
runs a short interactive interview (needs + technology) and writes a spec **file** you can
then feed to ``run --spec``.

`--dry-run` swaps every LLM for a deterministic stub so the full pipeline and file
generation can be exercised with no Ollama server running.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from . import elicit, intake, observability, project
from .config import SETTINGS
from .graph import build_graph
from .skills.common import filesystem
from .skills.registry import skills_catalog
from .state import TeamState, new_feature_state, new_state

app = typer.Typer(add_completion=False, help="Multi-agent software team (LangGraph + Ollama).")
console = Console()


def _mode_banner(dry_run: bool) -> str:
    """Return the provider/search/tracing banner for the run-start rule (or a dry-run tag)."""
    tracing = (
        f" tracing=[cyan]langsmith:{SETTINGS.langsmith_project}[/cyan]"
        if SETTINGS.langsmith_tracing
        else ""
    )
    if dry_run:
        return f"[yellow]dry-run[/yellow]{tracing}"
    search = SETTINGS.search_provider if SETTINGS.search_enabled else "off"
    return (
        f"provider=[cyan]{SETTINGS.llm_provider}[/cyan] "
        f"coder=[cyan]{SETTINGS.coder_model}[/cyan] "
        f"narrative=[cyan]{SETTINGS.narrative_model}[/cyan] "
        f"search=[cyan]{search}[/cyan]"
        f"{tracing}"
    )


@app.command()
def run(
    spec: Path | None = typer.Option(
        None, "--spec", "-s", exists=True, readable=True, help="Spec/use-case file to build from"
    ),
    prompt: str | None = typer.Option(
        None, "--prompt", "-p", help="Describe the feature directly, instead of a spec file"
    ),
    out: Path = typer.Option(Path("workspace"), "--out", "-o", help="Output workspace directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use canned outputs (no Ollama needed)"),
) -> None:
    """Drive a feature through the full SDLC and generate the project + DevOps artifacts.

    Hand the team its work either as a spec file (``--spec``) or as a direct feature
    prompt (``--prompt``); exactly one is required.
    """
    try:
        request = intake.resolve(spec, prompt)
    except intake.IntakeError as exc:
        raise typer.BadParameter(str(exc)) from exc

    out.mkdir(parents=True, exist_ok=True)

    console.rule(
        f"[bold]Software Team[/bold] · {request.origin}=[green]{request.display}[/green]"
        f" · {_mode_banner(dry_run)}"
    )

    state = new_state(request.label, request.text, str(out))
    state["dry_run"] = dry_run

    observability.configure_langsmith()
    graph = build_graph()
    config = observability.run_config(
        f"software-team:run:{request.label}",
        tags=["run", request.origin],
        metadata={
            "swteam.command": "run",
            "swteam.origin": request.origin,
            "swteam.dry_run": dry_run,
        },
    )
    config["recursion_limit"] = SETTINGS.graph_recursion_limit
    final = asyncio.run(graph.ainvoke(state, config=config))

    _summary(final, out)


@app.command()
def feature(
    into: Path = typer.Option(
        ...,
        "--into",
        "-i",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Workspace of the already-developed project to extend",
    ),
    spec: Path | None = typer.Option(
        None, "--spec", "-s", exists=True, readable=True, help="Spec/use-case file for the feature"
    ),
    prompt: str | None = typer.Option(
        None, "--prompt", "-p", help="Describe the new feature directly, instead of a spec file"
    ),
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Write the updated project here (default: modify --into in place)"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use canned outputs (no Ollama needed)"),
) -> None:
    """Integrate a new feature into software the team has already developed.

    Point ``--into`` at a previous run's workspace and describe the new feature with a spec
    file (``--spec``) or a prompt (``--prompt``); exactly one is required. The team re-runs
    the SDLC against the existing code, extending it rather than rebuilding it. By default
    the project is updated in place; pass ``--out`` to write the updated copy to a new
    directory instead, leaving the original untouched.
    """
    try:
        request = intake.resolve(spec, prompt)
        existing = project.load(str(into))
    except (intake.IntakeError, project.ProjectError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    target = out or into
    target.mkdir(parents=True, exist_ok=True)
    if target.resolve() != into.resolve():
        # Fresh output dir: duplicate the project there first so the result is complete and
        # the original is left untouched.
        project.mirror(existing, str(target))

    console.rule(
        f"[bold]Software Team · feature[/bold] · into=[green]{into}[/green]"
        f" · {request.origin}=[green]{request.display}[/green] · {_mode_banner(dry_run)}"
    )

    state = new_feature_state(
        request.label,
        request.text,
        str(target),
        source_files=existing.source_files,
        baseline=existing.brief(),
    )
    state["dry_run"] = dry_run

    observability.configure_langsmith()
    config = observability.run_config(
        f"software-team:feature:{request.label}",
        tags=["feature", request.origin],
        metadata={
            "swteam.command": "feature",
            "swteam.origin": request.origin,
            "swteam.dry_run": dry_run,
        },
    )
    config["recursion_limit"] = SETTINGS.graph_recursion_limit
    final = asyncio.run(build_graph().ainvoke(state, config=config))

    _summary(final, target)


@app.command()
def spec(
    spec: Path | None = typer.Option(
        None,
        "--spec",
        "-s",
        exists=True,
        readable=True,
        help="Existing markdown spec to revise into a better one",
    ),
    prompt: str | None = typer.Option(
        None, "--prompt", "-p", help="One-line idea to turn into a new spec file"
    ),
    out: Path = typer.Option(
        Path("spec.md"), "--out", "-o", help="Where to write the resulting spec file"
    ),
    no_interactive: bool = typer.Option(
        False, "--no-interactive", help="Skip the interview; use the prompt/spec alone"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use a canned spec (no model needed)"),
) -> None:
    """Write a spec file via a short interview — from a prompt, or by revising an existing spec.

    Provide exactly one input: a one-line ``--prompt`` to author a spec from scratch, or an
    existing markdown ``--spec`` file to revise into a better one. Either way the Product
    Manager (loading the ``elicit-requirements`` skill first) *talks to you* — asking about
    your needs and the technology to use, then following up on your answers — before writing
    the result to ``--out`` (default ``spec.md``; the input ``--spec`` file is left
    untouched). Feed the output to ``run --spec`` to build the project.
    """
    try:
        request = intake.resolve(spec, prompt)
    except intake.IntakeError as exc:
        raise typer.BadParameter(str(exc)) from exc

    mode = elicit.REVISE if request.origin == intake.FILE else elicit.GENERATE

    # Interview only when we can actually read answers: a real terminal, live model, and the
    # user didn't opt out. Otherwise fall back to using the prompt/spec alone.
    interactive = not no_interactive and not dry_run and sys.stdin.isatty()

    observability.configure_langsmith()
    action = "revise" if mode == elicit.REVISE else "spec"
    console.rule(
        f"[bold]Software Team · {action}[/bold] · {request.display} · {_mode_banner(dry_run)}"
    )
    if interactive:
        console.print("[dim]The PM will ask a few questions to shape the spec.[/dim]")
    else:
        source = "spec" if mode == elicit.REVISE else "prompt"
        console.print(f"[dim]Non-interactive: working from the {source} alone.[/dim]")

    path, _ = asyncio.run(
        elicit.generate_spec_file(
            request.text, out, mode=mode, interactive=interactive, dry_run=dry_run, console=console
        )
    )

    console.rule("[bold]Spec written[/bold]")
    console.print(f"  [green]✓[/green] {path}")
    console.print(f"\nNext: build it with [bold]software-team run --spec {path}[/bold]")


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
