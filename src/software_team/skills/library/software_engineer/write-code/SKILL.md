---
name: write-code
description: Use when implementing a feature, to write clean, idiomatic, SOLID code and persist it to the workspace.
tool: write_source_file
---

# Write clean code

Write clean, idiomatic code and save each file to the workspace.

- Follow **SOLID** — especially single-responsibility and dependency inversion (depend on
  abstractions; inject IO).
- Small functions, clear names; validate inputs at the boundary; handle errors explicitly.
- Avoid premature abstraction (**YAGNI**) and duplication (**DRY**).

Emit files using the file-block protocol: `<<<FILE path >>> ... <<<END>>>`.
