"""Deterministic project triage — decide which parts of the SDLC a spec actually needs.

Keyword heuristics over the raw spec set capability flags so the graph can skip phases
that do not apply: a pure API or library needs no frontend, and a library, CLI tool or
script needs no containerisation/CI-CD/deployment. The classification is deterministic (no
LLM) so routing is reproducible, testable and dry-run-safe — and robust even on a weakly
instruction-following local model. Defaults are conservative: when the spec is ambiguous
the team assumes a deployable backend service with no frontend.
"""

from __future__ import annotations

import re

# A user interface is wanted when the spec mentions any of these. Whole-word matched so
# "ui" is not found inside "build" and "page" hints are scoped (e.g. "web page").
_FRONTEND_HINTS: tuple[str, ...] = (
    "frontend",
    "front-end",
    "ui",
    "user interface",
    "gui",
    "web app",
    "webapp",
    "web application",
    "website",
    "web page",
    "web-based",
    "single page",
    "single-page",
    "spa",
    "dashboard",
    "screen",
    "landing page",
    "portal",
    "mobile app",
    "android",
    "ios",
    "react",
    "vue",
    "angular",
    "svelte",
    "next.js",
    "tailwind",
    "html",
    "css",
    "browser",
)

# Explicit "no UI" phrasings. Checked first so they win over a stray UI keyword (e.g. the
# word "frontend" inside "no frontend") — keyword matching alone cannot handle negation.
_FRONTEND_OPTOUT: tuple[str, ...] = (
    "no frontend",
    "no front-end",
    "no ui",
    "without a frontend",
    "without frontend",
    "without a ui",
    "headless",
    "api only",
    "api-only",
    "backend only",
    "backend-only",
)

# Explicit "no backend" phrasings — a product that is purely a static site / client app.
_BACKEND_OPTOUT: tuple[str, ...] = (
    "no backend",
    "no back-end",
    "without a backend",
    "without backend",
    "no server",
    "serverless",
    "frontend only",
    "front-end only",
    "frontend-only",
    "client-side only",
    "static site",
    "static website",
)

# Explicit "no deployment" phrasings — keep it local, don't containerise/ship it.
_DEPLOY_OPTOUT: tuple[str, ...] = (
    "no deployment",
    "no deploy",
    "without deployment",
    "not deployed",
    "do not deploy",
    "don't deploy",
    "no ci/cd",
    "no ci",
    "local only",
    "local-only",
    "run locally",
)

# Strong signals that the product is deployed/operated as a running service.
_DEPLOY_POSITIVE: tuple[str, ...] = (
    "deploy",
    "deployment",
    "kubernetes",
    "k8s",
    "docker",
    "container",
    "hosted",
    "cloud",
    "production",
    "microservice",
    "web service",
    "server",
    "daemon",
    "saas",
    "ci/cd",
)

# Signals that the product is a local artifact with nothing to deploy.
_DEPLOY_NEGATIVE: tuple[str, ...] = (
    "library",
    "package",
    "cli",
    "command-line",
    "command line",
    "script",
    "sdk",
    "plugin",
    "snippet",
    "module",
)


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    """Return whether ``text`` contains any of ``terms`` as a whole token.

    Args:
        text: Free text to search (case-insensitive).
        terms: Lower-cased terms to look for; spaces/punctuation in a term are literal.

    Returns:
        True if any term is present bounded by non-alphanumeric characters.
    """
    lowered = text.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered) for term in terms)


def needs_frontend(spec_text: str) -> bool:
    """Decide whether the spec calls for a user-facing frontend.

    An explicit opt-out ("no frontend", "API only") wins; otherwise a UI/frontend keyword
    turns it on; otherwise off (the default — most backend specs have no UI).

    Args:
        spec_text: The raw spec / feature request.

    Returns:
        True when a UI/frontend is indicated; False otherwise.
    """
    if _mentions(spec_text, _FRONTEND_OPTOUT):
        return False
    return _mentions(spec_text, _FRONTEND_HINTS)


def needs_backend(spec_text: str) -> bool:
    """Decide whether the spec calls for backend/server-side code.

    Defaults to True (most products — including libraries and CLIs — are backend code);
    only an explicit opt-out ("no backend", "static site", "frontend only") turns it off.

    Args:
        spec_text: The raw spec / feature request.

    Returns:
        False only for an explicitly frontend-only / static product; True otherwise.
    """
    return not _mentions(spec_text, _BACKEND_OPTOUT)


def needs_deployment(spec_text: str) -> bool:
    """Decide whether the spec calls for containerisation, CI/CD and deployment.

    An explicit opt-out ("no deployment", "run locally") wins; otherwise a positive
    deployment signal turns it on; otherwise the team defaults to a deployable service
    unless the product is clearly a local library/CLI/script.

    Args:
        spec_text: The raw spec / feature request.

    Returns:
        True when the product should be deployed; False for a local library/CLI/script.
    """
    if _mentions(spec_text, _DEPLOY_OPTOUT):
        return False
    if _mentions(spec_text, _DEPLOY_POSITIVE):
        return True
    # Otherwise deployable by default, unless it is clearly a local library/CLI/script.
    return not _mentions(spec_text, _DEPLOY_NEGATIVE)
