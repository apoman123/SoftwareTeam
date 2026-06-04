# Spec: Task API

## Background
We need a small backend service that lets a single user manage a personal task list.
It will be consumed by a thin CLI/web client later, so an HTTP/JSON API is the priority.

## Use cases
1. **Add a task** — the user provides a title and gets back a task with a unique id and
   a `done` flag defaulting to false. Empty/whitespace titles must be rejected.
2. **List tasks** — the user can retrieve all tasks.
3. **View a task** — the user can fetch a single task by id; unknown ids return not-found.
4. **Complete a task** — the user can mark a task done.
5. **Delete a task** — the user can remove a task; unknown ids return not-found.

## Non-functional requirements
- Simple to run locally and to containerise.
- Reasonable latency under light load (p95 < 200ms).
- Clear errors (400 for bad input, 404 for missing resources).

## Out of scope (for now)
- Authentication / multiple users.
- Durable persistence (in-memory storage is acceptable for v1).
