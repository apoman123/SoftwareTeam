---
name: glab
description: Drives the GitLab workflow from the command line with the glab CLI — merge requests, issues, pipelines, and CI/CD variables. Use when creating or inspecting MRs, issues, or pipelines on GitLab.
---

# GitLab workflow with glab

Use the `glab` CLI for GitLab work; it auto-detects the host from the git remote (no
`GITLAB_HOST` needed inside a repo).

- **Merge requests:** `glab mr create --fill`, `glab mr view`, `glab mr diff`,
  `glab mr merge`. Open a small MR early; let CI run on it.
- **Issues:** `glab issue list`, `glab issue create`.
- **Pipelines:** `glab ci status`, `glab ci view`, `glab ci trace` to follow CI and read
  failing job logs. Pair with the `gitlab-pipeline-watch` skill to block until a result.
- **CI/CD variables:** set masked secrets with `glab variable set NAME --masked` rather
  than committing them.

Authenticate once with `glab auth login` (check with `glab auth status`).

> **Source:** Adapted from the `glab` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/glab)
> (MIT licence, © 2026 GitLab B.V.).
