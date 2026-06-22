---
name: actions-workflow-watch
description: Watches a GitHub Actions workflow run until it reaches an actionable state (success, failure) and reacts. Use when you need CI results before the next step — e.g. fix-on-red or promote-on-green loops.
---

# Watch GitHub Actions runs

Block until a GitHub Actions workflow run reaches an **actionable** state, then react — the
event-loop counterpart to firing a workflow and walking away.

- **Wait for a result**, don't poll blindly: use `gh run watch` (or `gh run list`/
  `gh run view`, or the Actions API) to watch the running workflow for the current ref/PR.
- **On success:** proceed — promote the artifact, merge the PR, or move to the next stage.
- **On failure:** pull the failing job's log (`gh run view --log-failed`), diagnose the
  root cause, push a fix, and watch again. This is the loop that closes the CI feedback cycle.
- **Bound the wait** with a timeout so an indefinitely-stuck run never blocks forever.

Prerequisite: `gh` installed and authenticated (`gh auth status`). See the `gh` skill for
the underlying commands.

> **Source:** Retargeted from the `gitlab-pipeline-watch` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/gitlab-pipeline-watch)
> (MIT licence, © 2026 GitLab B.V.) — adapted from GitLab pipelines to GitHub Actions runs.
