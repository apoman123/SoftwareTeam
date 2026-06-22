---
name: gh
description: Drives the GitHub workflow from the command line with the gh CLI — pull requests, issues, Actions runs, and secrets. Use when creating or inspecting PRs, issues, or workflow runs on GitHub.
---

# GitHub workflow with gh

Use the `gh` CLI for GitHub work; it auto-detects the repo from the git remote (no host
config needed inside a repo).

- **Pull requests:** `gh pr create --fill`, `gh pr view`, `gh pr diff`, `gh pr merge`.
  Open a small PR early; let CI run on it.
- **Issues:** `gh issue list`, `gh issue create`.
- **Actions:** `gh run list`, `gh run view`, `gh run watch`, and `gh run view --log-failed`
  to follow a workflow run and read failing job logs. Pair with the
  `actions-workflow-watch` skill to block until a result.
- **Secrets:** set encrypted secrets with `gh secret set NAME` (repo or `--env <name>`)
  rather than committing them.

Authenticate once with `gh auth login` (check with `gh auth status`).

> **Source:** Retargeted from the `glab` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/glab)
> (MIT licence, © 2026 GitLab B.V.) — adapted from the GitLab CLI (`glab`) to the GitHub
> CLI (`gh`).
