# Software Team — a multi-agent SDLC crew (LangChain + LangGraph)

A **cross-functional, "you build it, you run it" software team** implemented as a
multi-agent system. You hand it a **spec file** describing your use-cases; six AI
characters carry the feature through the **whole software lifecycle** — Plan & Design →
Code & Build → Deploy & Release → Operate & Monitor — and write a **runnable project
plus all CI/CD and DevOps artifacts** to a workspace directory.

You pick the LLM backend — a local **Ollama** server, the **OpenAI** API (or any
OpenAI-compatible endpoint), **Google Gemini** (google-genai), or a local GGUF model via
**llama.cpp** — with a single env var. Every character can also **search the internet**
for the latest information it needs (current library APIs, today's stable versions, fresh
best practices) and fold it into its work. It ships with a **`--dry-run`** mode that
produces a complete, test-passing example with no model server, provider package, or
network at all.

## The characters and their skills

Each role is a graph node with an explicit, curated skill set (defined in
`src/software_team/skills/registry.py`). Run `software-team skills` to print the full
catalogue.

| Character | Phase focus | Key skills |
|-----------|-------------|------------|
| 🧭 **Product Manager** | Plan | `parse_spec`, `generate_user_stories`, `write_acceptance_criteria` (Gherkin), `prioritize_backlog` (MoSCoW) |
| 🎨 **UI/UX Designer** | Plan | `design_user_flow`, `generate_wireframe`, `component_spec` |
| 🧠 **Tech Lead / Architect** | Plan + supervise | `select_tech_stack`, `design_architecture` (mermaid), `define_api_spec` (OpenAPI), `design_db_schema`, `code_review`, `route_workflow` |
| 💻 **Software Engineer** | Code/Operate | `scaffold_project`, `write_source_file`, `write_unit_tests`, `run_tests`, `fix_bug` |
| 🧪 **QA / SDET** | Plan + Deploy | `generate_test_cases`, `edge_case_analysis`, `write_e2e_tests`, `run_tests` |
| 🚀 **DevOps / SRE** | Code/Deploy/Operate | `write_dockerfile`, `generate_ci_pipeline`, `generate_cd_pipeline`, `write_terraform`, `write_k8s_manifests`, `write_monitoring_config`, `write_runbook` |

Skills come in two kinds: **tool-backed** skills that perform real I/O (writing files,
running pytest — implemented as LangChain `@tool`s under `skills/common/`) and
**reasoning** skills the LLM performs in-context.

### The skills library (`src/software_team/skills/`)

