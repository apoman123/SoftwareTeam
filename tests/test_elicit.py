"""Tests for interactive spec generation (the ``spec`` command and the elicit module)."""

import asyncio

from typer.testing import CliRunner

from software_team import elicit
from software_team.agents import base
from software_team.main import app
from software_team.skills.registry import skill_guidance, skill_names, skills_for


def test_pm_library_includes_the_elicit_skill():
    # The searched-for skill was added to the Product Manager's skill directory.
    assert "elicit-requirements" in skill_names("product_manager")
    guidance = skill_guidance("product_manager", "elicit-requirements")
    assert guidance.strip()
    assert "Discover" in guidance  # the elicitation pipeline's first phase


def test_parse_questions_keeps_only_questions_and_caps():
    text = '1. Who uses it?\n- What scale?\nnot a question line\n"Why now?"\nExtra one?'
    assert elicit._parse_questions(text, limit=3) == ["Who uses it?", "What scale?", "Why now?"]


def test_ask_questions_non_interactive_records_unanswered():
    pairs = elicit.ask_questions(["Q1?", "Q2?"], interactive=False, console=None)
    assert pairs == [("Q1?", elicit._UNANSWERED), ("Q2?", elicit._UNANSWERED)]


def test_author_spec_loads_elicit_skill_before_generating(monkeypatch):
    # The core requirement: the elicit-requirements skill is composed into the system prompt
    # used to write the spec — i.e. the agent loads it *before* generating the spec file.
    captured = {}

    async def fake_generate(role, system, user, state, research_queries=None):
        captured["role"] = role
        captured["system"] = system
        captured["user"] = user
        return "# Spec: X\n\n## Technology\nGo.\n"

    monkeypatch.setattr(base, "generate", fake_generate)

    qa = [("Which technology should it use?", "Go with Postgres")]
    spec = asyncio.run(elicit.author_spec("Build a thing", qa, {"dry_run": False}))

    assert captured["role"] == "spec_author"
    assert "Apply these skills and the method behind them:" in captured["system"]
    assert "Discover" in captured["system"]  # the elicit skill body is present
    assert "Research the market" in captured["system"]  # the web-research skill body too
    assert "Go with Postgres" in captured["user"]  # the interview answers reached the model
    assert spec.startswith("# Spec:")


def test_generate_spec_file_dry_run_writes_a_spec(tmp_path):
    out = tmp_path / "nested" / "myspec.md"
    path, spec = asyncio.run(
        elicit.generate_spec_file(
            "Build a URL shortener", out, interactive=False, dry_run=True, console=None
        )
    )
    assert path == out
    assert out.exists()
    text = out.read_text()
    assert text == spec if spec.endswith("\n") else text == spec + "\n"
    # The offline spec has the sections the pipeline consumes.
    for heading in ("## Use cases", "## Technology", "## Out of scope"):
        assert heading in text


