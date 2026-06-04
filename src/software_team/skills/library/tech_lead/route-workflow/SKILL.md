---
name: route-workflow
description: Use when supervising the pipeline, to decide whether to loop work back or advance to the next phase within iteration caps.
---

# Route the workflow (supervisor)

As supervisor, control flow between phases:

- Send work **back to the engineer** when review requests changes or tests fail.
- Otherwise **advance** to the next phase.
- Always respect the **iteration caps** so the pipeline terminates rather than looping forever.
