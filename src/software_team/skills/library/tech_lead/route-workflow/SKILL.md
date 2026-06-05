---
name: route-workflow
description: Decides whether to loop work back or advance to the next phase within the iteration caps. Use when supervising the pipeline.
---

# Route the workflow (supervisor)

As supervisor, control flow between phases:

- Send work **back to the engineer** when review requests changes or tests fail.
- Otherwise **advance** to the next phase.
- Always respect the **iteration caps** so the pipeline terminates rather than looping forever.
