---
name: write-e2e-tests
description: Writes automated end-to-end / API tests that respect the test pyramid. Use when validating user journeys.
tool: write_source_file
---

# Write end-to-end tests

Automate end-to-end / API tests with the project's standard test framework and save them
to the workspace.

- Respect the **test pyramid**: many fast unit tests, fewer integration tests, a thin top
  layer of E2E tests for the **critical journeys**.
- Make tests **deterministic and independent**.
- Cover the happy path plus invalid-input and missing-resource cases.
- Use the stack's idiomatic API-test client (e.g. FastAPI's `TestClient` for Python —
  guard the import with `pytest.importorskip('fastapi')` — or Supertest for Node.js), and
  make the suite runnable with that stack's standard test command.
