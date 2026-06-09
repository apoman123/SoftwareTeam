"""Linter runner — language-aware static analysis whose findings become fix suggestions.

Mirrors :func:`software_team.skills.common.shell.run_test_suites`: it detects the project's
linter from its manifest files, runs it over the project root and each component directory,
and **skips** (never fails) when the linter or its toolchain is unavailable — so the gate
works in a bare environment yet lints everything it can. The diagnostics it returns are fed
to the Tech Lead review, which turns each one into a constructive, actionable fix suggestion
for the engineer.

Linting is **advisory**: unlike the test suite, a linter finding never blocks a run on its
own; it guides the next build pass. Exposed as a plain function (``run_linters``) for the
review node and as a LangChain ``@tool`` (``run_lint``) for tool-capable models, mirroring the
other skills in ``common/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool

from .shell import _COMPONENT_DIRS, CommandResult, _deps_missing, _has, run_command


def detect_lint_command(output_dir: str) -> list[str] | None:
    """Choose the linter command for the project in ``output_dir`` from its manifest files.

    Returns the standard linter invocation for the first ecosystem detected (Node, Go, Rust,
    PHP, Ruby, then Python), or ``None`` when no known linter applies — so a directory with
    nothing to lint is simply skipped rather than forced through an irrelevant tool.

    Args:
        output_dir: The directory holding the (component of the) generated project.

    Returns:
        The linter command (argv list), or ``None`` when no linter is applicable.
    """
    root = Path(output_dir)
    if _has(root, "package.json"):
        # --no-install so a missing eslint fails fast (skipped) instead of fetching from the net.
        return ["npx", "--no-install", "eslint", "."]
    if _has(root, "go.mod"):
        return ["go", "vet", "./..."]
    if _has(root, "Cargo.toml"):
        return ["cargo", "clippy", "-q"]
    if _has(root, "composer.json"):
        return ["composer", "exec", "phpcs"]
    if _has(root, "Gemfile"):
        return ["bundle", "exec", "rubocop"]
    # Python (and the dry-run project): ruff if there is a manifest or any .py file present.
    if _has(root, "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt") or any(
        root.glob("*.py")
    ):
        return ["ruff", "check", "."]
    return None


@dataclass
class LintRun:
    """One component's lint execution: its directory, the command, and the result."""

    component: str
    command: list[str]
    result: CommandResult


@dataclass
class LintOutcome:
    """The combined result of linting every applicable component.

    ``runs`` are the linters that actually executed; ``skipped`` names components that had a
    linter but could not be run (toolchain or dependencies absent), with the reason. A missing
    linter is always a skip, never a failure — linting is advisory.
    """

    runs: list[LintRun]
    skipped: list[str]

    @property
    def clean(self) -> bool:
        """Return whether every linter that ran reported no issues."""
        return all(run.result.ok for run in self.runs)

    @property
    def components_with_issues(self) -> int:
        """Return how many components the linter flagged (non-zero exit)."""
        return sum(1 for run in self.runs if not run.result.ok)

    def summary(self, max_chars: int = 3000) -> str:
        """Render a per-component lint summary for prompt embedding / reporting."""
        lines: list[str] = []
        for run in self.runs:
            verdict = "no issues" if run.result.ok else "issues found"
            lines.append(f"[{run.component}] {' '.join(run.command)} -> {verdict}")
            if not run.result.ok:
                body = run.result.summary(max_chars)
                if body:
                    lines.append(body)
        for name in self.skipped:
            lines.append(f"[skipped] {name}")
        return "\n".join(lines).strip() or "no linter applicable"


def run_linters(output_dir: str, timeout: int = 180) -> LintOutcome:
    """Lint the project root and each component subdirectory (an advisory quality aid).

    Each directory with a detectable linter gets its standard command. Components whose
    dependencies are not installed, or whose linter/toolchain is missing (exit 127), are
    skipped rather than failed.

    Args:
        output_dir: The workspace directory holding the generated project.
        timeout: Maximum seconds to allow each component's lint run.

    Returns:
        A :class:`LintOutcome` with the linters that ran and the components skipped.
    """
    root = Path(output_dir)
    components = ["."] + [name for name in _COMPONENT_DIRS if (root / name).is_dir()]
    runs: list[LintRun] = []
    skipped: list[str] = []
    for component in components:
        component_dir = root if component == "." else root / component
        command = detect_lint_command(str(component_dir))
        if command is None:
            continue
        if _deps_missing(component_dir):
            skipped.append(f"{component} (dependencies not installed)")
            continue
        result = run_command(str(component_dir), command, timeout=timeout)
        if result.returncode == 127:
            skipped.append(f"{component} (linter not installed)")
        else:
            runs.append(LintRun(component, command, result))
    return LintOutcome(runs=runs, skipped=skipped)


@tool
def run_lint(output_dir: str) -> str:
    """Detect the project's linter, run it, and return the diagnostics summary.

    Returns the per-component lint output (issues and skips). Use it to find concrete coding
    problems in the generated code and turn each into a constructive fix.
    """
    return run_linters(output_dir).summary()
