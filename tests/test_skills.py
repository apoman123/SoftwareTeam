"""Tests for the filesystem + authoring skills."""

import pytest

from software_team.skills.common import filesystem
from software_team.skills.common.authoring import (
    extract_fenced,
    file_blocks,
    parse_file_blocks,
    split_at_heading,
)


def test_file_block_roundtrip():
    files = {"app/main.py": "print('hi')", "tests/test_x.py": "def test():\n    assert True"}
    parsed = parse_file_blocks(file_blocks(files))
    assert parsed == files


def test_extract_fenced_by_language():
    text = "intro\n```yaml\nkey: value\n```\nmid\n```sql\nSELECT 1;\n```\n"
    assert extract_fenced(text, "yaml") == "key: value"
    assert extract_fenced(text, "sql") == "SELECT 1;"


def test_split_at_heading_keeps_subheadings_in_trailing_section():
    text = "# Manual\n\nUse it like so.\n\n## Release Notes\n\n### Added\n- a feature\n"
    manual, notes = split_at_heading(text, "Release Notes")
    assert manual == "# Manual\n\nUse it like so."
    # The trailing section keeps its own sub-headings (unlike extract_section).
    assert notes.startswith("## Release Notes")
    assert "### Added" in notes


def test_split_at_heading_without_heading_returns_whole_text():
    manual, notes = split_at_heading("# Manual\n\nNo notes here.", "Release Notes")
    assert manual == "# Manual\n\nNo notes here."
    assert notes == ""


def test_write_files_creates_tree(tmp_path):
    written = filesystem.write_files(str(tmp_path), {"a/b.py": "x = 1"})
    assert (tmp_path / "a" / "b.py").read_text().strip() == "x = 1"
    assert written and written[0].endswith("b.py")
    assert filesystem.list_tree(str(tmp_path)) == ["a/b.py"]


def test_write_refuses_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        filesystem.write_file(str(tmp_path), "../escape.py", "nope")


def test_every_character_loads_its_skill_md_library():
    from software_team.skills.registry import ROLE_SKILLS, guidance_for, tools_for

    expected = {
        "product_manager",
        "ux_designer",
        "tech_lead",
        "software_engineer",
        "qa_engineer",
        "devops_sre",
    }
    assert set(ROLE_SKILLS) == expected
    for role, skills in ROLE_SKILLS.items():
        assert skills, f"{role} has no skills"
        for s in skills:
            # Every SKILL.md provides the required frontmatter + an instructions body.
            assert s.name and s.description, f"{role}/{s.path} missing name or description"
            assert s.body.strip(), f"{role}/{s.name} has an empty body"
            assert s.path and s.path.endswith("SKILL.md")
        assert guidance_for(role).strip()

    # The hands-on roles expose executable, tool-backed skills (bound via frontmatter).
    for role in ("software_engineer", "qa_engineer", "devops_sre"):
        assert tools_for(role), f"{role} should have tool-backed skills"


def test_code_authors_load_foundation_skills_first():
    from software_team.skills.loader import CODE_AUTHORS, FOUNDATION_SKILLS, load_character_skills

    # The two foundation skills lead the list, Karpathy before the Google style guide.
    assert FOUNDATION_SKILLS == ("karpathy-guidelines", "follow-google-style")
    for role in CODE_AUTHORS:
        names = [s.name for s in load_character_skills(role)]
        assert names[:2] == list(FOUNDATION_SKILLS), f"{role} should load foundation skills first"

    # Non-code-authoring characters do not get the foundation skills.
    for role in ("product_manager", "ux_designer", "tech_lead"):
        names = {s.name for s in load_character_skills(role)}
        assert names.isdisjoint(FOUNDATION_SKILLS), f"{role} should not load foundation skills"


def test_skill_md_frontmatter_and_tool_binding():
    from software_team.skills.loader import load_character_skills

    swe = {s.name: s for s in load_character_skills("software_engineer")}
    # Verb-based names per the Agent Skills convention.
    assert "write-code" in swe and "run-tests" in swe
    # `tool:` frontmatter binds a real LangChain tool; reasoning skills bind none.
    assert swe["write-code"].tool is not None
    assert swe["write-code"].kind == "tool"
    assert swe["scaffold-project"].tool is None
