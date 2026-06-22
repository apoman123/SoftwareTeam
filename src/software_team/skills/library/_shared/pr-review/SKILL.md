---
name: pr-review
description: Reviews a GitHub pull request — reads the diff, analyses changes against a rubric, presents findings, and optionally posts comments. Use when reviewing a PR on GitHub.
---

# PR review

Review a GitHub pull request end to end.

1. **Gather context** — the PR description, target branch, linked issues, and the full
   diff (`gh pr diff`). Understand the *intent* before judging the code.
2. **Analyse against a rubric** — correctness, tests, readability, security, and scope
   (does the diff match what the PR claims, with nothing unrelated smuggled in?).
3. **Present findings** — lead with a short verdict (approve / changes requested), then
   group findings as **must-fix** vs **optional**, each tied to a specific file and line.
4. **Optionally post comments** — inline on the PR via `gh`, kept specific and actionable,
   so the author can address them directly.

Be constructive: explain the *why* behind each request so the author can push back.

> **Source:** Retargeted from the `mr-review` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/mr-review)
> (MIT licence, © 2026 GitLab B.V.) — adapted from GitLab merge requests to GitHub pull
> requests.
