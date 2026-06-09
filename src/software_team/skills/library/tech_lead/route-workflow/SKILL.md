---
name: route-workflow
description: Decides whether to loop work back or advance to the next phase within the iteration caps. Use when supervising the pipeline.
---

# Route the workflow (supervisor)

As supervisor, control flow between phases:

- Build and review **one feature at a time**: advance to the next feature only once the
  current one is approved (tests pass and it meets its acceptance criteria).
- Send work **back to the engineer** when review requests changes or tests fail.
- Otherwise **advance** — to the next feature, then the frontend, then deploy/test.
- Always respect the **iteration caps** so the pipeline terminates rather than looping forever.
