---
name: elicit-requirements
description: Runs a structured stakeholder interview that turns a rough one-line idea into a complete, testable spec — drawing out the real problem, the users, the scope and edges, functional and non-functional needs, and the target technology stack. Use when generating a spec file from a prompt, before any requirements, design, or build work.
---

# Elicit requirements

Turn a vague intent into a delivery contract. Requirements are contracts, not meeting
minutes: every line must be testable, traceable, and unambiguous before it reaches
engineering. Separate **problem** from **solution** — capture *what* the user needs, not
*how* to build it — and never invent details the stakeholder did not give you.

Work the interview in phases:

1. **Discover** — Find the *actual* problem, not the proposed solution. Establish the
   business goal and the measurable outcome the stakeholder wants, who the users/personas
   are, and the single most important job to be done.
2. **Interrogate** — Ask focused, Socratic questions across: **scope** (must-have vs
   later), **edges** (invalid input, empty/error/limit states), **success & failure**
   (what "done" and "broken" look like), **dependencies** (external systems, data, auth),
   **constraints** (deadlines, budget, compliance, scale/latency targets), and the
   **technology** — the language, framework, runtime, datastore, and deployment target the
   stakeholder wants (treat a stated stack as binding; if they have no preference, record
   that so the Tech Lead chooses and justifies it).
3. **Structure** — Write it up as a spec: a one-paragraph background/goal, concrete
   **use cases** (numbered, one per core capability), **functional requirements**,
   **non-functional requirements** (performance, security, scale, reliability), the
   **technology / stack** as its own section, and an explicit **out of scope** list.
4. **Validate** — Read each requirement back in plain language; anything the stakeholder
   did not confirm becomes an explicit **open question**, never a silent assumption.
5. **Gate** — Before finishing, check the spec is *ready*: the goal is measurable, every
   use case is independently testable, edge cases are documented, the stack is stated (or
   explicitly deferred), and nothing ambiguous is left unflagged.

Keep questions few and high-signal — prefer 3–6 sharp questions over a long form. Output a
clean markdown spec with `## Background`, `## Use cases`, `## Functional requirements`,
`## Non-functional requirements`, `## Technology`, `## Out of scope`, and (if any)
`## Open questions`.

_Adapted, with thanks, from the `requirements-elicitation` skill in
[andreaswasita/copilot-agents-dojo](https://github.com/andreaswasita/copilot-agents-dojo)
(MIT, © 2026 Andreas Wasita)._
