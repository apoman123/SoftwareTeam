"""Internet search — let every character pull the latest facts from the web.

Local models have a training cut-off, so when a character needs current information for
its work (the latest API of a library, a current best practice, today's stable version,
a live pricing/quota number…) it can search the web first and fold the findings into its
prompt. This keeps generated code and docs from drifting to stale, half-remembered APIs.

The search is provider-agnostic (``SWTEAM_SEARCH_PROVIDER``):

* ``duckduckgo`` (default) — keyless, via the ``ddgs`` package.
* ``tavily`` — higher-quality results, needs ``TAVILY_API_KEY``.
* ``none`` / ``off`` — disabled.

Everything degrades gracefully: a missing package, a missing key, or a network error
returns an empty result (and a short note) rather than raising, so a run never breaks
just because the network is down. It is also a no-op in ``--dry-run``.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.tools import tool

from ...config import SETTINGS


@dataclass
class SearchResult:
    """A single web search hit (title, URL, and snippet)."""

    title: str
    url: str
    snippet: str

    def render(self) -> str:
        """Render the hit as a compact, citeable two-line markdown bullet."""
        body = self.snippet.strip().replace("\n", " ")
        return f"- {self.title.strip()} ({self.url.strip()})\n  {body}"


def web_search(query: str, max_results: int | None = None) -> str:
    """Search the web and return a compact, citeable text digest of the top results.

    Returns an empty string when search is disabled, the backend is unavailable, or
    nothing is found — callers should treat the result as best-effort context.
    """
    query = (query or "").strip()
    if not query or not SETTINGS.search_enabled:
        return ""

    limit = max_results or SETTINGS.search_max_results
    provider = SETTINGS.search_provider
    try:
        # duckduckgo is the default and the fallback for any unknown provider value.
        results = _tavily(query, limit) if provider == "tavily" else _duckduckgo(query, limit)
    except Exception:  # noqa: BLE001 - best-effort: never break a run on search failure
        return ""

    return "\n".join(hit.render() for hit in results[:limit])


def _duckduckgo(query: str, limit: int) -> list[SearchResult]:
    # The maintained package is `ddgs` (formerly `duckduckgo_search`); support both.
    try:
        from ddgs import DDGS
    except ImportError:  # pragma: no cover - fallback for the older package name
        from duckduckgo_search import DDGS  # type: ignore[no-redef]

    out: list[SearchResult] = []
    with DDGS() as ddgs:
        for hit in ddgs.text(query, max_results=limit):
            out.append(
                SearchResult(
                    title=str(hit.get("title", "")),
                    url=str(hit.get("href", hit.get("url", ""))),
                    snippet=str(hit.get("body", hit.get("snippet", ""))),
                )
            )
    return out


def _tavily(query: str, limit: int) -> list[SearchResult]:
    if not SETTINGS.tavily_api_key:
        return []
    from tavily import TavilyClient

    client = TavilyClient(api_key=SETTINGS.tavily_api_key)
    resp = client.search(query=query, max_results=limit)
    return [
        SearchResult(
            title=str(item.get("title", "")),
            url=str(item.get("url", "")),
            snippet=str(item.get("content", "")),
        )
        for item in resp.get("results", [])
    ]


@tool
def web_search_tool(query: str) -> str:
    """Search the internet for up-to-date information and return a digest of top results.

    Use this to look up the latest API of a library, current best practices, or today's
    stable versions before relying on training-time knowledge.
    """
    return web_search(query)