def test_spec_command_dry_run_writes_file(tmp_path):
    out = tmp_path / "spec.md"
    result = CliRunner().invoke(
        app,
        ["spec", "--prompt", "Build a recipe sharing app", "--out", str(out), "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "## Use cases" in out.read_text()
    assert "software-team run --spec" in result.output  # points the user at the next step


def test_spec_command_rejects_empty_prompt():
    result = CliRunner().invoke(app, ["spec", "--prompt", "   ", "--dry-run"])
    assert result.exit_code != 0


def test_spec_command_rejects_prompt_and_spec_together(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("# Draft\n")
    result = CliRunner().invoke(app, ["spec", "--spec", str(draft), "--prompt", "x", "--dry-run"])
    assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# revise mode: improve an existing spec file
# --------------------------------------------------------------------------- #


def test_revise_spec_loads_elicit_skill_and_passes_existing_spec(monkeypatch):
    captured = {}

    async def fake_generate(role, system, user, state, research_queries=None):
        captured["system"] = system
        captured["user"] = user
        return "# Spec: Improved\n\n## Technology\nPython.\n"

    monkeypatch.setattr(base, "generate", fake_generate)

    draft = "# My Draft\n\n## Use cases\n- do stuff (vague)\n"
    out = asyncio.run(elicit.revise_spec(draft, [("Which tech?", "Python")], {"dry_run": False}))

    assert "improving an existing spec" in captured["system"].lower()
    assert "Apply these skills and the method behind them:" in captured["system"]
    assert "Discover" in captured["system"]  # the elicit skill body
    assert "# My Draft" in captured["user"]  # the existing spec reaches the model
    assert out.startswith("# Spec:")


def test_spec_command_revises_input_file_and_leaves_it_untouched(tmp_path):
    draft = tmp_path / "draft.md"
    original = "# Rough draft\n\nMake an app, somehow.\n"
    draft.write_text(original)
    out = tmp_path / "better.md"

    result = CliRunner().invoke(app, ["spec", "--spec", str(draft), "--out", str(out), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "## Use cases" in out.read_text()
    # The input spec is left untouched.
    assert draft.read_text() == original


# --------------------------------------------------------------------------- #
# the conversation: bounded, adaptive follow-ups
# --------------------------------------------------------------------------- #


def test_converse_is_multi_round_adaptive_and_bounded(monkeypatch):
    monkeypatch.setattr(elicit.SETTINGS, "max_interview_rounds", 3)
    calls = {"followup": 0}

    async def fake_generate(role, system, user, state, research_queries=None):
        system_l = system.lower()
        if "preparing to write a spec" in system_l:
            return "What scale?\nWhich datastore?"
        if "mid-interview" in system_l:
            calls["followup"] += 1
            return "One more — is auth needed?"  # always wants more; must be bounded by rounds
        return "spec"

    monkeypatch.setattr(base, "generate", fake_generate)
    answers = iter(f"answer {i}" for i in range(50))
    monkeypatch.setattr(elicit.Prompt, "ask", lambda *a, **k: next(answers))

    qa = asyncio.run(
        elicit.converse(
            "Build X",
            mode=elicit.GENERATE,
            state={"dry_run": False},
            interactive=True,
            console=None,
        )
    )

    # max_interview_rounds=3 => one seed round + at most two follow-up rounds.
    assert calls["followup"] <= 2
    # The mandatory needs/technology backbone plus the seeded questions were all asked.
    assert len(qa) >= len(elicit.MANDATORY_QUESTIONS) + 1


def test_converse_non_interactive_revise_asks_nothing():
    qa = asyncio.run(
        elicit.converse(
            "# spec", mode=elicit.REVISE, state={"dry_run": False}, interactive=False, console=None
        )
    )
    assert qa == []


def test_converse_non_interactive_generate_records_backbone():
    qa = asyncio.run(
        elicit.converse(
            "Build X",
            mode=elicit.GENERATE,
            state={"dry_run": False},
            interactive=False,
            console=None,
        )
    )
    assert len(qa) == len(elicit.MANDATORY_QUESTIONS)
    assert all(answer == elicit._UNANSWERED for _, answer in qa)


# --------------------------------------------------------------------------- #
# web research: the spec agent searches the internet before writing
# --------------------------------------------------------------------------- #


def test_pm_library_includes_the_research_skill():
    # The web-search skill is in the Product Manager's library and binds the web_search tool.
    assert "research-the-market" in skill_names("product_manager")
    skill = next(s for s in skills_for("product_manager") if s.name == "research-the-market")
    assert skill.tool is not None  # tool-backed: bound to the web_search LangChain tool
    assert skill.kind == "tool"


def test_research_queries_ground_on_a_named_stack():
    # The stakeholder named the stack only in an interview answer; it still drives the search.
    qa = [("Which technology should it use?", "Node.js with Postgres")]
    queries = elicit._research_queries("Build a chat app", qa)

    assert queries  # the agent has something to search for
    assert len(queries) <= 2  # bounded to protect prefill on a local model
    assert any("node.js" in q.lower() for q in queries)  # grounds on the requested stack
    assert any("chat app" in q.lower() for q in queries)  # and on the product topic


def test_research_queries_recommend_a_stack_when_none_is_named():
    # No technology stated anywhere -> research current recommended options for this product.
    qa = [("Which technology should it use?", elicit._UNANSWERED)]
    queries = elicit._research_queries("Build a recipe sharing app", qa)

    assert any("recommended technology stack" in q.lower() for q in queries)


def test_author_spec_searches_the_web_before_writing(monkeypatch):
    # The core requirement: writing the spec issues web-search queries to ground it.
    captured = {}

    async def fake_generate(role, system, user, state, research_queries=None):
        captured["research_queries"] = research_queries
        return "# Spec: X\n\n## Technology\nNode.js.\n"

    monkeypatch.setattr(base, "generate", fake_generate)

    qa = [("Which technology should it use?", "Node.js")]
    asyncio.run(elicit.author_spec("Build a URL shortener", qa, {"dry_run": False}))

    assert captured["research_queries"]  # the spec author asked the web, not just the model
    assert any("node.js" in q.lower() for q in captured["research_queries"])
