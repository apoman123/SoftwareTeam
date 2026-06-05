"""LangGraph orchestration of the SDLC.

A StateGraph routes the shared TeamState through four phases — Plan & Design, Code &
Build, Deploy & Release, Operate & Monitor — with the Tech Lead acting as supervisor.
Two feedback loops (code-review changes, failing tests) bounce work back to the
engineer, each bounded by an iteration cap so the graph always terminates.

    START → PM → UX → TechLead(design) → QA(plan) → SWE → TechLead(review)
                                                            │
                          ┌──────── changes (cap) ─────────┘
                          ▼                       approve
                        SWE                          │
                                                     ▼
                                                  DevOps(CI) → QA(run tests)
                                                                   │
                              ┌──────── fail (cap) ────────────────┤
                              ▼                          pass       │
                        SWE(fix) → QA(run tests)                    ▼
                                                            DevOps(CD) → Operate → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .agents.devops_sre import devops_cd_node, devops_ci_node, operate_node
from .agents.product_manager import product_manager_node
from .agents.qa_engineer import qa_planning_node, qa_test_node
from .agents.software_engineer import software_engineer_fix_node, software_engineer_node
from .agents.tech_lead import (
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
    builder.add_node("tech_lead_review", tech_lead_review_node)
    builder.add_node("devops_ci", devops_ci_node)
    # Deploy & Release
    builder.add_node("qa_test", qa_test_node)
    builder.add_node("software_engineer_fix", software_engineer_fix_node)
    builder.add_node("devops_cd", devops_cd_node)
    # Operate & Monitor
    builder.add_node("operate", operate_node)

    builder.add_edge(START, "product_manager")
    builder.add_edge("product_manager", "ux_designer")
    builder.add_edge("ux_designer", "tech_lead_design")
    builder.add_edge("tech_lead_design", "qa_planning")
    builder.add_edge("qa_planning", "software_engineer")
    builder.add_edge("software_engineer", "tech_lead_review")

    builder.add_conditional_edges(
        "tech_lead_review",
        route_after_review,
        {"software_engineer": "software_engineer", "devops_ci": "devops_ci"},
    )
    builder.add_edge("devops_ci", "qa_test")
    builder.add_conditional_edges(
        "qa_test",
        route_after_tests,
        {"software_engineer_fix": "software_engineer_fix", "devops_cd": "devops_cd"},
    )
    builder.add_edge("software_engineer_fix", "qa_test")
    builder.add_edge("devops_cd", "operate")
    builder.add_edge("operate", END)

    return builder.compile()
