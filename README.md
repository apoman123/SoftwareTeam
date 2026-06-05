# Software Team — a multi-agent SDLC crew (LangChain + LangGraph)

A cross-functional, "you build it, you run it" software team, implemented as a
multi-agent system. Tell the Product Manager what you want — either a spec **file**
describing your use cases, or a one-line feature **prompt** on the command line — and six
AI characters carry the feature through the whole software lifecycle — Plan & Design →
Code & Build → Deploy & Release → Operate & Monitor → Document & Handoff — writing a
runnable project plus all its CI/CD, DevOps, and documentation artifacts to a workspace
directory.

Highlights:

- **Six specialist characters.** A Product Manager, UI/UX Designer, Tech Lead, Software
  Engineer, QA/SDET, and DevOps/SRE — each a graph node with its own curated skill set.
- **Pluggable LLM backend.** Pick a local Ollama server, the OpenAI API (or any
  OpenAI-compatible endpoint), the Anthropic API (Claude), Google Gemini (google-genai),
  or a local GGUF model via llama.cpp, with a single environment variable.
- **Grounded in current facts.** Every character can search the web for what it needs —
  current library APIs, today's stable versions, fresh best practices — and fold the
  findings into its work.
- **Runs offline.** A `--dry-run` mode produces a complete, test-passing example with no
  model server, provider package, or network at all.

## The characters and their skills

Each role is a graph node with an explicit, curated skill set, defined in
`src/software_team/skills/registry.py`. Run `software-team skills` to print the full
catalogue.

| Character | Phase focus | Skills |
|-----------|-------------|--------|
| 🧭 **Product Manager** | Plan + Document | `parse-spec`, `write-user-stories`, `define-acceptance-criteria`, `prioritize-backlog`, `track-metrics`, `write-user-manual` |
| 🎨 **UI/UX Designer** | Plan | `map-user-flow`, `create-wireframe`, `specify-components`, `apply-usability-heuristics`, `ensure-accessibility` |
| 🧠 **Tech Lead / Architect** | Plan + supervise | `select-tech-stack`, `design-architecture`, `define-api-spec`, `design-db-schema`, `write-adr`, `review-code`, `route-workflow` |
| 💻 **Software Engineer** | Code + Operate + Document | `scaffold-project`, `write-code`, `write-unit-tests`, `run-tests`, `fix-bug`, `manage-version-control`, `write-readme` |
| 🧪 **QA / SDET** | Plan + Deploy + Document | `design-test-cases`, `analyze-edge-cases`, `write-e2e-tests`, `plan-performance-tests`, `execute-tests`, `inspect-project`, `write-test-report` |
| 🚀 **DevOps / SRE** | Code + Deploy + Operate + Document | `containerize-service`, `build-ci-pipeline`, `build-cd-pipeline`, `write-infrastructure-code`, `write-k8s-manifests`, `configure-observability`, `write-runbook`, `document-infrastructure` |

Skills come in two kinds: **tool-backed** skills that perform real I/O (writing files,
running pytest — implemented as LangChain `@tool`s under `skills/common/`) and
**reasoning** skills that the LLM performs in context.

