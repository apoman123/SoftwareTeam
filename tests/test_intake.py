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


def test_spec_file_without_images_has_none(tmp_path):
    spec = tmp_path / "spec.md"
    spec.write_text("Build a Task API. No pictures here.", encoding="utf-8")

    assert intake.resolve(spec, None).images == ()


def test_spec_file_discovers_referenced_sample_images(tmp_path):
    (tmp_path / "mock.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "flow.jpg").write_bytes(b"\xff\xd8\xff")
    spec = tmp_path / "spec.md"
    spec.write_text(
        "# App\n"
        "Landing: ![hero](mock.png)\n"
        "Flow: ![flow](assets/flow.jpg)\n"
        "Brand: ![remote](https://example.com/logo.svg)\n"
        "Missing: ![gone](nope.png)\n"
        "Not an image: ![doc](spec.md)\n",
        encoding="utf-8",
    )

    images = intake.resolve(spec, None).images

    # Local images resolve to absolute paths; the remote URL passes through; the missing file
    # and the non-image reference are dropped.
    assert str((tmp_path / "mock.png").resolve()) in images
    assert str((tmp_path / "assets" / "flow.jpg").resolve()) in images
    assert "https://example.com/logo.svg" in images
    assert len(images) == 3


def test_prompt_requests_have_no_images():
    assert intake.resolve(None, "Build a thing").images == ()


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
