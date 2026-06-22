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
# new project); ``feature`` is the brownfield/incremental mode (change software the team has
# already developed). See ``new_feature_state``.
BUILD_MODE = "build"
FEATURE_MODE = "feature"

# What an incremental (feature-mode) run does to the existing software. ``add`` integrates a
# new feature (the original incremental mode); ``modify`` changes how an existing feature
# behaves; ``remove`` takes an existing feature out. They share the whole brownfield engine
# and differ only in the instruction ``agents.base.feature_brief`` injects into every node.
OP_ADD = "add"
OP_MODIFY = "modify"
OP_REMOVE = "remove"
FEATURE_OPS = (OP_ADD, OP_MODIFY, OP_REMOVE)

# A maintenance operation (not one of the user-facing feature commands): the garbage-collection
# run fixes documentation inconsistencies, architecture violations, and technical debt found by
# the scanner, without changing intended behaviour. It reuses the brownfield engine (shows the
# existing software and re-emits only changed files), so it carries its own op marker too.
OP_GC = "gc"

# Header that marks the existing-software context block in a feature-mode prompt. It is a
# stable sentinel: ``project.ExistingProject.brief`` emits it (and ``feature_brief`` appends
# the baseline carrying it) and the dry-run stub keys off it to return the incremental
# variant of its canned output.
FEATURE_BRIEF_HEADER = "## Existing software you are extending (incremental feature mode)"

# A stable opening phrase per operation, emitted by ``agents.base.feature_brief`` so a node
# (and the dry-run stub) can tell add/modify/remove apart from the prompt alone.
FEATURE_OP_MARKERS: dict[str, str] = {
    OP_ADD: "Treat the request above as a NEW feature to integrate",
    OP_MODIFY: "Treat the request above as a CHANGE to an existing feature",
    OP_REMOVE: "Treat the request above as the REMOVAL of an existing feature",
    OP_GC: "Treat the request above as a GARBAGE-COLLECTION clean-up of existing software",
}

# Sentinel content a node can map a path to in its ``source_files`` delta to delete that file
# from the project (used by ``remove`` runs). The ``source_files`` reducer drops the key, so
# the file disappears from every later listing the same way it is deleted from disk. Chosen
# to never collide with real file content.
DELETE_FILE = "\x00__delete_file__\x00"


def _merge_dict(left: dict[str, str], right: dict[str, str]) -> dict[str, str]:
    """Reducer that merges file maps so multiple passes accumulate edits.

    A value of :data:`DELETE_FILE` in ``right`` removes that path from the merged map instead
    of setting it, so a ``remove`` run can drop a file from ``source_files`` (which several
    nodes list) in lockstep with deleting it from disk.
    """
    merged = dict(left or {})
    for path, content in (right or {}).items():
        if content == DELETE_FILE:
            merged.pop(path, None)
        else:
            merged[path] = content
    return merged


class TeamState(TypedDict, total=False):
    """The shared blackboard passed between every agent in the graph.

    Each phase reads what earlier roles produced and writes its own artifacts. All keys
    are optional (``total=False``) because each node contributes only its own slice.
    """

    # --- Input ---
    spec_path: str
    spec_text: str
    spec_images: list[str]  # sample images the spec referenced (paths/URLs), passed to UX
    output_dir: str
    dry_run: bool
    mode: str  # BUILD_MODE (greenfield) or FEATURE_MODE (change existing software)
    feature_op: str  # feature mode only: OP_ADD | OP_MODIFY | OP_REMOVE
    baseline: str  # feature mode only: rendered digest of the existing software

    # --- Capability flags (set by deterministic triage; gate which phases run) ---
    needs_frontend: bool  # build a UI? -> runs the UX designer + frontend engineer
    needs_backend: bool  # build server-side code? -> runs the software engineer (backend)
    needs_deployment: bool  # deploy it? -> runs containerisation, CI/CD, K8s, operate

    # --- Product Manager ---
    user_stories: str
    acceptance_criteria: str
    backlog: str
    features: list[str]  # ordered, independently buildable features (built one at a time)

    # --- Feature build loop (Code & Build) ---
    feature_cursor: int  # index into ``features`` of the feature currently being built
    feature_log: Annotated[list[str], operator.add]  # features built so far (UI / traceability)
    build_stage: str  # "backend" | "frontend" — what a "changes" verdict loops back to
    frontend_built: bool  # whether the frontend pass has run (so it is built/reviewed once)

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
    ci_workflow: str  # .github/workflows/ci.yml — GitHub Actions PR gate (lint, test, scans)
    cd_workflow: str  # .github/workflows/cd.yml — GitHub Actions build, deploy, rollback
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

    # --- Garbage collection (maintenance run) ---
    gc_findings: int  # number of issues the scan found (0 short-circuits the run)
    gc_report: str  # the rendered scan report submitted to the Tech Lead
    gc_request: str  # the Tech Lead's prioritised fix request (work order) for the engineer

    # --- Debugging (focused test -> diagnose -> fix run) ---
    bug_report: str  # optional reported symptom guiding the diagnosis (empty if none given)
    debug_report: str  # the engineer's debug write-up: symptom, root cause, fix, final status

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


