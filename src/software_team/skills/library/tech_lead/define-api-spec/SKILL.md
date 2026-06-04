---
name: define-api-spec
description: Use when defining a service boundary, to write a contract-first OpenAPI specification with correct HTTP semantics.
---

# Define the API spec

Define the HTTP API as an **OpenAPI 3** contract inside a ```yaml block.

- Resource-oriented, consistent naming.
- Correct HTTP semantics: proper verbs and status codes (`201` created, `400` invalid,
  `404` missing, `204` no content), with explicit error shapes.
- Design the **contract first** so client and server can be built in parallel against it.
