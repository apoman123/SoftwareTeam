"""Tests for image content blocks and the UX designer's multimodal prompt."""

import asyncio

from software_team.agents import base
from software_team.skills.common import media


def test_is_image_ref_matches_extensions():
    assert media.is_image_ref("mock.png")
    assert media.is_image_ref("a/b/shot.JPEG")
    assert media.is_image_ref("https://x.com/logo.svg?v=2")
    assert not media.is_image_ref("notes.md")
    assert not media.is_image_ref("https://x.com/page")


def test_local_image_is_inlined_as_base64(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    block = media.image_content_block(str(img))

    assert block is not None
    assert block["type"] == "image_url"
    assert block["image_url"]["url"].startswith("data:image/png;base64,")


def test_remote_url_passes_through():
    block = media.image_content_block("https://example.com/logo.png")
    assert block == {"type": "image_url", "image_url": {"url": "https://example.com/logo.png"}}


def test_unusable_refs_are_skipped(tmp_path):
    assert media.image_content_block(str(tmp_path / "missing.png")) is None
    text = tmp_path / "notes.txt"
    text.write_text("hi")
    assert media.image_content_block(str(text)) is None  # not an image mime
    # image_blocks drops the unusable ones and keeps the good remote URL.
    assert media.image_blocks([str(tmp_path / "missing.png"), "https://x.com/a.png"]) == [
        {"type": "image_url", "image_url": {"url": "https://x.com/a.png"}}
    ]


def test_generate_attaches_images_as_multimodal_content(monkeypatch, tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG\r\n")

    captured = {}

    async def fake_arun_turn(llm, messages, *, dry_run, config=None):
        captured["content"] = messages[-1].content
        return "ok"

    monkeypatch.setattr(base, "_arun_turn", fake_arun_turn)

    # Not a dry run, so images are attached; build_llm is never reached because _arun_turn
    # is stubbed, so no provider package or network is needed.
    state = {"dry_run": False, "current_phase": "plan"}
    result = asyncio.run(
        base.generate("ux_designer", "system", "describe the UI", state, images=[str(img)])
    )

    assert result == "ok"
    content = captured["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "describe the UI"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_generate_stays_text_only_in_dry_run(monkeypatch, tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"\x89PNG\r\n")

    captured = {}

    async def fake_arun_turn(llm, messages, *, dry_run, config=None):
        captured["content"] = messages[-1].content
        return "ok"

    monkeypatch.setattr(base, "_arun_turn", fake_arun_turn)

    state = {"dry_run": True, "current_phase": "plan"}
    asyncio.run(base.generate("ux_designer", "system", "describe", state, images=[str(img)]))

    # Dry-run keeps the prompt text-only (the offline stub is not multimodal).
    assert captured["content"] == "describe"
