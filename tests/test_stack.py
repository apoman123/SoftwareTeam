"""Tests for stack-agnostic behaviour: the team honours any requested language/technology.

Covers the two halves of the fix: ``stack_hint`` surfaces the stack a stakeholder asks for
(so the Tech Lead and Engineer build it), and ``detect_test_command`` runs the right test
command per ecosystem (so the QA quality gate is not hardwired to pytest).
"""

import sys

from software_team.agents.base import stack_hint
from software_team.skills.common import shell


def test_stack_hint_prefers_chosen_tech_stack():
    state = {"tech_stack": "Node.js + Express + PostgreSQL", "spec_text": "use python"}
    assert stack_hint(state).startswith("Node.js + Express")


def test_stack_hint_falls_back_to_requested_stack_from_spec():
    state = {"spec_text": "Build a REST API. Please use Node.js with Express."}
    hint = stack_hint(state)
    assert "node.js" in hint and "express" in hint


def test_stack_hint_detects_request_from_user_stories_too():
    state = {"user_stories": "As a dev I want a Go service so that it is fast."}
    assert "go" in stack_hint(state).split()


def test_stack_hint_ignores_substring_false_positives():
    # "go" must not be detected inside ordinary words like "goal" or "google".
    state = {"spec_text": "Our goal is a great product on google scale."}
    assert "go" not in stack_hint(state).split()


def test_stack_hint_empty_when_no_stack_known():
    assert stack_hint({"spec_text": "Track tasks with titles and a done flag."}) == ""


def test_detect_test_command_node(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert shell.detect_test_command(str(tmp_path))[:2] == ["npm", "test"]


def test_detect_test_command_go(tmp_path):
    (tmp_path / "go.mod").write_text("module x", encoding="utf-8")
    assert shell.detect_test_command(str(tmp_path)) == ["go", "test", "./..."]


def test_detect_test_command_rust(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]", encoding="utf-8")
    assert shell.detect_test_command(str(tmp_path)) == ["cargo", "test"]


def test_detect_test_command_defaults_to_pytest(tmp_path):
    # No ecosystem marker (or a Python one) -> pytest with the current interpreter.
    (tmp_path / "requirements.txt").write_text("pytest", encoding="utf-8")
    cmd = shell.detect_test_command(str(tmp_path))
    assert cmd[0] == sys.executable and "pytest" in cmd