def new_state(
    spec_path: str,
    spec_text: str,
    output_dir: str,
    *,
    images: tuple[str, ...] = (),
) -> TeamState:
    """Build the initial state for a greenfield (``build``) run.

    Args:
        spec_path: Human-readable label for the request (file path or ``<prompt>``).
        spec_text: The spec / use-case text the team builds from.
        output_dir: Workspace the generated project is written to.
        images: Sample images the spec referenced (resolved paths / URLs), carried so the
            Product Manager can hand them to the UI/UX Designer.

    Returns:
        The initial team state.
    """
    return {
        "spec_path": spec_path,
        "spec_text": spec_text,
        "spec_images": list(images),
        "output_dir": output_dir,
        "mode": BUILD_MODE,
        "needs_frontend": triage.needs_frontend(spec_text),
        "needs_backend": triage.needs_backend(spec_text),
        "needs_deployment": triage.needs_deployment(spec_text),
        "source_files": {},
        "features": [],
        "feature_cursor": 0,
        "feature_log": [],
        "build_stage": "backend",
        "frontend_built": False,
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
    op: str = OP_ADD,
    images: tuple[str, ...] = (),
) -> TeamState:
    """Build the initial state for an incremental (``feature``) run.

    Same shape as :func:`new_state`, but framed for changing software the team has
    already developed: the run is put in :data:`FEATURE_MODE`, the existing source files
    are pre-seeded so each phase modifies them in place (the ``source_files`` reducer
    merges later edits on top and honours :data:`DELETE_FILE` deletions), and a rendered
    ``baseline`` digest of the existing project is carried so every node can ground its
    work in what already exists. ``op`` selects what the run does to that software.

    Args:
        spec_path: Human-readable label for the change request (file path or ``<prompt>``).
        spec_text: The change the team must make (the feature to add, modify, or remove).
        output_dir: Workspace the updated project is written to.
        source_files: The existing project's code/config files (path -> content),
            pre-seeded so unchanged files are preserved and edits accumulate.
        baseline: A rendered digest of the existing software (file tree + key docs) for
            grounding every phase.
        op: The operation to perform: :data:`OP_ADD` (default), :data:`OP_MODIFY`, or
            :data:`OP_REMOVE`.
        images: Sample images the change request referenced, passed to the UI/UX Designer.

    Returns:
        The initial team state for a feature run.
    """
    state = new_state(spec_path, spec_text, output_dir, images=images)
    state["mode"] = FEATURE_MODE
    state["feature_op"] = op if op in FEATURE_OPS else OP_ADD
    state["source_files"] = dict(source_files)
    state["baseline"] = baseline
    state["current_phase"] = "feature"
    return state


def new_gc_state(
    spec_path: str,
    output_dir: str,
    *,
    source_files: dict[str, str],
    baseline: str,
) -> TeamState:
    """Build the initial state for a garbage-collection (maintenance) run.

    Like :func:`new_feature_state` but framed as a clean-up rather than a feature: the run is
    put in :data:`FEATURE_MODE` with :data:`OP_GC`, the existing source is pre-seeded so fixes
    accumulate on top of the real project, and the acceptance criteria pin the contract for a
    clean-up — behaviour unchanged, tests green, reported issues resolved — so the Tech Lead's
    verify gate (tests + lint) can judge it. The scanner fills in ``gc_findings`` / ``gc_report``.

    Args:
        spec_path: Human-readable label for the run (the workspace path).
        output_dir: Workspace of the project to clean up.
        source_files: The existing project's editable files (path -> content).
        baseline: A rendered digest of the existing software, for grounding the fix.

    Returns:
        The initial team state for a garbage-collection run.
    """
    state = new_state(spec_path, "", output_dir)
    state["mode"] = FEATURE_MODE
    state["feature_op"] = OP_GC
    state["source_files"] = dict(source_files)
    state["baseline"] = baseline
    state["acceptance_criteria"] = (
        "The garbage-collection fixes must not change existing behaviour: all tests must "
        "still pass, and the issues the scan reported should be resolved."
    )
    state["current_phase"] = "gc"
    return state


def new_debug_state(
    spec_path: str,
    output_dir: str,
    *,
    source_files: dict[str, str],
    baseline: str,
    bug_report: str = "",
) -> TeamState:
    """Build the initial state for a focused debugging run on already-developed software.

    Unlike the build pipeline's bug-fix loop (which only fires when QA's freshly written
    tests go red), this drives a direct ``test -> diagnose -> fix`` loop over an existing
    workspace: the existing source is pre-seeded so fixes accumulate on top of the real
    project, and an optional reported ``bug_report`` symptom guides the diagnosis even when
    the suite is green. It re-uses the brownfield framing (existing software, re-emit only
    changed files) without re-running planning, architecture, or deployment.

    Args:
        spec_path: Human-readable label for the run (the workspace path).
        output_dir: Workspace of the project to debug.
        source_files: The existing project's editable files (path -> content).
        baseline: A rendered digest of the existing software, for grounding the fix.
        bug_report: An optional reported symptom to diagnose; empty to just fix red tests.

    Returns:
        The initial team state for a debugging run.
    """
    state = new_state(spec_path, bug_report, output_dir)
    state["mode"] = FEATURE_MODE
    state["feature_op"] = OP_ADD
    state["source_files"] = dict(source_files)
    state["baseline"] = baseline
    state["bug_report"] = bug_report
    state["current_phase"] = "debug"
    return state
