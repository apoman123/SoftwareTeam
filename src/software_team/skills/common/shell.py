"""Shell capabilities — run commands and tests inside the generated workspace.

Used by QA (run the test suite) and by the SWE bug-fix loop. Commands run with the
workspace as the working directory and a timeout, so `import app` resolves and runs are
bounded.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool


def _to_text(value: object) -> str:
    """Coerce subprocess output (``str``, ``bytes``, or ``None``) to text.

    ``subprocess`` returns ``str`` in text mode, but ``TimeoutExpired`` can still carry the
    raw ``bytes`` captured before the process was killed. Decoding here keeps
    :class:`CommandResult` uniformly string-typed so :meth:`CommandResult.summary` never
    mixes ``str`` and ``bytes``.

    Args:
        value: The stdout/stderr value from a subprocess run or exception.

    Returns:
        The value as text ("" for ``None``; bytes decoded as UTF-8, replacing bad bytes).
    """
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


@dataclass
class CommandResult:
    """The outcome of a subprocess run: exit code plus captured stdout/stderr."""

    returncode: int
    stdout: str
    stderr: str

    def __post_init__(self) -> None:
        """Normalise stdout/stderr to text so combining them never mixes str and bytes."""
        self.stdout = _to_text(self.stdout)
        self.stderr = _to_text(self.stderr)

    @property
    def ok(self) -> bool:
        """Return whether the command exited successfully (zero exit code)."""
        return self.returncode == 0

    def summary(self, max_chars: int = 4000) -> str:
        """Return combined stdout/stderr, trimmed to ``max_chars`` for prompt embedding."""
        body = (self.stdout + ("\n" + self.stderr if self.stderr else "")).strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "\n... (truncated)"
        return body


def run_command(output_dir: str, command: list[str], timeout: int = 300) -> CommandResult:
    """Run a command list with cwd=output_dir. Never raises on non-zero exit."""
    workdir = Path(output_dir)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            command,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)
    except FileNotFoundError as e:
        return CommandResult(127, "", f"command not found: {e}")
    except subprocess.TimeoutExpired as e:
        # On timeout, captured output may be bytes even in text mode; _to_text (via
        # __post_init__) normalises stdout, and we keep stderr plus a clear timeout note.
        captured = _to_text(e.stderr)
        note = f"timed out after {timeout}s"
        return CommandResult(124, e.stdout or "", f"{captured}\n{note}".strip())


def _has(root: Path, *names: str) -> bool:
    """Return whether any of ``names`` exists directly under ``root``."""
    return any((root / name).exists() for name in names)


def detect_test_command(output_dir: str) -> list[str]:
    """Choose the test command for the project in ``output_dir`` from its manifest files.

    Inspects the workspace for the marker file of each ecosystem and returns the standard
    test invocation for the first one found, so the same quality gate works for any stack
    (Node.js, Go, Rust, Java, …). Falls back to ``python -m pytest`` — which also covers
    the dry-run project — when no other ecosystem is detected.

    Args:
        output_dir: The workspace directory holding the generated project.

    Returns:
        The command (argv list) that runs the project's test suite.
    """
    root = Path(output_dir)
    if _has(root, "package.json"):
        return ["npm", "test", "--silent"]
    if _has(root, "go.mod"):
        return ["go", "test", "./..."]
    if _has(root, "Cargo.toml"):
        return ["cargo", "test"]
    if _has(root, "pom.xml"):
        return ["mvn", "-q", "test"]
    if _has(root, "build.gradle", "build.gradle.kts"):
        return ["gradle", "test", "-q"]
    if _has(root, "composer.json"):
        return ["composer", "test"]
    if _has(root, "mix.exs"):
        return ["mix", "test"]
    if _has(root, "Gemfile"):
        return ["bundle", "exec", "rspec"]
    # Default: Python (and the canned dry-run project) — `python -m pytest` so the workspace
    # root is on sys.path[0] and the generated package imports cleanly.
    return [sys.executable, "-m", "pytest", "-q", "--no-header"]


def run_project_tests(output_dir: str, timeout: int = 300) -> CommandResult:
    """Detect the project's stack and run its test suite (a language-agnostic quality gate).

    Args:
        output_dir: The workspace directory holding the generated project.
        timeout: Maximum seconds to allow the test run before failing fast.

    Returns:
        The command result; ``returncode`` 127 when the stack's test tool is not installed.
    """
    return run_command(output_dir, detect_test_command(output_dir), timeout=timeout)


# Subdirectories tested as their own component alongside the project root. The Frontend
# Engineer writes the UI under ``frontend/``, so a full-stack repo has two test suites.
_COMPONENT_DIRS: tuple[str, ...] = ("frontend",)

# Ecosystem manifests that mark a directory as having a runnable test setup.
_TEST_MANIFESTS: tuple[str, ...] = (
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "mix.exs",
    "Gemfile",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
)


def _has_test_setup(component: Path) -> bool:
    """Return whether ``component`` has something we know how to test."""
    return _has(component, *_TEST_MANIFESTS) or (component / "tests").is_dir()


def _deps_missing(component: Path) -> bool:
    """Return whether a component's dependencies are clearly not installed yet.

    For ecosystems whose test command cannot run without a fetched dependency tree (Node's
    ``node_modules``, PHP's ``vendor``), this lets the gate *skip* the component rather than
    report a spurious failure. Compiled-language toolchains fetch deps during the test run,
    so they are not gated here (a missing toolchain surfaces as a 127 skip instead).
    """
    node = (component / "package.json").exists() and not (component / "node_modules").is_dir()
    php = (component / "composer.json").exists() and not (component / "vendor").is_dir()
    return node or php


@dataclass
class TestRun:
    """One component's test execution: its directory, the command, and the result."""

    component: str
    command: list[str]
    result: CommandResult


@dataclass
class GateOutcome:
    """The combined result of running every testable component's suite.

    ``runs`` are the suites that actually executed; ``skipped`` names components that were
    not run (toolchain or dependencies not installed), with the reason. A missing toolchain
    is a skip, never a failure, so the gate does not block on an unavailable runtime.
    """

    runs: list[TestRun]
    skipped: list[str]

    @property
    def passed(self) -> bool:
        """Pass when every suite that actually ran passed (vacuously true if none ran)."""
        return all(run.result.ok for run in self.runs)

    def summary(self, max_chars: int = 4000) -> str:
        """Render a per-component summary for prompt embedding / reporting."""
        lines: list[str] = []
        for run in self.runs:
            verdict = "passed" if run.result.ok else f"FAILED (exit {run.result.returncode})"
            lines.append(f"[{run.component}] {' '.join(run.command)} -> {verdict}")
            body = run.result.summary(max_chars)
            if body:
                lines.append(body)
        for name in self.skipped:
            lines.append(f"[skipped] {name}")
        return "\n".join(lines).strip() or "no test suites found"


def run_test_suites(output_dir: str, timeout: int = 300) -> GateOutcome:
    """Run the test suite of the project root and of each component subdirectory.

    Each testable directory (the root, plus ``frontend/`` etc.) gets its detected test
    command. Components whose dependencies are not installed, or whose toolchain is missing
    (exit 127), are skipped rather than failed — so the gate works in a bare environment yet
    still runs everything that can run.

    Args:
        output_dir: The workspace directory holding the generated project.
        timeout: Maximum seconds to allow each component's test run.

    Returns:
        A :class:`GateOutcome` with the suites that ran and the components skipped.
    """
    root = Path(output_dir)
    components = ["."] + [name for name in _COMPONENT_DIRS if (root / name).is_dir()]
    runs: list[TestRun] = []
    skipped: list[str] = []
    for component in components:
        component_dir = root if component == "." else root / component
        if not _has_test_setup(component_dir):
            continue
        if _deps_missing(component_dir):
            skipped.append(f"{component} (dependencies not installed)")
            continue
        command = detect_test_command(str(component_dir))
        result = run_command(str(component_dir), command, timeout=timeout)
        if result.returncode == 127:
            skipped.append(f"{component} (toolchain not installed)")
        else:
            runs.append(TestRun(component, command, result))
    return GateOutcome(runs=runs, skipped=skipped)


@tool
def run_shell(output_dir: str, command: str) -> str:
    """Run a shell command inside the project workspace and return combined output."""
    import shlex

    return run_command(output_dir, shlex.split(command)).summary()


@tool
def run_tests(output_dir: str) -> str:
    """Detect the project's stack, run its test suite, and return the result summary."""
    return run_project_tests(output_dir).summary()
