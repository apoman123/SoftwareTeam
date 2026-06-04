---
name: scaffold-project
description: Use when starting implementation, to lay out a clean project structure that keeps business logic testable.
---

# Scaffold the project

Lay out a clear structure:

- Keep **pure business logic in a framework-free module**.
- Put the **web/IO adapter** in a thin, separate layer.
- Place tests in their own package.
- Include a dependency manifest (e.g. `requirements.txt`).
