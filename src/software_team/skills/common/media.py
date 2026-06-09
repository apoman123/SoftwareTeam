"""Image helpers — turn sample images referenced by a spec into LLM content blocks.

A stakeholder's spec sometimes ships with sample images (mock-ups, screenshots, brand
references). These helpers detect such references and encode them as the multimodal
``image_url`` content blocks that vision-capable chat models accept (Anthropic Claude,
OpenAI GPT-4o, Google Gemini), so the UI/UX Designer can actually *look* at them. Local
files are inlined as base64 ``data:`` URLs (no network, works offline); ``http(s)`` URLs
are passed through for the provider to fetch.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

# Raster/vector formats the vision models accept. Lower-cased, with the leading dot.
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
)


def is_image_ref(ref: str) -> bool:
    """Return whether ``ref`` looks like an image file path or image URL (by extension)."""
    ref = (ref or "").split("?", 1)[0].split("#", 1)[0]
    return Path(ref).suffix.lower() in IMAGE_EXTENSIONS


def _is_remote(ref: str) -> bool:
    """Return whether ``ref`` is an http(s) URL (passed through for the model to fetch)."""
    return ref.startswith("http://") or ref.startswith("https://")


def image_content_block(ref: str) -> dict[str, Any] | None:
    """Encode one image reference as an ``image_url`` content block, or ``None`` if unusable.

    A local path that exists is read and inlined as a base64 ``data:`` URL; an ``http(s)``
    URL is passed through unchanged. Anything else (missing file, non-image, unreadable)
    returns ``None`` so the caller can skip it without failing the run.

    Args:
        ref: An image file path or URL.

    Returns:
        A ``{"type": "image_url", "image_url": {"url": ...}}`` block, or ``None``.
    """
    if _is_remote(ref):
        return {"type": "image_url", "image_url": {"url": ref}}
    path = Path(ref)
    if not path.is_file():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not mime.startswith("image/"):
        return None
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}


def image_blocks(refs: list[str]) -> list[dict[str, Any]]:
    """Encode every usable image reference in ``refs`` as a content block (skipping the rest)."""
    blocks: list[dict[str, Any]] = []
    for ref in refs:
        block = image_content_block(ref)
        if block is not None:
            blocks.append(block)
    return blocks
