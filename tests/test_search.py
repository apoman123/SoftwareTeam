"""Tests for web search: the per-run result cache and the disabled/no-op path."""

from software_team.skills.common import search


def test_web_search_caches_repeated_queries(monkeypatch):
    # Many characters (and the review/fix loops) re-issue identical queries; the cache must
    # make every repeat a hit so the backend is called exactly once per distinct query.
    monkeypatch.setattr(search.SETTINGS, "search_provider", "duckduckgo")
    search._CACHE.clear()
    calls = {"n": 0}

    def fake_duckduckgo(query, limit):
        calls["n"] += 1
        return [search.SearchResult("title", "url", f"body {query}")]

    monkeypatch.setattr(search, "_duckduckgo", fake_duckduckgo)

    first = search.web_search("best practices 2026")
    second = search.web_search("best practices 2026")
    third = search.web_search("BEST PRACTICES 2026")  # case-insensitive -> same key

    assert calls["n"] == 1
    assert first == second == third
    assert "body best practices 2026" in first


def test_web_search_disabled_returns_empty(monkeypatch):
    monkeypatch.setattr(search.SETTINGS, "search_provider", "none")
    assert search.web_search("anything at all") == ""
