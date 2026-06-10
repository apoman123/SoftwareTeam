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
- **Builds new, changes existing, and maintains.** `run` builds a project from scratch;
  `feature`, `modify`, and `remove` change software the team already developed — adding a new
  feature, changing how an existing one behaves, or taking one out (deleting its files) —
  re-running the whole lifecycle so the change is reviewed, regression-tested, redeployed, and
  documented. Two maintenance commands round it out: `gc` scans an existing project for rot and
  fixes it under the Tech Lead, and `debug` runs the project's own tests, diagnoses a bug, and
  fixes it until the suite is green.
- **Runs offline.** A `--dry-run` mode produces a complete, test-passing example with no
  model server, provider package, or network at all.
- **Async & observable.** Every character infers asynchronously (`astream`/`ainvoke`) and
  the graph is driven with `ainvoke`, so a node streams its output live (no more silent,
  idle-looking turns) and never blocks the event loop; each node's web-research queries run
  concurrently. Turn on **LangSmith** with one env var to trace every run — the graph, each
  character's named/tagged LLM call, and the research step.

## The characters and their skills

Each role is a graph node with an explicit, curated skill set, defined in
`src/software_team/skills/registry.py`. Run `software-team skills` to print the full
catalogue.

| Character | Phase focus | Skills |
|-----------|-------------|--------|
| 🧭 **Product Manager** | Plan + Document | `elicit-requirements`, `research-the-market`, `parse-spec`, `write-user-stories`, `define-acceptance-criteria`, `prioritize-backlog`, `track-metrics`, `write-user-manual` |
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
(MIT, © 2024 Next Level Builder). It *describes* but never *draws* — yet it can **look at
sample images** when a spec ships them: any images a spec file references with markdown
`![](…)` (mock-ups, screenshots, brand references — local files or URLs) are discovered at
intake, handed over by the Product Manager, and sent to the designer as multimodal input on
a vision-capable provider, so the written UX is grounded in what the stakeholder showed.

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

