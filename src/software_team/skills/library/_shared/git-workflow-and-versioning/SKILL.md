---
name: git-workflow-and-versioning
description: Structures git for reviewable, reversible change — trunk-based, short-lived branches, atomic commits. Use when committing, branching, or organising work into a small, focused change set.
---

# Git workflow and versioning

Treat commits as save points, branches as sandboxes, and history as documentation.

- **Trunk-based.** Keep `main` always deployable. Work on short-lived feature branches that
  merge back within 1–3 days. Long-lived branches diverge, breed conflicts, and delay
  integration — DORA research links trunk-based development to high-performing teams.
- **Atomic commits.** One logical change per commit; it should build and pass tests on its
  own so it can be reverted or cherry-picked cleanly.
- **Small PRs.** Keep a change set small and single-purpose — it reviews faster and
  regresses less. Split unrelated changes.
- **Never rewrite shared history.** Rebase only your own un-pushed work; never force-push a
  shared branch.
- **Don't commit secrets or generated artifacts**; keep them in ignore files.

> **Source:** Adapted from the `git-workflow-and-versioning` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/git-workflow-and-versioning)
> (MIT licence, © 2025 Addy Osmani).
