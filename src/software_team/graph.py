"""LangGraph orchestration of the SDLC.

A StateGraph routes the shared TeamState through four phases — Plan & Design, Code &
Build, Deploy & Release, Operate & Monitor — with the Tech Lead acting as supervisor.
Three feedback loops bounce work back to the engineer — code-review changes, the
one-feature-at-a-time build loop, and failing tests — each bounded by an iteration cap so
the graph always terminates.

The Code & Build phase builds **one feature at a time**: the Product Manager decomposes the
spec into an ordered ``features`` plan, and the Software Engineer builds each feature in turn.
The Tech Lead then *verifies* it as the quality gate — running the project's test suite (a
failing suite forces changes) and checking the feature against its acceptance criteria — and
the loop only advances to the next feature once the current one is approved.

Routing is also capability-aware. Deterministic triage sets ``needs_frontend`` and
``needs_deployment`` on the state (see ``triage``), and the supervisor skips the phases a
project does not need: no UX/frontend for a pure API or library, and no
containerisation/CI-CD/operate/infra-docs for a library, CLI or script.

    START → PM ─needs_frontend?─→ UX → TechLead(design) → QA(plan) → SWE(feature i)
               └─no UI──────────────┘                                     │
                       ┌──── changes (cap) ────────────────────────→ TechLead(review:
                       │                                              run tests + spec)
                     SWE(feature i) ←── approve & more features ──────────┤
                                          approve & UI not built ─→ Frontend ─┐
                                          approve & done ─needs_deployment?─→ │
                                                  │                  DevOps(CI)│
                                       ┌──────────┘  └─no deploy─→ QA(tests) ←─┘
                                       ▼     (Frontend is reviewed the same way)
                          ┌──── fail (cap) ───── QA(run tests)
                          ▼     pass ─needs_deployment?─→ DevOps(CD) → Operate
                    SWE(fix)         └─no deploy───────────────┐         │
                                                               ▼         ▼
            END ← PM(user manual) ← [DevOps(infra docs)?] ← QA(test report) ← SWE(README)

The final Document & Handoff phase has each role write the documentation it knows best:
the engineer the README (how to run it), QA the test report, DevOps the infrastructure
docs (only when the project deploys), and the PM the user manual + release notes (what it
does, for end users).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .agents.devops_sre import (
    devops_cd_node,
    devops_ci_node,
    devops_docs_node,
    operate_node,
)
from .agents.frontend_engineer import frontend_engineer_node
from .agents.garbage_collector import (
    GC_REVIEW_ROUTES,
    GC_SCAN_ROUTES,
    gc_fix_node,
    gc_scan_node,
    route_after_gc_review,
    route_after_gc_scan,
    tech_lead_gc_request_node,
)
from .agents.product_manager import product_manager_docs_node, product_manager_node
from .agents.qa_engineer import qa_planning_node, qa_report_node, qa_test_node
from .agents.software_engineer import (
    software_engineer_fix_node,
    software_engineer_node,
    software_engineer_readme_node,
)
from .agents.tech_lead import (
    route_after_planning,
    route_after_product_manager,
    route_after_qa_report,
    route_after_review,
    route_after_tests,
    tech_lead_design_node,
    tech_lead_review_node,
)
from .agents.ux_designer import ux_designer_node
from .state import TeamState


def build_graph() -> CompiledStateGraph:
    """Wire the SDLC phases and feedback loops into a compiled LangGraph state graph."""
    builder = StateGraph(TeamState)

    # Plan & Design
    builder.add_node("product_manager", product_manager_node)
    builder.add_node("ux_designer", ux_designer_node)
    builder.add_node("tech_lead_design", tech_lead_design_node)
    builder.add_node("qa_planning", qa_planning_node)
    # Code & Build
    builder.add_node("software_engineer", software_engineer_node)
    builder.add_node("frontend_engineer", frontend_engineer_node)
    builder.add_node("tech_lead_review", tech_lead_review_node)
    builder.add_node("devops_ci", devops_ci_node)
    # Deploy & Release
    builder.add_node("qa_test", qa_test_node)
    builder.add_node("software_engineer_fix", software_engineer_fix_node)
    builder.add_node("devops_cd", devops_cd_node)
    # Operate & Monitor
    builder.add_node("operate", operate_node)
    # Document & Handoff
    builder.add_node("software_engineer_readme", software_engineer_readme_node)
    builder.add_node("qa_report", qa_report_node)
    builder.add_node("devops_docs", devops_docs_node)
    builder.add_node("product_manager_docs", product_manager_docs_node)

    builder.add_edge(START, "product_manager")
    # Design the UX only when the product has a UI (needs_frontend), else skip to design.
    builder.add_conditional_edges(
        "product_manager",
        route_after_product_manager,
        {"ux_designer": "ux_designer", "tech_lead_design": "tech_lead_design"},
    )
    builder.add_edge("ux_designer", "tech_lead_design")
    builder.add_edge("tech_lead_design", "qa_planning")
    # Build the backend when needed; a frontend-only product skips straight to the frontend.
    builder.add_conditional_edges(
        "qa_planning",
        route_after_planning,
        {
            "software_engineer": "software_engineer",
            "frontend_engineer": "frontend_engineer",
            "tech_lead_review": "tech_lead_review",
        },
    )
    # Every feature is reviewed right after it is built; the frontend is reviewed too.
    builder.add_edge("software_engineer", "tech_lead_review")
    builder.add_edge("frontend_engineer", "tech_lead_review")

    # The feature loop: changes -> back to the engineer (same feature); approve -> next
    # backend feature, then the frontend, then CI (or straight to the test gate when not
    # deploying). See ``route_after_review``.
    builder.add_conditional_edges(
        "tech_lead_review",
        route_after_review,
        {
            "software_engineer": "software_engineer",
            "frontend_engineer": "frontend_engineer",
            "devops_ci": "devops_ci",
            "qa_test": "qa_test",
        },
    )
    builder.add_edge("devops_ci", "qa_test")
    # Pass -> CD when deploying, else skip the whole deploy/operate phase to documentation.
    builder.add_conditional_edges(
        "qa_test",
        route_after_tests,
        {
            "software_engineer_fix": "software_engineer_fix",
            "devops_cd": "devops_cd",
            "software_engineer_readme": "software_engineer_readme",
        },
    )
    builder.add_edge("software_engineer_fix", "qa_test")
    builder.add_edge("devops_cd", "operate")

    # Document & Handoff: each role documents the part it knows best.
    builder.add_edge("operate", "software_engineer_readme")
    builder.add_edge("software_engineer_readme", "qa_report")
    # Infrastructure docs only when the project deploys; otherwise jump to the user manual.
    builder.add_conditional_edges(
        "qa_report",
        route_after_qa_report,
        {"devops_docs": "devops_docs", "product_manager_docs": "product_manager_docs"},
    )
    builder.add_edge("devops_docs", "product_manager_docs")
    builder.add_edge("product_manager_docs", END)

    return builder.compile()


def build_gc_graph() -> CompiledStateGraph:
    """Wire the on-demand garbage-collection flow (scan → Tech Lead → fix → verify).

    A small maintenance graph, separate from the build pipeline: a deterministic scan submits
    its findings to the Tech Lead, who triages them into a fix request; the engineer applies
    the fixes; and the existing Tech Lead review (tests + lint) verifies the result, looping
    within the bug-fix cap. A clean project short-circuits straight to the end.

        START → gc_scan ─findings?─→ TechLead(request) → gc_fix → TechLead(review: tests+lint)
                   └─clean─→ END           ┌──── changes (cap) ──────────┘
                                           ▼ else
                                          END
    """
    builder = StateGraph(TeamState)
    builder.add_node("gc_scan", gc_scan_node)
    builder.add_node("tech_lead_gc_request", tech_lead_gc_request_node)
    builder.add_node("gc_fix", gc_fix_node)
    builder.add_node("tech_lead_review", tech_lead_review_node)

    builder.add_edge(START, "gc_scan")
    builder.add_conditional_edges("gc_scan", route_after_gc_scan, GC_SCAN_ROUTES)
    builder.add_edge("tech_lead_gc_request", "gc_fix")
    builder.add_edge("gc_fix", "tech_lead_review")
    builder.add_conditional_edges("tech_lead_review", route_after_gc_review, GC_REVIEW_ROUTES)

    return builder.compile()
