"""Tests for the garbage-collection scanner."""

from software_team.skills.common import gc


def test_scan_flags_documentation_inconsistencies():
    docs = {"README.md": "See `app/gone.py` for details. Status: TBD."}
    findings = gc.scan(source_files={}, docs=docs)
    issues = [f.issue for f in findings if f.category == gc.CAT_DOC]
    assert any("does not exist" in i for i in issues)
    assert any("placeholder" in i for i in issues)


def test_scan_flags_architecture_violation():
    # A pure-logic module that imports a web framework breaks the layering principle.
    source = {"app/service.py": "import fastapi\n\n\ndef do():\n    return 1\n"}
    findings = gc.scan(source_files=source, docs={"README.md": "app/service.py"})
    assert any(f.category == gc.CAT_ARCH and "delivery framework" in f.issue for f in findings)


def test_scan_flags_technical_debt():
    body = "\n".join(
        ["def run():", "    # TODO: handle errors", "    print('debug')", "    return 1"] + [""] * 8
    )
    source = {"app/worker.py": body}
    findings = gc.scan(source_files=source, docs={"README.md": "app/worker.py worker"})
    issues = [f.issue for f in findings if f.category == gc.CAT_DEBT]
    assert any("markers" in i for i in issues)
    assert any("debug output" in i for i in issues)


def test_scan_clean_project_has_no_findings():
    calc = "\n".join(
        ["def add(a, b):", "    return a + b", "", "", "def sub(a, b):", "    return a - b"]
        + [f"# line {n}" for n in range(8)]
    )
    source = {
        "app/__init__.py": "",
        "app/calc.py": calc,
        "tests/test_calc.py": (
            "from app.calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
        ),
    }
    docs = {"README.md": "Run the calculator in `app/calc.py`."}
    assert gc.scan(source_files=source, docs=docs) == []


def test_scan_report_groups_and_summarises():
    findings = gc.scan(
        source_files={"app/service.py": "import flask\n" + "x = 1\n" * 12},
        docs={"README.md": "app/service.py"},
    )
    report = gc.scan_report(findings)
    assert "Garbage-Collection Report" in report
    assert "issue(s)" in report
    assert gc.CAT_ARCH in report

    assert "No documentation, architecture, or technical-debt issues found" in gc.scan_report([])
