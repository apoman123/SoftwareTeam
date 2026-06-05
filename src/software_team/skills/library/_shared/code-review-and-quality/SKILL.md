---
name: code-review-and-quality
description: Reviews a change across five axes — correctness, readability, architecture, security, performance — before it merges. Use when reviewing code written by yourself, another agent, or a human.
---

# Code review and quality

Every change gets reviewed before merge. Evaluate it on five axes:

1. **Correctness** — does it do what it claims? Edge cases, error paths, and a test that
   would have caught the bug.
2. **Readability** — clear names, small functions, no surprises; a future reader
   understands it without the author.
3. **Architecture** — right layer, no leaked concerns, no needless coupling or duplication.
4. **Security** — untrusted input validated, no secrets, authorisation enforced.
5. **Performance** — no obvious N+1s or hot-path waste (but don't demand premature
   optimisation).

**The approval standard:** approve when the change *definitely improves overall code
health*, even if imperfect. Don't block because it isn't how you'd have written it. Flag
must-fix defects clearly and separate them from optional nits.

> **Source:** Adapted from the `code-review-and-quality` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/code-review-and-quality)
> (MIT licence, © 2025 Addy Osmani).
