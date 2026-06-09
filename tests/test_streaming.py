"""Tests for the async streaming chat turn in ``agents.base``.

A node's LLM turn is awaited and streamed (``astream``, falling back to ``ainvoke``) so a
slow local model shows continuous progress instead of looking idle, and the HTTP
read-timeout bounds the gap between tokens rather than the whole generation. These tests
pin that behaviour (accumulation, multi-block content, and the fallbacks) without needing a
real model server.
"""

import asyncio

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from software_team.agents import base
from software_team.config import Settings


def _messages():
    return [HumanMessage(content="hi")]


def _run(coro):
    return asyncio.run(coro)


def test_run_turn_streams_and_accumulates():
    class StreamingModel:
        async def astream(self, messages, config=None):
            for piece in ["Hello ", "from ", "the ", "stream"]:
                yield AIMessageChunk(content=piece)

        async def ainvoke(self, messages, config=None):  # pragma: no cover - not reached
            raise AssertionError("ainvoke() should not run when streaming succeeds")

    out = _run(base._arun_turn(StreamingModel(), _messages(), dry_run=False))
    assert out == "Hello from the stream"


def test_run_turn_flattens_block_content():
    # Some providers (e.g. Anthropic) stream content as a list of typed blocks.
    class BlockStreamingModel:
        async def astream(self, messages, config=None):
            yield AIMessageChunk(content=[{"type": "text", "text": "block "}])
            yield AIMessageChunk(content=[{"type": "text", "text": "text"}])

        async def ainvoke(self, messages, config=None):  # pragma: no cover
            raise AssertionError("ainvoke() should not run when streaming succeeds")

    out = _run(base._arun_turn(BlockStreamingModel(), _messages(), dry_run=False))
    assert out == "block text"


def test_run_turn_falls_back_when_streaming_unsupported():
    class NoStreamModel:
        def astream(self, messages, config=None):
            raise NotImplementedError

        async def ainvoke(self, messages, config=None):
            return AIMessage(content="fallback content")

    out = _run(base._arun_turn(NoStreamModel(), _messages(), dry_run=False))
    assert out == "fallback content"


def test_run_turn_falls_back_on_empty_stream():
    class EmptyStreamModel:
        async def astream(self, messages, config=None):
            return
            yield  # makes this an async generator that yields nothing

        async def ainvoke(self, messages, config=None):
            return AIMessage(content="from ainvoke")

    out = _run(base._arun_turn(EmptyStreamModel(), _messages(), dry_run=False))
    assert out == "from ainvoke"


def test_run_turn_dry_run_uses_sync_invoke():
    class StubModel:
        def invoke(self, messages):
            return AIMessage(content="canned")

        async def astream(self, messages, config=None):  # pragma: no cover - not used in dry-run
            raise AssertionError("dry-run must not stream")
            yield

    out = _run(base._arun_turn(StubModel(), _messages(), dry_run=True))
    assert out == "canned"


def test_content_text_handles_str_list_and_none():
    assert base._content_text("plain") == "plain"
    assert base._content_text([{"text": "a"}, "b", {"content": "c"}]) == "abc"
    assert base._content_text(None) == ""


def test_recursion_limit_scales_with_loop_caps(monkeypatch):
    monkeypatch.setenv("SWTEAM_MAX_REVIEW_ITERS", "10")
    monkeypatch.setenv("SWTEAM_MAX_FIX_ITERS", "10")
    monkeypatch.setenv("SWTEAM_MAX_FEATURES", "7")
    settings = Settings()
    # High caps and a full feature plan must not starve the graph below the worst-case path:
    # the build loop runs up to max_features features, each re-reviewable up to the review cap.
    assert settings.max_features == 7
    assert settings.graph_recursion_limit == 40 + 7 * (10 + 1) * 2 + 10 * 3
    assert settings.graph_recursion_limit > 50