The 💻 **Software Engineer**'s `write-unit-tests` skill adapts its test-case strategy
(Given-When-Then, the `{method}_{state}_{outcome}` naming convention, INCLUDE/EXCLUDE
criteria, one behaviour per test, no logic in tests) from
[**clear-solutions/unit-tests-skills**](https://github.com/clear-solutions/unit-tests-skills);
the skill's References section also cites the Google Testing Blog and Anthropic's skill-authoring guide.

Sources (all MIT-licensed; each `SKILL.md` carries the specific link):
[`jenkins-expert`](https://github.com/0xfurai/claude-code-subagents/blob/main/agents/jenkins-expert.md)
from **0xfurai/claude-code-subagents** ·
[**addyosmani/agent-skills**](https://github.com/addyosmani/agent-skills/tree/main/skills) ·
[**gitlab-org/ai/skills**](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills) ·
[**nextlevelbuilder/ui-ux-pro-max-skill**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) ·
[**BagelHole/DevOps-Security-Agent-Skills**](https://github.com/BagelHole/DevOps-Security-Agent-Skills) ·
[**andreaswasita/copilot-agents-dojo**](https://github.com/andreaswasita/copilot-agents-dojo)
(the Product Manager's `elicit-requirements` skill behind the interactive `spec` command).
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

The Tech Lead acts as supervisor. The team builds **one feature at a time**: the Product
Manager decomposes the spec into an ordered **feature plan**, and the Software Engineer
builds each feature in turn. The Tech Lead then *verifies* each feature as the quality gate
— it **installs the project's dependencies and runs its test suite** (a failing suite forces
changes, so "is it without bugs?" is checked, not assumed; installing the deps first — into
an isolated per-workspace virtualenv for Python, `npm install` for a UI — is what lets the
generated project's FastAPI/React imports actually resolve, so the gate runs the tests
instead of erroring on a missing dependency), **runs the project's linter** and turns each
diagnostic into a constructive fix suggestion for the engineer (advisory — lint guides but
does not by itself block), and judges the code against its acceptance criteria — and the loop
only advances to the next feature once the current one is approved. Three feedback loops
(review changes, the feature loop, failing tests) bounce work back to the engineer, each
bounded by an iteration cap so the run always terminates. A final **Document & Handoff** phase
then has each role write the documentation it knows best.

```text
START → PM(feature plan) → UX → TechLead(design) → QA(plan) → SWE(feature i)
                                                                  │
                  ┌──── changes (cap) ─────────────────→ TechLead(review:
                  │                                       run tests + check spec)
                SWE(feature i) ←── approve & more features ───────┤
                                     approve & UI not built ─→ Frontend ─┐
                                     approve & done                      │
                                                  ▼                      │
                                            DevOps(CI) ← (reviewed too) ─┘
                                                  │
                                                  ▼
                                            QA(run tests)
                                                  │
                          ┌──────── fail (cap) ───┤
                          ▼              pass      │
                    SWE(fix) → QA(run tests)       ▼
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

# Change software the team already built (brownfield/incremental mode):
uv run software-team feature --into workspace --prompt "Add task priorities" --dry-run
uv run software-team modify  --into workspace --prompt "Make priorities support a numeric scale"
uv run software-team remove  --into workspace --prompt "Remove the task priority feature"
#   …or from a spec file, writing the updated copy elsewhere (leaving the original intact):
uv run software-team feature --into workspace --spec examples/feature_priority.md --out workspace2

# Maintain software the team built — clean up accumulated rot, or debug a bug you hit running it:
uv run software-team gc    --into workspace --dry-run
uv run software-team debug --into workspace --bug "empty titles are accepted" --dry-run

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

#### …or have the team write the spec *with* you (`spec`)

If you only have a rough idea — or a rough first draft — let the Product Manager **interview
you** and write (or improve) the spec file. Give it exactly one input: a `--prompt` to author
a spec from scratch, or an existing markdown `--spec` to **revise into a better one**:

```bash
# Author a new spec from a one-line idea:
uv run software-team spec --prompt "A recipe sharing app"            # asks, then writes spec.md
uv run software-team spec --prompt "A recipe sharing app" -o specs/recipes.md

# Revise an existing markdown spec into a better one (the input file is left untouched):
uv run software-team spec --spec draft.md --out better.md

# Non-interactive (CI) or offline:
uv run software-team spec --prompt "A recipe sharing app" --no-interactive   # use the input alone
uv run software-team spec --spec draft.md --dry-run                          # offline canned spec
```

The PM **loads the `elicit-requirements` and `research-the-market` skills first**, then
**talks to you** — a short,
*bounded conversation* (capped by `SWTEAM_MAX_INTERVIEW_ROUNDS`, default 3): it opens with
questions about **your needs** (users, must-have features, scope, non-functional
requirements) and the **technology** to use (language/framework/datastore/deploy target — a
stated stack is treated as binding; "no preference" is recorded so the Tech Lead chooses),
then *reads your answers and asks follow-up questions* when something important is still
missing. In **revise** mode the opening questions are **gap-driven** — it reads your draft and
asks about its weakest points (vague or untestable requirements, missing NFRs, no stated
stack, unclear scope). Anything you skip becomes an explicit *open question* rather than a
silent assumption.

Before writing, it **searches the web** (via the `research-the-market` skill) to ground the
spec in current facts — today's stable version of the requested stack (or, when you state no
preference, the technologies teams actually reach for now), plus any domain/compliance
considerations — so the `## Technology` section is not built on the local model's stale
training data. The search is best-effort: if the network is unavailable it simply writes the
spec without it.

It writes the result to `--out` (default `spec.md`; you choose the file name, and a revised
spec never overwrites its `--spec` input) with `## Background`, `## Use cases`,
`## Functional requirements`, `## Non-functional requirements`, `## Technology` and
`## Out of scope` — feed it straight to `run --spec`. The flow lives in
`src/software_team/elicit.py`; it falls back to non-interactive generation when there is no
terminal (CI) so it stays scriptable. The `elicit-requirements` skill is adapted from
[**andreaswasita/copilot-agents-dojo**](https://github.com/andreaswasita/copilot-agents-dojo)
(MIT, © 2026 Andreas Wasita).

### Building new vs. changing existing software

There are four build commands (all accept the same `--spec`/`--prompt` input) plus two
maintenance commands, `gc` and `debug` (described below):

- **`run`** — greenfield. Build a brand-new project from the request.
- **`feature`**, **`modify`**, **`remove`** — brownfield/incremental. Point `--into` at a
  previous run's workspace; the loader (`src/software_team/project.py`) reads the existing
  code and docs, seeds them into the run, and grounds every phase in what already exists, so
  the team *changes* the software instead of rewriting it. The whole SDLC re-runs (so the
  change is reviewed, tested for regressions, re-deployed, and the docs are refreshed). The
  three differ only in **what** they do to that software:
  - **`feature`** — **add** a new feature, integrating it into what is there.
  - **`modify`** — **change how an existing feature behaves**: the team locates it, edits the
    relevant files, and updates the affected tests and docs.
  - **`remove`** — **take an existing feature out**: the team deletes its code, tests, and
    docs (genuinely removing files that existed only for it, via a `<<<DELETE path >>>`
    directive in the file-block protocol) while keeping every other feature working.

```bash
# Change the project in place:
uv run software-team feature --into workspace --prompt "Add task priorities"
uv run software-team modify  --into workspace --prompt "Make priorities a 1–5 numeric scale"
uv run software-team remove  --into workspace --prompt "Remove the task priority feature"

# Or write the updated project to a new directory, leaving the original untouched:
uv run software-team feature --into workspace --spec examples/feature_priority.md --out workspace2
```

In `--dry-run`, `feature`/`modify` deterministically add a `priority` field (and a
`POST /tasks/{id}/priority` endpoint) to the demo Task API, and `remove` deletes that
feature's test file and trims the code back — with the remaining tests still passing — a
self-contained demonstration of changing software without breaking what exists.

### Garbage collection (`gc`) — scan for rot, then a Tech-Lead-gated clean-up

A fifth, maintenance command sweeps a whole existing project for accumulated problems and
fixes them under the Tech Lead's supervision:

```bash
uv run software-team gc --into workspace                 # clean up in place
uv run software-team gc --into workspace --out workspace-clean   # or write a cleaned copy
```

A deterministic, offline scanner (`src/software_team/skills/common/gc.py`, modelled on the
DevSecOps `security_audit`) flags three kinds of rot, each with a concrete fix:

- **Documentation inconsistency** — docs referencing files that no longer exist, leftover
  placeholder text, or source modules no documentation mentions.
- **Architecture violation** — a delivery framework imported into a pure-logic module, a
  "god" file, or a hardcoded secret.
- **Technical debt** — `TODO`/`FIXME` markers, empty exception handlers, leftover debug
  output, or a module with no test.

The findings (`docs/garbage_collection.md`) are **submitted to the Tech Lead**, who triages
them into a prioritised fix request (`docs/gc_request.md`); the Software Engineer applies the
fixes; and the same Tech Lead review (tests + linter) **verifies** the clean-up, looping within
the bug-fix cap. A clean project is reported and left untouched. The Tech Lead's tool-backed
`collect-garbage` skill drives the scan + triage.

### Debugging (`debug`) — run the tests, diagnose the root cause, fix until green

The build pipeline's bug-fix loop only fires when QA's *own* freshly written tests go red. A
sixth command is for when you **run the generated project yourself and hit a bug**: point the
team at the workspace and the 💻 Software Engineer runs the project's own test suite, diagnoses
the root cause (guided by an optional reported symptom), fixes it, and re-runs until the suite
is green — **without** re-doing planning, architecture, or deployment:

```bash
uv run software-team debug --into workspace                                  # fix in place
uv run software-team debug --into workspace --bug "empty titles are accepted" # with a symptom
uv run software-team debug --into workspace --out workspace-fixed             # or a fixed copy
```

When a reported symptom is not yet covered by a test, the engineer **first adds a test that
reproduces it**, then fixes the code so that test passes. The focused `test → diagnose → fix`
loop (`src/software_team/agents/debugger.py`, wired by `graph.build_debug_graph`) is bounded by
`SWTEAM_MAX_FIX_ITERS`, so it always terminates and **honestly reports anything still failing**
in `docs/debug_report.md` (the symptom, the root cause, the fix, and the final test status). In
`--dry-run` it deterministically repairs a planted regression in the demo Task API.

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
                         # (maintenance runs add garbage_collection.md / gc_request.md for gc,
                         #  and debug_report.md for debug)
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

**Observability (LangSmith)**

Tracing is opt-in and turn-key — set one flag and a key (`uv sync --extra langsmith`; the
package also ships with LangChain):

- `SWTEAM_LANGSMITH_TRACING` — `true` to trace the run (default `false`).
- `SWTEAM_LANGSMITH_API_KEY` — your LangSmith key.
- `SWTEAM_LANGSMITH_PROJECT` — the project traces land in (default `software-team`).
- `SWTEAM_LANGSMITH_ENDPOINT` — optional, for the EU or a self-hosted instance.

When on, `software_team/observability.py` exports the canonical `LANGSMITH_*` / legacy
`LANGCHAIN_*` variables the SDK reads, so the whole pipeline is traced with no per-call
code: the **graph run** (named `software-team:run:<label>`), **each character's streamed LLM
call** (named and tagged by role + phase, with role/mode/provider metadata), and the
**web-research** step (a child `tool` run). That populates the trace tree LangSmith's other
features build on — run inspection, monitoring/dashboards, datasets and offline evaluation,
and human feedback/annotation. The SDK's own `LANGSMITH_*`/`LANGCHAIN_*` env vars are also
honoured if you prefer to configure it that way. With tracing off, the helpers are cheap
no-ops, so behaviour (and `--dry-run`) is unchanged.

**Other**

- `SWTEAM_TEMPERATURE` — generation temperature (default 0.2).
- `SWTEAM_MAX_REVIEW_ITERS`, `SWTEAM_MAX_FIX_ITERS` — feedback-loop caps (default 2). The
  graph's `recursion_limit` is derived from these, so raising the caps never aborts a
  healthy run partway with a recursion error.
- `SWTEAM_MAX_FEATURES` — how many features the PM splits a spec into (default 12). The team
  builds and reviews one feature at a time, so this caps the build loop's length (and feeds
  the recursion budget). Raise it for large specs; lower it for coarser, fewer features.
- `SWTEAM_MAX_INTERVIEW_ROUNDS` — how many rounds the interactive `spec` interview may run
  (default 3); each round the agent can ask follow-up questions based on your answers.

## Design notes

- **Deterministic orchestration.** Local models are unreliable at multi-step tool
  calling, so the pipeline doesn't depend on it: each character makes a single
  structured generation, and Python *skill functions* persist artifacts and run
  commands. Tool-backed skills are still bound for the SWE/QA loop on capable models.
- **Async, streamed inference.** Every node is an `async` graph node and the graph runs via
  `ainvoke`; each character's single generation is awaited and **streamed** (`astream`, with
  an `ainvoke` fallback). Streaming keeps the run from *looking* idle on a slow local model —
  tokens render as they arrive — and turns the request timeout into a per-token *inactivity*
  deadline, so a slow-but-healthy generation no longer trips it. The blocking test-suite run
  is off-loaded to a worker thread so it never stalls the event loop.
- **Built to run faster.** The dominant cost on a local CPU-offloaded model is prompt
  prefill, so the pipeline keeps prompts lean and avoids repeat work: each node's web-search
  queries run **concurrently** (the research step takes as long as its slowest query, not
  their sum), results are **cached per run** (the review/bug-fix loops and the many shared
  "latest <stack> …" queries become cache hits — no duplicate round-trips), and the research
  block folded into a prompt is **size-bounded** so grounding never bloats prefill. On a
  cloud backend the async design also lets independent calls overlap.
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
- **Multi-component test gate.** QA (and the Tech Lead's review, and the `debug` loop) runs
  every testable component — the backend at the root and the UI under `frontend/` — each with
  its own detected test command, and the gate passes only if all suites that ran passed. On a
  live run it **installs each component's dependencies first** so the suite can actually run:
  the generated project's third-party imports (FastAPI, pydantic, React, …) are otherwise
  absent from the team's own environment, which would make every gate fail. Python deps go
  into an isolated per-workspace `.venv` (so the team's environment is never polluted, and
  the venv is reused across review passes), `frontend/` gets `npm install`, and compiled
  toolchains (Go, Rust, …) fetch their deps during the test run. A component whose **toolchain**
  is missing (exit 127) is still **skipped, never failed**, so the gate never blocks on an
  unavailable runtime. (In `--dry-run` nothing is installed — the offline canned project's
  unit tests are framework-free — so dry runs stay hermetic.)
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
  elicit.py      # interactive `spec` command: interview the user -> write a spec file
  project.py     # load already-developed software for an incremental `feature` run
  state.py       # TeamState blackboard (build vs. feature mode)
  llm.py         # multi-provider chat-model factory (ollama/openai/anthropic/google/llama_cpp) + dry-run stub
  observability.py # LangSmith wiring: enable tracing, name/tag runs, @traceable steps
  dryrun.py      # canned artifacts for --dry-run
  ui.py          # console reporting
  skills/        # SKILL.md library (loader, registry, common tools incl. web search + security-audit engine)
  triage.py      # deterministic spec classifier -> needs_frontend / needs_backend / needs_deployment
  agents/        # the characters (one file each, incl. frontend_engineer, debugger) + shared node helpers
  graph.py       # LangGraph StateGraph wiring the phases + loops (build, gc, debug graphs)
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
