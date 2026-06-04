---
name: fix-bug
description: Use when tests fail or an incident is reported, to find the root cause and patch it minimally.
---

# Fix the bug

When tests fail, read the pytest output and find the **root cause** before changing code —
fix the cause, not the symptom.

- Re-emit **only the files you change**.
- Keep the change minimal and covered by a test.

This embodies "you build it, you run it": the author is first responder for their service.
