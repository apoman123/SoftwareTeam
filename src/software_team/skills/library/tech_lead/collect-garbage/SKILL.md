---
name: collect-garbage
description: Scans a whole project for rot and triages the findings into a prioritised fix request. Use during a garbage-collection (maintenance) run.
tool: garbage_scan
---

# Collect garbage

As the supervisor, you receive the automated garbage-collection scan (`garbage_scan`) and
turn it into work. The scan flags three kinds of rot, each with a suggested fix:

- **Documentation inconsistency** — docs that reference files that no longer exist, leftover
  placeholder text, or source modules no documentation mentions.
- **Architecture violation** — a delivery framework imported into a pure-logic module, a
  "god" file, or a hardcoded secret.
- **Technical debt** — `TODO`/`FIXME` markers, empty exception handlers, debug output, or a
  module with no test.

Triage the findings into a **prioritised fix request** for the engineer:

- Order by risk and impact; fix architecture violations and secrets before cosmetic debt.
- Group related findings so one change resolves several.
- For each item, state concretely what to change and what "done" looks like.
- The clean-up must **not change intended behaviour** — keep every test passing. Verify the
  fixes by re-running the tests and the linter before accepting them.
