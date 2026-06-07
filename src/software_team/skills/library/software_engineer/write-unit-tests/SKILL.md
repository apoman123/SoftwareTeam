---
name: write-unit-tests
description: Writes fast, isolated unit tests that form the base of the test pyramid. Use when implementing logic.
---

# Write unit tests

Write fast, isolated unit tests for the business logic with the project's standard test
framework (e.g. pytest for Python, Jest/Vitest for Node.js, `go test` for Go).

- Follow **Arrange-Act-Assert**, one behaviour per test.
- Cover **error paths** as well as the happy path.
- Test the **framework-free core directly** so tests stay fast and stable (the broad base
  of the test pyramid).
