# Feature: Task priorities

## Background
The Task API (built from `sample_spec.md`) already lets a user create, list, view,
complete, and delete tasks. Users now want to flag how urgent a task is so they can focus
on what matters first. This is an **incremental feature** added to the existing service —
feed it to `software-team feature --into <workspace>`.

## Use cases
1. **Set a priority on create** — when adding a task the user may include a priority of
   `low`, `medium`, or `high`. If omitted it defaults to `medium`.
2. **Change a priority** — the user can update the priority of an existing task.
3. **See the priority** — every task returned by the API includes its current priority.

## Acceptance criteria
- An invalid priority (anything other than `low`/`medium`/`high`) is rejected with a 400.
- Updating the priority of an unknown task id returns 404.
- Existing behaviour (create/list/view/complete/delete) is unchanged and still passes its
  tests.

## Out of scope (for now)
- Sorting or filtering the task list by priority.
- Per-user default priorities.
