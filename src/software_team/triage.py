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

# Explicit, unambiguous "no backend" phrasings — a product that is purely a client app.
# These always win: they are direct statements that there is no server-side code to build.
_BACKEND_OPTOUT: tuple[str, ...] = (
    "no backend",
    "no back-end",
    "without a backend",
    "without backend",
    "no server",
    "frontend only",
    "front-end only",
    "frontend-only",
    "client-side only",
)

# Weaker "looks like a static/client-only product" phrasings. Unlike the opt-outs above
# these are *ambiguous*: "static site" matches "Static Site Generation (SSG)", a frontend
# rendering technique that is routinely paired with a real backend (an API, a form handler).
# So a static-frontend hint suppresses the backend only when nothing explicitly names one —
# an explicit backend signal (``_BACKEND_POSITIVE``) overrides it.
_STATIC_FRONTEND_HINTS: tuple[str, ...] = (
    "static site",
    "static website",
    "serverless",
)

# Explicit signals that the product has server-side code to build, used to override an
# ambiguous static-frontend hint. Deliberately narrow (the literal word "backend" and named
# backend frameworks) so it does not fire on a genuinely backend-free static site.
_BACKEND_POSITIVE: tuple[str, ...] = (
    "backend",
    "back-end",
    "fastapi",
    "django",
    "flask",
    "express",
    "nestjs",
    "rails",
    "laravel",
    "microservice",
    "web service",
    "rest api",
    "graphql",
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

    Defaults to True (most products — including libraries and CLIs — are backend code). An
    explicit opt-out ("no backend", "frontend only") turns it off. A weaker static-frontend
    hint ("static site", "serverless") turns it off too, *unless* the spec also names a
    backend — because "Static Site Generation (SSG)" describes how the UI is rendered and is
    commonly paired with a real backend (e.g. a React SSG frontend with a FastAPI API). In
    that case the explicit backend signal wins, so the Software Engineer is not skipped.

    Args:
        spec_text: The raw spec / feature request.

    Returns:
        False only for an explicitly frontend-only / static product with no backend signal;
        True otherwise.
    """
    if _mentions(spec_text, _BACKEND_OPTOUT):
        return False
    if _mentions(spec_text, _STATIC_FRONTEND_HINTS):
        return _mentions(spec_text, _BACKEND_POSITIVE)
    return True


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
