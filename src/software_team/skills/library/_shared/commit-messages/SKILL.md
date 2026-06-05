---
name: commit-messages
description: Writes clear, structured commit messages — imperative subject, body that explains why, one atomic change per commit. Use when creating a git commit or about to run git commit.
---

# Writing commit messages

A subject line completes the sentence **"If applied, this commit will _<subject>_"**.

- **Detect the project convention first.** Check `git log --oneline -20` and any repo
  guidance, and match the existing style (this project uses Conventional Commits —
  `feat:`, `fix:`, `refactor:`, `test:`).
- **Subject:** imperative mood, capitalised, no trailing period, ≤ 50 characters.
- **Body (when needed):** wrap at 72 characters; explain **why**, not what — the diff
  already shows what. Reference issues/MRs.
- **Atomic.** One logical change per commit so history is readable and releases are
  automatable.

> **Source:** Adapted from the `commit-messages` skill in
> [gitlab-org/ai/skills](https://gitlab.com/gitlab-org/ai/skills/-/tree/main/skills/commit-messages)
> (MIT licence, © 2026 GitLab B.V.).
