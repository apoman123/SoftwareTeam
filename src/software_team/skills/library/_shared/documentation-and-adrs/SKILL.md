---
name: documentation-and-adrs
description: Records the why behind significant technical decisions as Architecture Decision Records. Use when making an architectural decision, choosing between approaches, or changing a public API.
---

# Documentation and ADRs

Document decisions, not just code. Code shows *what* was built; the highest-value
documentation captures *why it was built this way* and *what alternatives were considered*
— the context future humans and agents need.

Write an **ADR** for each significant decision, kept in `docs/adr/NNNN-title.md`:

- **Title & status** — accepted / superseded / deprecated.
- **Context** — the forces and constraints that make a decision necessary.
- **Decision** — what was chosen, stated plainly.
- **Consequences** — the trade-offs accepted, good and bad, and what it rules out.
- **Alternatives considered** — what else was weighed and why it lost.

Keep ADRs short and immutable: supersede with a new record rather than rewriting history.
Don't document obvious code or throwaway prototypes.

> **Source:** Adapted from the `documentation-and-adrs` skill in
> [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/main/skills/documentation-and-adrs)
> (MIT licence, © 2025 Addy Osmani).