Skills follow the **Agent Skills convention** (as used by
[forgecode's `create-skill`](https://github.com/tailcallhq/forgecode/tree/main/crates/forge_repo/src/skills/create-skill)):
**each skill is a directory with a `SKILL.md`** — YAML frontmatter (`name`, a "use when"
`description`, and an optional `tool:`) plus a concise markdown body of instructions.
The bodies encode real, researched practice (INVEST, MoSCoW, Nielsen's heuristics, the
C4 model, ADRs, equivalence partitioning / boundary-value analysis, the test pyramid,
12-factor, the four golden signals, SLO/SLI/error budgets, blue-green/canary rollouts,
…). At runtime each character's system prompt is **composed from its skills' bodies**, so
the files in this directory actually drive behaviour — they are not just documentation.

```
skills/
  base.py                     # the Skill dataclass + guidance composer
  loader.py                   # discovers & parses SKILL.md frontmatter + body
  registry.py                 # groups skills by character -> ROLE_SKILLS
  common/                     # executable tools (filesystem, shell, web search) + tool registry + authoring
  library/                    # the SKILL.md skill library, one folder per character
    product_manager/          #   parse-spec, write-user-stories, define-acceptance-criteria,
                              #     prioritize-backlog, track-metrics
    ux_designer/              #   map-user-flow, create-wireframe, specify-components,
                              #     apply-usability-heuristics, ensure-accessibility
    tech_lead/                #   select-tech-stack, design-architecture, write-adr,
                              #     define-api-spec, design-db-schema, review-code, route-workflow
    software_engineer/        #   scaffold-project, write-code, write-unit-tests,
                              #     run-tests, fix-bug, manage-version-control
    qa_engineer/              #   design-test-cases, write-e2e-tests, analyze-edge-cases,
                              #     plan-performance-tests, execute-tests, inspect-project
    devops_sre/               #   containerize-service, build-ci-pipeline, build-cd-pipeline,
                              #     write-infrastructure-code, write-k8s-manifests,
                              #     configure-observability, write-runbook
```

A skill becomes **tool-backed** by naming a tool in its frontmatter (e.g. `tool: run_tests`);
the loader resolves it against `common/tools.py` and binds the real LangChain `@tool`.

**Add a skill**: create `library/<character>/<verb-based-name>/SKILL.md` with `name` +
`description` frontmatter and a short instructions body. It is loaded automatically — no
code change. Add `tool: <name>` to make it executable.

Sources for the practices baked into the skill bodies:
[INVEST](https://www.volkerdon.com/pages/invest-criteria) ·
[MoSCoW / acceptance criteria](https://www.atlassian.com/work-management/project-management/acceptance-criteria) ·
[C4 model + ADRs](https://medium.com/decathlondigital/software-architecture-architecture-decision-record-c4-11ceff211baf) ·
[test design techniques](https://www.qamadness.com/5-essential-test-design-techniques-qa-2026/) ·
[SRE golden signals / SLOs](https://medium.com/@sainath.814/devops-roadmap-part-32-sre-fundamentals-slis-slos-error-budgets-incident-response-abc3c4f7db01).

## Workflow (LangGraph)

The Tech Lead acts as supervisor. Two feedback loops (review changes, failing tests)
bounce work back to the engineer, each bounded by an iteration cap so the run always
terminates.

```
START → PM → UX → TechLead(design) → QA(plan) → SWE → TechLead(review)
                                                         │
                       ┌──────── changes (cap) ──────────┘
                       ▼                       approve
                     SWE                          │
                                                  ▼
                                            DevOps(CI) → QA(run tests)
                                                            │
                          ┌──────── fail (cap) ─────────────┤
                          ▼                       pass       │
                    SWE(fix) → QA(run tests)                 ▼
                                                     DevOps(CD) → Operate → END
```

Each character reads the shared **TeamState blackboard** (`src/software_team/state.py`)
and contributes its artifacts.

## Quick start

```bash
# 1. Install dependencies (uses uv; Python pinned to 3.12 via .python-version)
uv sync --extra dev

# 2a. Offline demo — no model needed, generates a complete, test-passing project
uv run software-team run --spec examples/sample_spec.md --dry-run

# 2b. Live run — default backend is Ollama
./scripts/setup.sh                 # installs models: qwen2.5-coder:7b, llama3.1:8b
uv run software-team run --spec examples/sample_spec.md

# Other backends (set SWTEAM_LLM_PROVIDER, install the matching extra):
#   uv sync --extra openai     && SWTEAM_LLM_PROVIDER=openai     OPENAI_API_KEY=...  uv run software-team run -s examples/sample_spec.md
#   uv sync --extra google     && SWTEAM_LLM_PROVIDER=google     GOOGLE_API_KEY=...  uv run software-team run -s examples/sample_spec.md
#   uv sync --extra llama-cpp  && SWTEAM_LLM_PROVIDER=llama_cpp  SWTEAM_CODER_MODEL=/models/coder.gguf uv run software-team run -s examples/sample_spec.md

# Enable internet search so characters fetch the latest APIs/best practices:
uv sync --extra search             # keyless DuckDuckGo (SWTEAM_SEARCH_PROVIDER=duckduckgo)

# Inspect what the team built
ls -R workspace/
uv run pytest workspace/           # run the generated project's tests

# See each character's skills
uv run software-team skills
```

### Input

The PM consumes a plain markdown/text **spec file** of use-cases — see
`examples/sample_spec.md`. Point `--spec` at your own file to build something else.

### Output (`workspace/`)

```
app/                     # runnable FastAPI service (pure logic + thin web adapter)
tests/                   # unit tests + E2E API tests (run automatically by QA)
requirements.txt
Dockerfile
.github/workflows/       # ci.yml, cd.yml
terraform/main.tf        # IaC
k8s/                     # deployment (+ readiness probe) and service
monitoring/              # prometheus.yml, alerts.yml
docs/                    # backlog, ux, architecture, openapi, schema, test plan,
                         # runbook, operations report
```

## Configuration

Copy `.env.example` and adjust. Key variables:

**LLM provider**

- `SWTEAM_LLM_PROVIDER` — `ollama` (default), `openai`, `google`, or `llama_cpp`.
  Install the matching extra (`uv sync --extra openai|google|llama-cpp`).
- `SWTEAM_CODER_MODEL` — model for Tech Lead + Software Engineer (needs strong code +
  tool calling). Defaults per provider (Ollama `qwen2.5-coder:7b`, OpenAI `gpt-4o`,
  Google `gemini-1.5-pro`; for `llama_cpp` set it to a local `.gguf` path).
- `SWTEAM_NARRATIVE_MODEL` — model for PM/UX/QA-planning/DevOps prose. Defaults per
  provider (Ollama `llama3.1:8b`, OpenAI `gpt-4o-mini`, Google `gemini-1.5-flash`). Set
  both to the same value to run on a single model.
- Credentials/endpoints: `OLLAMA_HOST`, `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`
  for OpenAI-compatible servers), `GOOGLE_API_KEY`.

**Internet search** (every character pulls the latest info it needs)

- `SWTEAM_SEARCH_PROVIDER` — `duckduckgo` (default, keyless via `uv sync --extra search`),
  `tavily` (needs `TAVILY_API_KEY`, `uv sync --extra tavily`), or `none` to disable.
- `SWTEAM_SEARCH_MAX_RESULTS` — results per query (default 4). Search is skipped in
  `--dry-run` and fails soft (no network/package → the run continues without it).

**Other**

- `SWTEAM_TEMPERATURE` — generation temperature (default 0.2).
- `SWTEAM_MAX_REVIEW_ITERS`, `SWTEAM_MAX_FIX_ITERS` — feedback-loop caps (default 2).

## Design notes

- **Deterministic orchestration.** Local models are unreliable at multi-step tool
  calling, so the pipeline doesn't depend on it: each character makes a single
  structured generation, and Python *skill functions* persist artifacts and run
  commands. Tool-backed skills are still bound for the SWE/QA loop on capable models.
- **Verifiable by construction.** Codegen targets Python/FastAPI with business logic
  kept framework-free, so the generated unit tests pass with only pytest installed; the
  FastAPI E2E tests `importorskip` when FastAPI isn't present.
- **Search grounds, it doesn't drive.** To fit the single-generation design, each
  character runs its web queries *before* generating and the findings are folded into
  that one prompt (rather than a multi-step tool loop). `web_search` is also registered as
  a LangChain tool for tool-capable models. Search is best-effort: disabled in dry-run and
  silent on any failure, so it never blocks a run.

## Project layout

```
src/software_team/
  config.py      # LLM provider, per-role model tiers, web search, paths, loop caps
  state.py       # TeamState blackboard
  llm.py         # multi-provider chat-model factory (ollama/openai/google/llama_cpp) + dry-run stub
  dryrun.py      # canned artifacts for --dry-run
  ui.py          # console reporting
  skills/        # SKILL.md library (loader, registry, common tools incl. web search) — one folder per character
  agents/        # the six characters (one file each) + base helpers
  graph.py       # LangGraph StateGraph wiring the phases + loops
  main.py        # Typer CLI
tests/           # framework tests (routers, skills, full dry-run pipeline)
examples/        # sample_spec.md
scripts/setup.sh
```

## Tests

```bash
uv run pytest
```

Covers the supervisor routing/iteration caps, the file-writing skills, and a full
dry-run pass of the graph that asserts every phase's artifacts land on disk and the
generated project's own tests pass.

## Code style

The codebase follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
(naming, import grouping, and `Args:`/`Returns:`/`Raises:` docstrings). It is enforced
with Ruff — configured in `pyproject.toml` under `[tool.ruff]`:

```bash
uv run ruff check .      # lint (naming, imports, docstrings, bugs)
uv run ruff format .     # auto-format
```
