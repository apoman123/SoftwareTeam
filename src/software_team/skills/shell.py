"""Shell skills — run commands and tests inside the generated workspace.

Used by QA (run the test suite) and by the SWE bug-fix loop. Commands run with the
workspace as the working directory and a timeout, so `import app` resolves and runs
are bounded.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def summary(self, max_chars: int = 4000) -> str:
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
        return CommandResult(124, e.stdout or "", f"timed out after {timeout}s")


def run_pytest(output_dir: str, timeout: int = 300) -> CommandResult:
    """Run the workspace test suite with the current interpreter.

    Uses `python -m pytest` so the workspace root is on sys.path[0] and the generated
    `app` package imports cleanly.
    """
    return run_command(
        output_dir,
        [sys.executable, "-m", "pytest", "-q", "--no-header"],
        timeout=timeout,
    )


@tool
def run_shell(output_dir: str, command: str) -> str:
    """Run a shell command inside the project workspace and return combined output."""
    import shlex

    return run_command(output_dir, shlex.split(command)).summary()


@tool
def run_tests(output_dir: str) -> str:
    """Run the project's pytest suite and return the result summary."""
    return run_pytest(output_dir).summary()
