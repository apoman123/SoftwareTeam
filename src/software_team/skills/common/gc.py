"""Garbage-collection scanner — static, offline sweep of a whole project for rot.

A dependency-free checker that scans a generated project for three kinds of accumulated
problem, each reported with a concrete fix:

* **Documentation inconsistency** — docs that reference a file that no longer exists, leftover
  placeholder text, or a source module that no documentation mentions.
* **Architecture violation** — a delivery framework imported inside a module that is meant to
  hold pure business logic (the codebase's own "keep logic framework-free" principle), an
  oversized "god" file, or a hardcoded secret.
* **Technical debt** — ``TODO``/``FIXME``/``XXX``/``HACK`` markers, bare/empty
  ``except``/``catch`` blocks, leftover debug prints, or a source module with no test.

It performs no network I/O and is deterministic, so it works in ``--dry-run``. Modelled on
``skills.common.security`` (``Finding`` / ``audit`` / ``audit_report`` / ``@tool``): the pure
``scan`` / ``scan_report`` functions take file maps, ``scan_workspace`` reads a directory and
scans it, and the ``garbage_scan`` ``@tool`` wraps it for tool-capable models.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.tools import tool

from . import filesystem

# Finding categories.
CAT_DOC = "Documentation inconsistency"
CAT_ARCH = "Architecture violation"
CAT_DEBT = "Technical debt"

# Files treated as documentation (context) rather than editable source — mirrors project.py.
_DOC_PREFIX = "docs/"
_DOC_FILES = frozenset({"README.md"})

# A source file big enough to be worth checks that skip trivial files.
_SIGNIFICANT_LINES = 10
# A "god file" past this many lines is flagged as an architecture/maintainability smell.
_GOD_FILE_LINES = 400

# Module/path hints that a file is meant to hold pure business logic (no delivery framework).
_PURE_HINTS = ("service", "domain", "core", "logic", "model", "entities", "repository", "usecase")
# Delivery frameworks that should not be imported by a pure-logic module.
_FRAMEWORK_TOKENS = (
    "fastapi",
    "flask",
    "django",
    "starlette",
    "rest_framework",
    "express",
    "@nestjs",
    "react",
    "vue",
)
# Code extensions used to recognise a doc reference that points at a project file.
_CODE_EXTS = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php",
    ".yaml", ".yml", ".json", ".toml", ".sql", ".tf", ".sh", ".md",
)

_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
_SECRET_RE = re.compile(
    r"""(?ix)\b(password|passwd|secret|api[_-]?key|access[_-]?token|aws_secret_access_key)\b"""
    r"""\s*[:=]\s*['"][^'"]{4,}['"]"""
)
_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:", re.MULTILINE)
_EMPTY_CATCH_RE = re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}")
# Backtick-quoted token or markdown-link target that looks like a relative project path.
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_MD_LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?\s*\)")


@dataclass(frozen=True)
class Finding:
    """A single garbage-collection finding: category, location, the issue, and the fix."""

    category: str
    location: str
    issue: str
    fix: str

    def render(self) -> str:
        """Render the finding as a markdown bullet."""
        return f"⚠️ **{self.location}** — {self.issue} _(fix: {self.fix})_"


def _is_doc(path: str) -> bool:
    """Return whether ``path`` is documentation (scanned for refs, not as source)."""
    return path.startswith(_DOC_PREFIX) or path in _DOC_FILES


def _is_test(path: str) -> bool:
    """Return whether ``path`` looks like a test file."""
    return "test" in path.lower() or "spec." in path.lower()


def _basename(path: str) -> str:
    """Return the final path component."""
    return path.rsplit("/", 1)[-1]


def _significant(content: str) -> bool:
    """Return whether a file is non-trivial enough to be worth the deeper checks."""
    return len(content.splitlines()) >= _SIGNIFICANT_LINES


def _scan_docs(source_files: dict[str, str], docs: dict[str, str]) -> list[Finding]:
    """Flag documentation that drifts from the code: dead references and placeholders."""
    findings: list[Finding] = []
    known = set(source_files) | set(docs)
    for doc_path, text in docs.items():
        lowered = text.lower()
        for placeholder in ("lorem ipsum", "tbd", "<placeholder>", "coming soon"):
            if placeholder in lowered:
                findings.append(
                    Finding(
                        CAT_DOC,
                        doc_path,
                        f"contains placeholder text ('{placeholder}')",
                        "replace the placeholder with real content or remove the section",
                    )
                )
        refs = set(_BACKTICK_RE.findall(text)) | set(_MD_LINK_RE.findall(text))
        for ref in refs:
            ref = ref.strip()
            if "/" not in ref or ref.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not ref.lower().endswith(_CODE_EXTS):
                continue
            if ref not in known:
                findings.append(
                    Finding(
                        CAT_DOC,
                        doc_path,
                        f"references `{ref}`, which does not exist in the project",
                        "update the reference to an existing path or remove it",
                    )
                )
    # Significant source modules that no documentation mentions.
    doc_blob = "\n".join(docs.values())
    for path, content in source_files.items():
        if _is_test(path) or _basename(path).startswith("__") or not _significant(content):
            continue
        stem = _basename(path).rsplit(".", 1)[0]
        if path not in doc_blob and stem not in doc_blob:
            findings.append(
                Finding(
                    CAT_DOC,
                    path,
                    "is not referenced by any documentation",
                    "document the module (or remove it if it is dead)",
                )
            )
    return findings


def _scan_architecture(source_files: dict[str, str], tech_stack: str = "") -> list[Finding]:
    """Flag layering violations, god files, and hardcoded secrets in source."""
    findings: list[Finding] = []
    for path, content in source_files.items():
        if _is_test(path):
            continue
        lowered_path = path.lower()
        lowered = content.lower()
        if any(hint in lowered_path for hint in _PURE_HINTS):
            hit = next((tok for tok in _FRAMEWORK_TOKENS if tok in lowered), None)
            if hit:
                findings.append(
                    Finding(
                        CAT_ARCH,
                        path,
                        f"a pure-logic module imports the delivery framework '{hit}'",
                        "move framework code into a thin adapter; keep this module framework-free",
                    )
                )
        line_count = len(content.splitlines())
        if line_count > _GOD_FILE_LINES:
            findings.append(
                Finding(
                    CAT_ARCH,
                    path,
                    f"is a 'god file' ({line_count} lines)",
                    "split it into focused modules with single responsibilities",
                )
            )
        if _SECRET_RE.search(content):
            findings.append(
                Finding(
                    CAT_ARCH,
                    path,
                    "contains a hardcoded secret",
                    "move the secret to configuration/environment and inject it at runtime",
                )
            )
    return findings


def _scan_debt(source_files: dict[str, str]) -> list[Finding]:
    """Flag TODO markers, empty exception handlers, debug prints, and untested modules."""
    findings: list[Finding] = []
    test_blob = "\n".join(c for p, c in source_files.items() if _is_test(p))
    for path, content in source_files.items():
        if _is_test(path):
            continue
        markers = sorted(set(_MARKER_RE.findall(content)))
        if markers:
            findings.append(
                Finding(
                    CAT_DEBT,
                    path,
                    f"has unresolved markers ({', '.join(markers)})",
                    "resolve the work the marker describes, then delete the marker",
                )
            )
        if _BARE_EXCEPT_RE.search(content) or _EMPTY_CATCH_RE.search(content):
            findings.append(
                Finding(
                    CAT_DEBT,
                    path,
                    "swallows errors with a bare/empty exception handler",
                    "catch a specific error and handle or re-raise it; never silently pass",
                )
            )
        if "print(" in content or "console.log(" in content:
            findings.append(
                Finding(
                    CAT_DEBT,
                    path,
                    "contains leftover debug output (print/console.log)",
                    "remove the debug call or replace it with structured logging",
                )
            )
        if _basename(path).startswith("__") or not _significant(content):
            continue
        stem = _basename(path).rsplit(".", 1)[0]
        if path not in test_blob and stem not in test_blob:
            findings.append(
                Finding(
                    CAT_DEBT,
                    path,
                    "has no corresponding test",
                    "add unit tests covering this module's behaviour",
                )
            )
    return findings


def scan(
    source_files: dict[str, str], docs: dict[str, str], tech_stack: str = ""
) -> list[Finding]:
    """Run every check over the project's files and return all findings.

    Args:
        source_files: Editable code/config files (path -> content).
        docs: Documentation files (path -> content), scanned for stale references.
        tech_stack: The project's declared stack, for stack-aware checks (optional).

    Returns:
        Every finding across documentation, architecture, and technical-debt checks.
    """
    return (
        _scan_docs(source_files, docs)
        + _scan_architecture(source_files, tech_stack)
        + _scan_debt(source_files)
    )


def scan_report(findings: list[Finding]) -> str:
    """Render the findings as a markdown garbage-collection report, grouped by category."""
    lines = ["# Garbage-Collection Report", ""]
    if not findings:
        lines += ["✅ No documentation, architecture, or technical-debt issues found.", ""]
        return "\n".join(lines)

    lines.append(f"**{len(findings)} issue(s)** found across the project.")
    lines.append("")
    for category in (CAT_DOC, CAT_ARCH, CAT_DEBT):
        group = [f for f in findings if f.category == category]
        if not group:
            continue
        lines.append(f"## {category} ({len(group)})")
        lines += [f"- {f.render()}" for f in group]
        lines.append("")
    return "\n".join(lines)


def scan_workspace(output_dir: str) -> list[Finding]:
    """Read every text file in ``output_dir`` and scan the whole project.

    Args:
        output_dir: The workspace directory holding the project.

    Returns:
        Every finding across the project's files (binaries are skipped).
    """
    source_files: dict[str, str] = {}
    docs: dict[str, str] = {}
    for rel_path in filesystem.list_tree(output_dir):
        try:
            content = filesystem.read_file(output_dir, rel_path)
        except (UnicodeDecodeError, ValueError):
            continue  # skip binaries / anything outside the workspace
        (docs if _is_doc(rel_path) else source_files)[rel_path] = content
    return scan(source_files, docs)


@tool
def garbage_scan(output_dir: str) -> str:
    """Scan a whole project for doc inconsistencies, architecture violations, and tech debt.

    Reads the project at ``output_dir`` and returns a markdown report grouped by category,
    each finding paired with a concrete fix. Use it before a clean-up to know what to fix.
    """
    return scan_report(scan_workspace(output_dir))
