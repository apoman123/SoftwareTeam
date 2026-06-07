# Software Team — a multi-agent SDLC crew (LangChain + LangGraph)

A cross-functional, "you build it, you run it" software team, implemented as a
multi-agent system. Tell the Product Manager what you want — either a spec **file**
describing your use cases, or a one-line feature **prompt** on the command line — and a
team of AI characters carries the feature through the whole software lifecycle — Plan &
Design → Code & Build → Deploy & Release → Operate & Monitor → Document & Handoff — writing
a runnable project plus all its CI/CD, DevOps, and documentation artifacts to a workspace
directory. The pipeline is **capability-aware**: it only runs the phases a project needs
(no frontend for a pure API, no deployment for a library — see below).

Highlights:

- **Six specialist characters.** A Product Manager, UI/UX Designer, Tech Lead, Software
  Engineer, QA/SDET, and DevOps/SRE — each a graph node with its own curated skill set. A
  Frontend Engineer (reusing the Software Engineer's skill set) joins whenever the product
  needs a UI.
- **Capability-aware routing.** Deterministic triage classifies the spec into
  `needs_frontend` / `needs_backend` / `needs_deployment`, and the supervisor skips phases
  that don't apply: no UX/frontend for a pure API, no backend for a static/frontend-only
  site, and no containerisation/CI-CD/operate for a library, CLI or script.
- **Pluggable LLM backend.** Pick a local Ollama server, the OpenAI API (or any
  OpenAI-compatible endpoint), the Anthropic API (Claude), Google Gemini (google-genai),
  or a local GGUF model via llama.cpp, with a single environment variable.
- **Grounded in current facts.** Every character can search the web for what it needs —
  current library APIs, today's stable versions, fresh best practices — and fold the
  findings into its work.
- **Builds new or extends existing.** `run` builds a project from scratch; `feature`
  integrates a new request into software the team already developed, re-running the whole
  lifecycle so the change is reviewed, regression-tested, redeployed, and documented.
- **Runs offline.** A `--dry-run` mode produces a complete, test-passing example with no
  model server, provider package, or network at all.

## The characters and their skills

Each role is a graph node with an explicit, curated skill set, defined in
`src/software_team/skills/registry.py`. Run `software-team skills` to print the full
catalogue.

| Character | Phase focus | Skills |
|-----------|-------------|--------|
| 🧭 **Product Manager** | Plan + Document | `parse-spec`, `write-user-stories`, `define-acceptance-criteria`, `prioritize-backlog`, `track-metrics`, `write-user-manual` |
| 🎨 **UI/UX Designer** | Plan | `map-user-flow`, `describe-ui-layout`, `specify-components`, `apply-usability-heuristics`, `apply-ui-quality-checklist`, `ensure-accessibility` |
| 🧠 **Tech Lead / Architect** | Plan + supervise | `select-tech-stack`, `design-architecture`, `define-api-spec`, `design-db-schema`, `write-adr`, `review-code`, `route-workflow` |
| 💻 **Software Engineer** | Code + Operate + Document | `scaffold-project`, `write-code`, `write-unit-tests`, `run-tests`, `fix-bug`, `manage-version-control`, `write-readme` |
| 🖥️ **Frontend Engineer** _(only if `needs_frontend`)_ | Code | reuses the Software Engineer's skill set; builds the UI under `frontend/` from the UX + API contract |
| 🧪 **QA / SDET** | Plan + Deploy + Document | `design-test-cases`, `analyze-edge-cases`, `write-e2e-tests`, `plan-performance-tests`, `execute-tests`, `inspect-project`, `write-test-report` |
| 🚀 **DevOps / SRE** | Code + Deploy + Operate + Document | `containerize-service`, `build-ci-pipeline`, `build-cd-pipeline`, `write-infrastructure-code`, `write-k8s-manifests`, `configure-observability`, `write-runbook`, `audit-container-security`, `document-infrastructure` |

The CI/CD that DevOps/SRE generates is **GitLab CI integrated with Jenkins**: a
`.gitlab-ci.yml` lints and tests every merge request and then triggers a `Jenkinsfile`
(Declarative pipeline) for the heavier build and a safe, rollback-capable deploy. Several
characters also load **external, attributed skills** (Jenkins, GitLab, code-review,
performance) — see [External skills](#external-skills-shared-with-attribution) below.

**DevSecOps for the DevOps/SRE.** The pipeline shifts security left: the generated
`.gitlab-ci.yml` adds a `security` stage (SAST, dependency/SCA scan, and a Trivy image+config
CVE scan that fails on HIGH/CRITICAL, plus an SBOM), the Dockerfile and Kubernetes manifests
are hardened (non-root, pinned image, dropped capabilities, read-only root filesystem,
resource limits), and the 🚀 DevOps/SRE then runs an offline **security audit**
(`skills/common/security.py`) over those artifacts, writing a pass/total review to
`docs/security_review.md`. The DevSecOps knowledge (six shared skills + the
`audit-container-security` tool-backed skill) is adapted from
[**BagelHole/DevOps-Security-Agent-Skills**](https://github.com/BagelHole/DevOps-Security-Agent-Skills)
(MIT, © 2026 Toby Miller). The audit is deterministic and offline, so it also runs in `--dry-run`.

**Describe, don't draw — for the UI/UX Designer.** The 🎨 UI/UX Designer hands the Tech
Lead a *written* description of the UI and the user experience — never a drawing. It maps
the user flow, describes each screen's layout, content hierarchy and primary action in
words (no wireframes, ASCII art, or diagrams), specifies each component's states,
validation and copy, and checks the design against Nielsen's heuristics and WCAG's POUR
principles. The output is `docs/ux_design.md`, which the Tech Lead designs the
architecture against. The companion `apply-ui-quality-checklist` skill distils a
priority-ordered UX review pass adapted from
[**nextlevelbuilder/ui-ux-pro-max-skill**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(MIT, © 2024 Next Level Builder).

Skills come in two kinds: **tool-backed** skills that perform real I/O (writing files,
running the project's test suite — implemented as LangChain `@tool`s under `skills/common/`)
and **reasoning** skills that the LLM performs in context.

**Foundation skills for the code authors.** The three characters that write code —
💻 Software Engineer, 🧪 QA/SDET, and 🚀 DevOps/SRE — additionally load two shared
**foundation** skills *first*, before any role-specific skill: `karpathy-guidelines`
(behaviour rules that cut common LLM coding mistakes — think before coding, keep it
simple, make surgical changes, work to verifiable goals; adapted from
[multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/tree/main/skills/karpathy-guidelines),
after [Andrej Karpathy](https://x.com/karpathy/status/2015883857489522876)) and then `follow-google-style`
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
    security.py       # offline DevSecOps audit of Dockerfile/k8s/CI artifacts (security_audit tool)
  library/       # the SKILL.md library — one folder per character, one folder per skill
    _foundation/        # shared skills the code authors load first (karpathy-guidelines, follow-google-style)
    _shared/            # externally-sourced skills several characters reuse (see "External skills" below)
    product_manager/    ux_designer/    tech_lead/
    software_engineer/  qa_engineer/    devops_sre/
```

### External skills (shared, with attribution)

Some skills are adapted from excellent open-source skill collections rather than authored
from scratch. They live in `library/_shared/` (one on-disk copy, MIT-licensed sources
cited in each `SKILL.md`) and `loader.py`'s **`SHARED_SKILLS`** map decides which
characters load which — *"make the agents that need a skill load it"* — so e.g. the `glab`
GitLab-CLI skill is shared by the Software Engineer and DevOps/SRE without duplication.
They compose **after** a character's own role skills.

| Character | Shared skills it loads | Source |
|-----------|------------------------|--------|
| 🧠 **Tech Lead** | `code-review-and-quality`, `documentation-and-adrs`, `mr-review` | addyosmani · GitLab |
| 💻 **Software Engineer** | `git-workflow-and-versioning`, `commit-messages`, `glab` | addyosmani · GitLab |
| 🧪 **QA / SDET** | `performance-optimization`, `self-service-performance-testing` | addyosmani · GitLab |
| 🚀 **DevOps / SRE** | `jenkins-expert`, `ci-cd-and-automation`, `security-and-hardening`, `gitlab-pipeline-watch`, `glab`, `vulnerability-scanning`, `sast-scanning`, `dependency-scanning`, `sbom-supply-chain`, `container-hardening`, `kubernetes-hardening` | 0xfurai · addyosmani · GitLab · BagelHole |

The DevOps/SRE's six DevSecOps skills (`vulnerability-scanning`, `sast-scanning`,
`dependency-scanning`, `sbom-supply-chain`, `container-hardening`, `kubernetes-hardening`)
are distilled from [**BagelHole/DevOps-Security-Agent-Skills**](https://github.com/BagelHole/DevOps-Security-Agent-Skills)
(MIT, © 2026 Toby Miller); its tool-backed `audit-container-security` skill (a DevOps role
skill) runs the offline `security_audit` tool built from the same checklist.

The 🎨 **UI/UX Designer**'s `apply-ui-quality-checklist` is a reasoning skill that distils
a priority-ordered UX review pass adapted from
[**nextlevelbuilder/ui-ux-pro-max-skill**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(MIT, © 2024 Next Level Builder). The designer describes the UI in words for the Tech
Lead and draws nothing, so it ships no embedded engine or vendored data.

Sources (all MIT-licensed; each `SKILL.md` carries the specific link):
[`jenkins-expert`](https://github.com/0xfurai/claude-code-subagents/blob/main/agents/jenkins-expert.md)
from **0xfurai/claude-code-subagents** ·
[**addyosmani/agent-skills**](https://github.com/addyosmani/agent-skills/tree/main/skills) ·
[**gitlab-org/ai/skills**](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills) ·
[**nextlevelbuilder/ui-ux-pro-max-skill**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) ·
[**BagelHole/DevOps-Security-Agent-Skills**](https://github.com/BagelHole/DevOps-Security-Agent-Skills).
Add or re-map a shared skill by dropping a `SKILL.md` under `library/_shared/<name>/` and
listing it in `SHARED_SKILLS` for the characters that need it — no other code change.

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

# Add a feature to software the team already built (brownfield/incremental mode):
uv run software-team feature --into workspace --prompt "Add task priorities" --dry-run
#   …or from a spec file, writing the updated copy elsewhere (leaving the original intact):
uv run software-team feature --into workspace --spec examples/feature_priority.md --out workspace2

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

### Building new vs. extending existing software

There are two commands, and both accept the same `--spec`/`--prompt` input:

- **`run`** — greenfield. Build a brand-new project from the request.
- **`feature`** — brownfield/incremental. Integrate the request as a **new feature into a
  project the team has already developed**. Point `--into` at a previous run's workspace;
  the loader (`src/software_team/project.py`) reads the existing code and docs, seeds them
  into the run, and grounds every phase in what already exists, so the team *extends* the
  software instead of rewriting it. The whole SDLC re-runs (so the change is reviewed,
  tested for regressions, re-deployed, and the docs are refreshed).

```bash
# Modify the project in place:
uv run software-team feature --into workspace --prompt "Add task priorities"

# Or write the updated project to a new directory, leaving the original untouched:
uv run software-team feature --into workspace --spec examples/feature_priority.md --out workspace2
```

In `--dry-run`, the feature command deterministically adds a `priority` field (and a
`POST /tasks/{id}/priority` endpoint) to the demo Task API, with the original tests still
passing — a self-contained demonstration of integrating a feature without breaking what
exists.

### Output (`workspace/`)

```text
README.md                # how to set up, run, and call the service (Software Engineer)
app/                     # runnable service in the chosen stack (pure logic + thin adapter; e.g. FastAPI)
frontend/                # the UI in the chosen frontend stack — only when needs_frontend (Frontend Engineer)
tests/                   # unit tests + E2E API tests (run automatically by QA)
requirements.txt         # the stack's dependency manifest (e.g. package.json / go.mod)
Dockerfile               # hardened: non-root, pinned base, HEALTHCHECK — only when needs_deployment
.gitlab-ci.yml           # GitLab CI/CD: lint + test + security scans, then trigger Jenkins (+ manual deploy)
Jenkinsfile              # Jenkins Declarative pipeline: build + safe rollout with rollback
terraform/main.tf        # IaC
k8s/                     # deployment (hardened securityContext + limits) and service
monitoring/              # prometheus.yml, alerts.yml
docs/                    # backlog, ux, architecture, openapi, schema,
                         # test plan, runbook, operations report, security_review, and the
                         # handoff docs: test_report, infrastructure, user_manual, release_notes
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
- **Stack-agnostic by design.** The team honours whatever language/framework the spec
  asks for: the Tech Lead treats a stated stack as a binding constraint (and the raw spec
  reaches it, so the request is never lost), every node grounds its prompts and research in
  the chosen stack, and the QA quality gate detects each component's ecosystem
  (`package.json`, `go.mod`, `Cargo.toml`, …) and runs that stack's test command instead of
  always `pytest`. When the spec is silent the Tech Lead picks pragmatically — the bundled
  examples and the `--dry-run` project happen to be Python/FastAPI.
- **Capability-aware routing.** `software_team/triage.py` deterministically classifies the
  spec into `needs_frontend`, `needs_backend` and `needs_deployment` (set on the state in
  `new_state`), and the supervisor's conditional edges skip phases that don't apply: a pure
  API skips the UX designer and the Frontend Engineer; a static/frontend-only site skips the
  backend build; a library/CLI/script also skips containerisation, CI/CD, the operate phase,
  and the infrastructure docs. Classification is keyword-based (no LLM, with explicit
  "no X" negation handling) so routing is reproducible and dry-run-safe; defaults are
  conservative (assume a deployable backend, no UI).
- **Multi-component test gate.** QA runs every testable component — the backend at the root
  and the UI under `frontend/` — each with its own detected test command, and the gate
  passes only if all suites that ran passed. A component whose toolchain or dependencies are
  not installed (e.g. `frontend/` without `node_modules`) is **skipped, never failed**, so
  the gate works in a bare environment yet still runs everything it can.
- **Verifiable by construction.** Business logic is kept framework-free, so generated unit
  tests are fast and stable; the Python/FastAPI E2E tests `importorskip` when FastAPI is
  absent.
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
  project.py     # load already-developed software for an incremental `feature` run
  state.py       # TeamState blackboard (build vs. feature mode)
  llm.py         # multi-provider chat-model factory (ollama/openai/anthropic/google/llama_cpp) + dry-run stub
  dryrun.py      # canned artifacts for --dry-run
  ui.py          # console reporting
  skills/        # SKILL.md library (loader, registry, common tools incl. web search + security-audit engine)
  triage.py      # deterministic spec classifier -> needs_frontend / needs_backend / needs_deployment
  agents/        # the characters (one file each, incl. frontend_engineer) + shared node helpers
  graph.py       # LangGraph StateGraph wiring the phases + loops
  main.py        # Typer CLI
tests/           # framework tests (routers, skills, full dry-run pipeline, feature mode)
examples/        # sample_spec.md (greenfield), feature_priority.md (incremental)
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
