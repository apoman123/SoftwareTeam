---
name: mr-review
description: Reviews a GitLab merge request — reads the diff, analyses changes against a rubric, presents findings, and optionally posts comments. Use when reviewing an MR on GitLab.
---

# MR review

Review a GitLab merge request end to end.

1. **Gather context** — the MR description, target branch, linked issues, and the full
   diff (`glab mr diff`). Understand the *intent* before judging the code.
2. **Analyse against a rubric** — correctness, tests, readability, security, and scope
   (does the diff match what the MR claims, with nothing unrelated smuggled in?).
3. **Present findings** — lead with a short verdict (approve / changes requested), then
   group findings as **must-fix** vs **optional**, each tied to a specific file and line.
4. **Optionally post comments** — inline on the MR via `glab`, kept specific and
   actionable, so the author can address them directly.

Be constructive: explain the *why* behind each request so the author can push back.

> **Source:** Adapted from the `mr-review` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/mr-review)
> (MIT licence, © 2026 GitLab B.V.).
