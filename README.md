# Software Team — a multi-agent SDLC crew (LangChain + LangGraph + Ollama)

A **cross-functional, "you build it, you run it" software team** implemented as a
multi-agent system. You hand it a **spec file** describing your use-cases; six AI
characters carry the feature through the **whole software lifecycle** — Plan & Design →
Code & Build → Deploy & Release → Operate & Monitor — and write a **runnable project
plus all CI/CD and DevOps artifacts** to a workspace directory.

It runs entirely on **local models via Ollama**, and ships with a **`--dry-run`** mode
that produces a complete, test-passing example with no model server at all.

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
running pytest — implemented as LangChain `@tool`s in `skills/filesystem.py` and
`skills/shell.py`) and **reasoning** skills the LLM performs in-context.

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

# 2b. Live run — needs Ollama + models
./scripts/setup.sh                 # installs models: qwen2.5-coder:7b, llama3.1:8b
uv run software-team run --spec examples/sample_spec.md

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

- `OLLAMA_HOST` — Ollama endpoint (default `http://localhost:11434`).
- `SWTEAM_CODER_MODEL` — model for Tech Lead + Software Engineer (needs strong code +
  tool calling). Default `qwen2.5-coder:7b`.
- `SWTEAM_NARRATIVE_MODEL` — model for PM/UX/QA-planning/DevOps prose. Default
  `llama3.1:8b`. Set both to the same model to run on a single model.
- `SWTEAM_MAX_REVIEW_ITERS`, `SWTEAM_MAX_FIX_ITERS` — feedback-loop caps (default 2).

## Design notes

- **Deterministic orchestration.** Local models are unreliable at multi-step tool
  calling, so the pipeline doesn't depend on it: each character makes a single
  structured generation, and Python *skill functions* persist artifacts and run
  commands. Tool-backed skills are still bound for the SWE/QA loop on capable models.
- **Verifiable by construction.** Codegen targets Python/FastAPI with business logic
  kept framework-free, so the generated unit tests pass with only pytest installed; the
  FastAPI E2E tests `importorskip` when FastAPI isn't present.

## Project layout

```
src/software_team/
  config.py      # per-role model tiers, paths, loop caps
  state.py       # TeamState blackboard
  llm.py         # ChatOllama factory + dry-run stub
  dryrun.py      # canned artifacts for --dry-run
  ui.py          # console reporting
  skills/        # filesystem, shell, authoring, registry (role→skills)
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
