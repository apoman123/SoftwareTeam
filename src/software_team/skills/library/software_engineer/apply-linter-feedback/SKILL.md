---
name: apply-linter-feedback
description: Turns linter diagnostics into real fixes. Use when the review hands back linter findings on the generated code.
tool: run_lint
---

# Apply linter feedback

The Tech Lead runs the project's linter during review and returns its diagnostics with
constructive fix suggestions. Treat each finding as an actionable change, not noise.

- Fix the **root cause**, not the symptom — don't silence a warning with a blanket ignore.
- Group findings by file and address them together with the feature work in the same pass.
- Keep changes behaviour-preserving: a lint fix must not break a passing test.
- Re-run the linter (`run_lint`) after fixing to confirm the diagnostics are gone.
- Linting is **advisory** — prioritise correctness and the acceptance criteria first, then
  clear the lint findings so the code stays clean and idiomatic for the project's stack.
