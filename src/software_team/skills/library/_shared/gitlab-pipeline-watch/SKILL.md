---
name: gitlab-pipeline-watch
description: Watches a GitLab MR pipeline until it reaches an actionable state (success, failure, merge) and reacts. Use when you need CI results before the next step — e.g. fix-on-red or promote-on-green loops.
---

# Watch GitLab pipelines

Block until a GitLab MR pipeline reaches an **actionable** state, then react — the
event-loop counterpart to firing a pipeline and walking away.

- **Wait for a result**, don't poll blindly: use `glab ci status`/`glab ci view` (or the
  pipelines API) to watch the running pipeline for the current ref.
- **On success:** proceed — promote the artifact, merge the MR, or move to the next stage.
- **On failure:** pull the failing job's log (`glab ci trace`), diagnose the root cause,
  push a fix, and watch again. This is the loop that closes the CI feedback cycle.
- **Bound the wait** with a timeout so an indefinitely-stuck pipeline never blocks forever.

Prerequisite: `glab` installed and authenticated (`glab auth status`). See the `glab`
skill for the underlying commands.

> **Source:** Adapted from the `gitlab-pipeline-watch` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/gitlab-pipeline-watch)
> (MIT licence, © 2026 GitLab B.V.).
