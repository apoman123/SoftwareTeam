---
name: follow-google-style
description: Write all code to the Google style guide for its language. Use whenever authoring source, tests, or infrastructure code so naming, imports, docstrings, and formatting stay consistent and reviewable. Load after karpathy-guidelines.
---

# Follow the Google style guide

Write every file to the [Google style guide](https://google.github.io/styleguide/) for
its language. When the project's own config (e.g. a formatter's line length) differs,
match the project.

## Python — [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

- **Naming:** `snake_case` for functions, variables, and modules; `CapWords` for classes;
  `UPPER_SNAKE_CASE` for constants. Names are descriptive — no cryptic abbreviations.
- **Docstrings:** every module, public function, and class gets a Google-style
  docstring — a one-line summary, then `Args:`, `Returns:`, and `Raises:` sections where
  applicable.
- **Imports:** grouped and ordered — standard library, then third party, then local —
  each group sorted, no wildcard (`from x import *`) imports.
- **Structure:** annotate public signatures with types; keep functions small and
  single-responsibility; validate inputs at the boundary; handle errors explicitly and
  never use a bare `except`.

## Other languages

- **Shell:** [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
  — start with `set -euo pipefail`, use lowercase function names, and quote expansions.
- **YAML / Dockerfile / HCL** (CI workflows, Kubernetes, Terraform): 2-space indentation
  and no tabs, pin versions, one declaration per line, and keep files small and ordered.

Lint and format the code before declaring the work done.
