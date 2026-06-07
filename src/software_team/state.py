"""Shared team state — the "blackboard" passed between every agent in the graph.

Each phase reads what earlier roles produced and writes its own artifacts. Most fields
are plain strings (markdown / yaml / code) so they can be persisted to disk verbatim.
`source_files` is a path -> content map for the generated application.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage

from . import triage

# How a run is framed. ``build`` is the default greenfield mode (turn a spec into a brand
# new project); ``feature`` is the brownfield/incremental mode (integrate a new feature
# into software the team has already developed). See ``new_feature_state``.
BUILD_MODE = "build"
FEATURE_MODE = "feature"

# Header that marks the existing-software context block in a feature-mode prompt. It is a
# stable sentinel: ``agents.base.feature_brief`` emits it and the dry-run stub keys off it
# to return the incremental-feature variant of its canned output.
FEATURE_BRIEF_HEADER = "## Existing software you are extending (incremental feature mode)"


def _merge_dict(left: dict[str, str], right: dict[str, str]) -> dict[str, str]:
    """Reducer that merges file maps so multiple SWE passes accumulate files."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class TeamState(TypedDict, total=False):
    """The shared blackboard passed between every agent in the graph.

    Each phase reads what earlier roles produced and writes its own artifacts. All keys
    are optional (``total=False``) because each node contributes only its own slice.
    """

    # --- Input ---
    spec_path: str
    spec_text: str
    output_dir: str
    dry_run: bool
    mode: str  # BUILD_MODE (greenfield) or FEATURE_MODE (extend existing software)
    baseline: str  # feature mode only: rendered digest of the existing software

    # --- Capability flags (set by deterministic triage; gate which phases run) ---
    needs_frontend: bool  # build a UI? -> runs the UX designer + frontend engineer
    needs_backend: bool  # build server-side code? -> runs the software engineer (backend)
    needs_deployment: bool  # deploy it? -> runs containerisation, CI/CD, K8s, operate

    # --- Product Manager ---
    user_stories: str
    acceptance_criteria: str
    backlog: str

    # --- UI/UX Designer ---
    ux_design: str  # written UI/UX description handed to the Tech Lead (no drawings)

    # --- Tech Lead / Architect ---
    architecture: str
    tech_stack: str
    api_spec: str
    db_schema: str

    # --- QA planning ---
    test_plan: str

    # --- Software Engineer ---
    source_files: Annotated[dict[str, str], _merge_dict]
    unit_tests: str

    # --- Code review (Tech Lead) ---
    review_notes: str
    review_status: str  # "approve" | "changes"

    # --- DevOps / SRE ---
    dockerfile: str
    ci_config: str
    cd_config: str
    gitlab_ci: str  # .gitlab-ci.yml — GitLab CI/CD that triggers Jenkins
    jenkinsfile: str  # Declarative Jenkins pipeline driven from GitLab CI
    iac: str
    k8s: str
    monitoring: str
    runbook: str
    security_review: str  # DevSecOps hardening/scan audit of the deployment artifacts

    # --- QA execution ---
    test_results: str
    tests_passed: bool

    # --- Operate / Monitor ---
    deploy_status: str
    incidents: str
    ops_report: str

    # --- Document & Handoff ---
    readme: str
    user_manual: str
    release_notes: str
    infrastructure_docs: str
    test_report: str

    # --- Control / bookkeeping ---
    current_phase: str
    review_iters: int
    fix_iters: int
    skills_log: Annotated[list[str], operator.add]
    messages: Annotated[list[BaseMessage], operator.add]


def new_state(spec_path: str, spec_text: str, output_dir: str) -> TeamState:
    """Build the initial state for a greenfield (``build``) run."""
    return {
        "spec_path": spec_path,
        "spec_text": spec_text,
        "output_dir": output_dir,
        "mode": BUILD_MODE,
        "needs_frontend": triage.needs_frontend(spec_text),
        "needs_backend": triage.needs_backend(spec_text),
        "needs_deployment": triage.needs_deployment(spec_text),
        "source_files": {},
        "review_iters": 0,
        "fix_iters": 0,
        "tests_passed": False,
        "skills_log": [],
        "messages": [],
        "current_phase": "plan",
    }


def new_feature_state(
    spec_path: str,
    spec_text: str,
    output_dir: str,
    *,
    source_files: dict[str, str],
    baseline: str,
) -> TeamState:
    """Build the initial state for an incremental (``feature``) run.

    Same shape as :func:`new_state`, but framed for extending software the team has
    already developed: the run is put in :data:`FEATURE_MODE`, the existing source files
    are pre-seeded so each phase modifies them in place (the ``source_files`` reducer
    merges later edits on top), and a rendered ``baseline`` digest of the existing
    project is carried so every node can ground its work in what already exists.

    Args:
        spec_path: Human-readable label for the new feature request (file path or
            ``<prompt>``).
        spec_text: The new feature description the team must integrate.
        output_dir: Workspace the updated project is written to.
        source_files: The existing project's code/config files (path -> content),
            pre-seeded so unchanged files are preserved and edits accumulate.
        baseline: A rendered digest of the existing software (file tree + key docs) for
            grounding every phase.

    Returns:
        The initial team state for a feature run.
    """
    state = new_state(spec_path, spec_text, output_dir)
    state["mode"] = FEATURE_MODE
    state["source_files"] = dict(source_files)
    state["baseline"] = baseline
    state["current_phase"] = "feature"
    return state
