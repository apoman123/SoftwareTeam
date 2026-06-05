---
name: write-readme
description: Writes the repository README so other engineers and users can set up, run, and call the project. Use once a feature is built.
---

# Write the repository README

Write the project's front-door README — for other engineers and your future self:

- **Overview** — what the project does, in a sentence or two.
- **Prerequisites** — the language/runtime versions and tools required.
- **Setup** — create an isolated environment and install pinned dependencies (e.g. `pip install -r requirements.txt`).
- **Run** — the exact command that starts the service (e.g. `uvicorn app.main:app --reload`).
- **Usage / API** — the key endpoints with copy-pasteable `curl` examples.

Keep every command copy-pasteable, and document the **how**, not just that a thing exists.
