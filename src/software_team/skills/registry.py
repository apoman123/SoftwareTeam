"""Skill registry — the explicit map of which skills belong to which role.

This is the heart of the "assign specific skills to specific characters" design. Each
`Skill` has a name, a human description, and an optional bound LangChain tool (for the
skills that actually execute side effects). Roles list the skills they are allowed to
use; agents surface their skill list in prompts and logs, and the SWE/QA agents can
bind their tool-backed skills to a ReAct loop on tool-capable models.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import filesystem, shell


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    tool: object | None = None  # a LangChain @tool, when the skill executes I/O


# --- Tool-backed skills (real side effects) ---
WRITE_SOURCE = Skill("write_source_file", "Write a code file into the project workspace", filesystem.write_source_file)
READ_SOURCE = Skill("read_source_file", "Read a code file from the project workspace", filesystem.read_source_file)
LIST_FILES = Skill("list_project_files", "List all files in the project workspace", filesystem.list_project_files)
RUN_SHELL = Skill("run_shell", "Run a shell command inside the workspace", shell.run_shell)
RUN_TESTS = Skill("run_tests", "Run the project's pytest suite", shell.run_tests)


def _doc(name: str, desc: str) -> Skill:
    """A prompt-guided skill (no side effect tool); the LLM performs it in-context."""
    return Skill(name, desc, None)


ROLE_SKILLS: dict[str, list[Skill]] = {
    "product_manager": [
        _doc("parse_spec", "Read the input spec and extract goals, actors and use-cases"),
        _doc("generate_user_stories", "Write 'As a [role], I want [goal], so that [value]' stories"),
        _doc("write_acceptance_criteria", "Write Gherkin Given/When/Then acceptance criteria"),
        _doc("prioritize_backlog", "Order the backlog with MoSCoW (Must/Should/Could/Won't)"),
    ],
    "ux_designer": [
        _doc("design_user_flow", "Map the user's step-by-step flow through the product"),
        _doc("generate_wireframe", "Produce ASCII/markdown wireframes of key screens"),
        _doc("component_spec", "Specify UI components, states and interactions"),
    ],
    "tech_lead": [
        _doc("select_tech_stack", "Choose language, framework, datastore and rationale"),
        _doc("design_architecture", "Design components and data flow (mermaid diagram)"),
        _doc("define_api_spec", "Define the HTTP API as an OpenAPI YAML contract"),
        _doc("design_db_schema", "Design the persistence schema (SQL/DDL)"),
        _doc("code_review", "Review the engineer's code; approve or request changes"),
        _doc("route_workflow", "Supervise: decide whether to loop back or advance phases"),
    ],
    "software_engineer": [
        _doc("scaffold_project", "Lay out the project package and module structure"),
        WRITE_SOURCE,
        _doc("write_unit_tests", "Write unit tests for the business logic"),
        READ_SOURCE,
        RUN_TESTS,
        RUN_SHELL,
        _doc("fix_bug", "Diagnose failing tests and patch the code"),
    ],
    "qa_engineer": [
        _doc("generate_test_cases", "Derive test cases from acceptance criteria"),
        _doc("write_e2e_tests", "Write end-to-end / API tests"),
        _doc("edge_case_analysis", "Enumerate edge cases and failure modes"),
        _doc("performance_test_stub", "Sketch a load/performance test scenario"),
        RUN_TESTS,
        LIST_FILES,
    ],
    "devops_sre": [
        _doc("write_dockerfile", "Containerise the service with a Dockerfile"),
        _doc("generate_ci_pipeline", "Author the CI pipeline (GitHub Actions)"),
        _doc("generate_cd_pipeline", "Author the CD pipeline + a safe rollout strategy"),
        _doc("write_terraform", "Describe infrastructure as code (Terraform)"),
        _doc("write_k8s_manifests", "Write Kubernetes deployment/service manifests"),
        _doc("write_monitoring_config", "Configure Prometheus/Grafana metrics and alerts"),
        _doc("write_runbook", "Write an on-call runbook and DR procedure"),
        WRITE_SOURCE,
    ],
}


def skills_for(role: str) -> list[Skill]:
    return ROLE_SKILLS.get(role, [])


def skill_names(role: str) -> list[str]:
    return [s.name for s in skills_for(role)]


def tools_for(role: str) -> list[object]:
    """The executable (tool-backed) skills for a role, for ReAct binding."""
    return [s.tool for s in skills_for(role) if s.tool is not None]


def skills_catalog() -> str:
    """A human-readable catalogue of every role's skills (used in the README/CLI)."""
    lines: list[str] = []
    for role, skills in ROLE_SKILLS.items():
        lines.append(f"### {role}")
        for s in skills:
            kind = "tool" if s.tool is not None else "reasoning"
            lines.append(f"- `{s.name}` ({kind}): {s.description}")
        lines.append("")
    return "\n".join(lines)
