"""Tests for the UI/UX design-system engine and its tool wrappers."""

from software_team.skills.common import design_system as ds


def test_bm25_ranks_relevant_documents_first():
    bm25 = ds.BM25()
    bm25.fit(["fast fintech banking dashboard", "playful childrens game", "spa wellness booking"])
    ranked = bm25.score("fintech banking")
    assert ranked[0][1] > 0
    assert ranked[0][0] == 0  # the fintech document outranks the rest


def test_search_returns_results_for_a_known_domain():
    result = ds.search("accessibility keyboard contrast", "ux", 2)
    assert result["domain"] == "ux"
    assert result["file"] == "ux-guidelines.csv"
    assert 1 <= result["count"] <= 2
    assert all("Issue" in row for row in result["results"])


def test_detect_domain_infers_from_keywords():
    assert ds.detect_domain("which colour palette and accent hex") == "color"
    assert ds.detect_domain("recommend a line chart for the trend") == "chart"
    assert ds.detect_domain("something with no hints") == "style"  # default


def test_generate_design_system_has_every_section():
    md = ds.generate_design_system("beauty spa wellness booking", "Serenity")
    for heading in (
        "# Design System — Serenity",
        "## Page Pattern",
        "## Visual Style",
        "## Colour Tokens",
        "## Typography",
        "## Pre-Delivery Checklist",
    ):
        assert heading in md, f"missing section: {heading}"
    # Recommends semantic colour tokens, not raw hex in components.
    assert "--color-primary" in md
    assert "#" in md  # at least one palette hex value rendered


def test_generate_design_system_is_deterministic():
    query = "fintech banking trust secure"
    assert ds.generate_design_system(query, "Bank") == ds.generate_design_system(query, "Bank")


def test_design_system_tool_wrapper():
    out = ds.design_system.invoke({"query": "saas dashboard analytics", "project_name": "Acme"})
    assert "# Design System — Acme" in out
    assert "## Colour Tokens" in out


def test_ui_ux_search_tool_wrapper():
    out = ds.ui_ux_search.invoke({"query": "minimalism dark mode", "domain": "style"})
    assert "domain: style" in out
    assert "Result 1" in out


def test_design_system_skill_is_tool_backed_for_ux_designer():
    from software_team.skills.loader import load_character_skills

    ux = {skill.name: skill for skill in load_character_skills("ux_designer")}
    assert "generate-design-system" in ux
    assert ux["generate-design-system"].tool is not None
    assert ux["generate-design-system"].kind == "tool"
    # The quality checklist is a reasoning skill (no bound tool).
    assert "apply-ui-quality-checklist" in ux
    assert ux["apply-ui-quality-checklist"].tool is None
