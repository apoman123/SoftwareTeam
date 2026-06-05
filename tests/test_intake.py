"""Tests for feature-request intake — the two ways to hand the team work."""

import pytest

from software_team import intake


def test_resolve_from_spec_file_reads_text(tmp_path):
    spec = tmp_path / "spec.md"
    spec.write_text("Build a Task API.", encoding="utf-8")

    request = intake.resolve(spec, None)

    assert request.origin == intake.FILE
    assert request.text == "Build a Task API."
    assert request.label == str(spec)
    assert request.display == str(spec)


def test_resolve_from_prompt_keeps_text():
    request = intake.resolve(None, "Build a URL shortener with click analytics")

    assert request.origin == intake.PROMPT
    assert request.text == "Build a URL shortener with click analytics"
    assert request.label == intake.PROMPT_LABEL


def test_prompt_is_stripped():
    assert intake.resolve(None, "  trim me  ").text == "trim me"


def test_prompt_display_is_quoted_and_truncated():
    request = intake.resolve(None, "word " * 50)

    assert request.display.startswith('"')
    assert request.display.endswith('"')
    assert request.display.endswith('…"')


def test_resolve_requires_an_input(tmp_path):
    with pytest.raises(intake.IntakeError):
        intake.resolve(None, None)


def test_resolve_rejects_both_inputs(tmp_path):
    spec = tmp_path / "spec.md"
    spec.write_text("either or", encoding="utf-8")
    with pytest.raises(intake.IntakeError):
        intake.resolve(spec, "also a prompt")


def test_resolve_rejects_blank_prompt():
    with pytest.raises(intake.IntakeError):
        intake.resolve(None, "   ")
