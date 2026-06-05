"""Shared team state — the "blackboard" passed between every agent in the graph.

Each phase reads what earlier roles produced and writes its own artifacts. Most fields
are plain strings (markdown / yaml / code) so they can be persisted to disk verbatim.
`source_files` is a path -> content map for the generated application.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


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

    # --- Product Manager ---
    user_stories: str
    acceptance_criteria: str
    backlog: str

    # --- UI/UX Designer ---
    ux_design: str

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
    """Build the initial state for a run."""
    return {
        "spec_path": spec_path,
        "spec_text": spec_text,
        "output_dir": output_dir,
        "source_files": {},
        "review_iters": 0,
        "fix_iters": 0,
        "tests_passed": False,
        "skills_log": [],
        "messages": [],
        "current_phase": "plan",
    }