**Foundation skills for the code authors.** The three characters that write code —
💻 Software Engineer, 🧪 QA/SDET, and 🚀 DevOps/SRE — additionally load two shared
**foundation** skills *first*, before any role-specific skill: `karpathy-guidelines`
(behaviour rules that cut common LLM coding mistakes — think before coding, keep it
simple, make surgical changes, work to verifiable goals) and then `follow-google-style`
(write every file to the [Google style guide](https://google.github.io/styleguide/) for
its language). They live in `skills/library/_foundation/` because they are cross-cutting,
and the loader prepends them for the `CODE_AUTHORS` set so the engineering baseline frames
everything that follows.

### The skills library (`src/software_team/skills/`)

Skills follow **[Anthropic's Agent Skills convention](https://platform.claude.com/docs/en/docs/agents-and-tools/agent-skills/overview)**:
**each skill is a directory containing a `SKILL.md`** — YAML frontmatter plus a concise
markdown body of instructions. The two required frontmatter fields obey Anthropic's
[authoring rules](https://platform.claude.com/docs/en/docs/agents-and-tools/agent-skills/best-practices):

- **`name`** — lowercase letters, numbers and hyphens only, ≤ 64 characters, no reserved
  words (`anthropic`/`claude`); it matches the skill's directory name. We use
  action-oriented verb names (`write-code`, `run-tests`) — an accepted Anthropic pattern
  (its stated preference is the gerund form, e.g. `writing-code`).
- **`description`** — third person, stating both **what** the skill does and **when** to
  use it, ≤ 1024 characters. We follow Anthropic's recommended shape *"&lt;what it does&gt;.
  Use when &lt;trigger&gt;."*, e.g. `run-tests`: *"Runs the test suite locally and self-checks
  the result. Use before declaring work done."*

Per Anthropic's **progressive disclosure** principle the bodies are kept short (well under
the 500-line guideline). They encode real, researched practice (INVEST, MoSCoW, Nielsen's
heuristics, the C4 model, ADRs, equivalence partitioning / boundary-value analysis, the
test pyramid, 12-factor, the four golden signals, SLO/SLI/error budgets,
blue-green/canary rollouts, …). At runtime each character's system prompt is **composed
from its skills' bodies**, so the files in this directory actually drive behaviour — they
are not just documentation.

```text
skills/
  base.py        # the Skill dataclass + guidance composer
  loader.py      # discovers and parses each SKILL.md (frontmatter + body)
  registry.py    # groups skills by character -> ROLE_SKILLS
  common/        # executable tools (filesystem, shell, web search), tool registry, authoring
  library/       # the SKILL.md library — one folder per character, one folder per skill
    _foundation/        # shared skills the code authors load first (karpathy-guidelines, follow-google-style)
    product_manager/    ux_designer/    tech_lead/
    software_engineer/  qa_engineer/    devops_sre/
```

Beyond the two standard fields, a `SKILL.md` may carry one **project-specific extension** —
an optional **`tool:`** key naming an executable to bind (e.g. `tool: run_tests`). The
loader resolves it against `common/tools.py` and binds the real LangChain `@tool`, making
the skill **tool-backed**; skills without it are **reasoning** skills the model performs
in context.

**Add a skill:** create `library/<character>/<verb-name>/SKILL.md` with a conforming
`name` and `description` (see the rules above) and a short instructions body. It is loaded
automatically — no code change. Add `tool: <name>` to make it executable.

Sources for the practices baked into the skill bodies:
[INVEST](https://www.volkerdon.com/pages/invest-criteria) ·
[MoSCoW / acceptance criteria](https://www.atlassian.com/work-management/project-management/acceptance-criteria) ·
[C4 model + ADRs](https://medium.com/decathlondigital/software-architecture-architecture-decision-record-c4-11ceff211baf) ·
[test design techniques](https://www.qamadness.com/5-essential-test-design-techniques-qa-2026/) ·
[SRE golden signals / SLOs](https://medium.com/@sainath.814/devops-roadmap-part-32-sre-fundamentals-slis-slos-error-budgets-incident-response-abc3c4f7db01).

## Workflow (LangGraph)

The Tech Lead acts as supervisor. Two feedback loops (review changes, failing tests)
bounce work back to the engineer, each bounded by an iteration cap so the run always
terminates. A final **Document & Handoff** phase then has each role write the
documentation it knows best.

```text
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
                                                     DevOps(CD) → Operate
                                                                    │
                                                                    ▼
  END ← PM(user manual) ← DevOps(infra docs) ← QA(test report) ← SWE(README)
```

Each character reads the shared **TeamState blackboard** (`src/software_team/state.py`)
and contributes its artifacts.

### Who documents what

Documentation follows the principle *"whoever understands a part best writes it down"*,
so the closing phase splits it by responsibility — the same way a real team does:

| Question | Owner | Artifact |
|----------|-------|----------|
| **How** do I set up and run it? | 💻 Software Engineer | `README.md` (setup, run, API usage) |
| Is it **tested**? | 🧪 QA / SDET | `docs/test_report.md` (coverage, results, residual risk) |
| **Where & When** does it deploy / alert? | 🚀 DevOps / SRE | `docs/infrastructure.md` (pipelines, resources, rollout) + `docs/runbook.md` |
| **Why & What** does it do for users? | 🧭 Product Manager | `docs/user_manual.md` + `docs/release_notes.md` |

## Quick start

```bash
# 1. Install dependencies (uses uv; Python pinned to 3.12 via .python-version)
uv sync --extra dev

# 2a. Offline demo — no model needed, generates a complete, test-passing project
uv run software-team run --spec examples/sample_spec.md --dry-run

# 2b. Live run — default backend is Ollama
./scripts/setup.sh                 # installs models: qwen2.5-coder:7b, llama3.1:8b
uv run software-team run --spec examples/sample_spec.md

# Or skip the file and just tell the PM what to build with a prompt:
uv run software-team run --prompt "Build a URL shortener with click analytics" --dry-run

# Other backends (set SWTEAM_LLM_PROVIDER, install the matching extra):
#   uv sync --extra openai     && SWTEAM_LLM_PROVIDER=openai     OPENAI_API_KEY=...     uv run software-team run -s examples/sample_spec.md
#   uv sync --extra anthropic  && SWTEAM_LLM_PROVIDER=anthropic  ANTHROPIC_API_KEY=...  uv run software-team run -s examples/sample_spec.md
#   uv sync --extra google     && SWTEAM_LLM_PROVIDER=google     GOOGLE_API_KEY=...     uv run software-team run -s examples/sample_spec.md
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

There are two ways to tell the Product Manager what to build; provide exactly one:

- **A spec file** — point `--spec` at a plain markdown/text file of use cases (see
  `examples/sample_spec.md`). Best for anything with multiple use cases, non-functional
  requirements, or out-of-scope notes.
- **A prompt** — pass `--prompt "…"` to describe the feature inline. Handy for a quick,
  one-line feature request without writing a file first.

Either way the request becomes the same `spec_text` the PM turns into requirements, so
the rest of the pipeline is identical. The intake logic lives in
`src/software_team/intake.py`.

### Output (`workspace/`)

```text
README.md                # how to set up, run, and call the service (Software Engineer)
app/                     # runnable FastAPI service (pure logic + thin web adapter)
tests/                   # unit tests + E2E API tests (run automatically by QA)
requirements.txt
Dockerfile
.github/workflows/       # ci.yml, cd.yml
terraform/main.tf        # IaC
k8s/                     # deployment (+ readiness probe) and service
monitoring/              # prometheus.yml, alerts.yml
docs/                    # backlog, ux, architecture, openapi, schema, test plan,
                         # runbook, operations report, and the handoff docs:
                         # test_report, infrastructure, user_manual, release_notes
```

## Configuration

Copy `.env.example` and adjust. Key variables:

**LLM provider**

- `SWTEAM_LLM_PROVIDER` — `ollama` (default), `openai`, `anthropic`, `google`, or
  `llama_cpp`. Install the matching extra (`uv sync --extra openai|anthropic|google|llama-cpp`).
- `SWTEAM_CODER_MODEL` — model for the Tech Lead and Software Engineer (needs strong code
  and tool calling). Defaults per provider (Ollama `qwen2.5-coder:7b`, OpenAI `gpt-4o`,
  Anthropic `claude-opus-4-8`, Google `gemini-1.5-pro`; for `llama_cpp` set it to a local
  `.gguf` path).
- `SWTEAM_NARRATIVE_MODEL` — model for PM/UX/QA-planning/DevOps prose. Defaults per
  provider (Ollama `llama3.1:8b`, OpenAI `gpt-4o-mini`, Anthropic `claude-sonnet-4-6`,
  Google `gemini-1.5-flash`). Set both models to the same value to run on a single model.
- Credentials and endpoints: `OLLAMA_HOST`, `OPENAI_API_KEY` (plus optional
  `OPENAI_BASE_URL` for OpenAI-compatible servers), `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`.

> **Note (Anthropic):** Claude Opus 4.7 and 4.8 no longer accept a `temperature`
> parameter, so `SWTEAM_TEMPERATURE` is ignored for those models (the factory omits it to
> avoid an API error). Older Claude models and the other providers still honour it.

**Internet search** (every character pulls the latest info it needs)

- `SWTEAM_SEARCH_PROVIDER` — `duckduckgo` (default, keyless via `uv sync --extra search`),
  `tavily` (needs `TAVILY_API_KEY`, `uv sync --extra tavily`), or `none` to disable.
- `SWTEAM_SEARCH_MAX_RESULTS` — results per query (default 4). Search is skipped in
  `--dry-run` and fails soft (no network or package → the run continues without it).

**Other**

- `SWTEAM_TEMPERATURE` — generation temperature (default 0.2).
- `SWTEAM_MAX_REVIEW_ITERS`, `SWTEAM_MAX_FIX_ITERS` — feedback-loop caps (default 2).

## Design notes

- **Deterministic orchestration.** Local models are unreliable at multi-step tool
  calling, so the pipeline doesn't depend on it: each character makes a single
  structured generation, and Python *skill functions* persist artifacts and run
  commands. Tool-backed skills are still bound for the SWE/QA loop on capable models.
- **Verifiable by construction.** Code generation targets Python/FastAPI with business
  logic kept framework-free, so the generated unit tests pass with only pytest installed;
  the FastAPI E2E tests `importorskip` when FastAPI isn't present.
- **Search grounds, it doesn't drive.** To fit the single-generation design, each
  character runs its web queries *before* generating and folds the findings into that one
  prompt (rather than a multi-step tool loop). `web_search` is also registered as a
  LangChain tool for tool-capable models. Search is best-effort: disabled in dry-run and
  silent on any failure, so it never blocks a run.

## Project layout

```text
src/software_team/
  config.py      # LLM provider, per-role model tiers, web search, paths, loop caps
  intake.py      # resolve the feature request from a --spec file or a --prompt
  state.py       # TeamState blackboard
  llm.py         # multi-provider chat-model factory (ollama/openai/anthropic/google/llama_cpp) + dry-run stub
  dryrun.py      # canned artifacts for --dry-run
  ui.py          # console reporting
  skills/        # SKILL.md library (loader, registry, common tools incl. web search)
  agents/        # the six characters (one file each) + shared node helpers
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

The suite covers the supervisor routing and iteration caps, the file-writing skills, and
a full dry-run pass of the graph that asserts every phase's artifacts land on disk and
the generated project's own tests pass.

## Code style

The codebase follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
(naming, import grouping, and `Args:`/`Returns:`/`Raises:` docstrings), enforced with
Ruff and configured in `pyproject.toml` under `[tool.ruff]`:

```bash
uv run ruff check .      # lint (naming, imports, docstrings, likely bugs)
uv run ruff format .     # auto-format
```
