---
name: review-code
description: Use when an engineer submits code, to review it as the quality gate and approve or request changes.
---

# Review code

Review for correctness, **separation of concerns**, input validation, error handling,
naming, and **test coverage of both happy and failure paths**.

- Be specific and actionable; distinguish **blocking defects** from nits.
- Approve unless there is a real defect — do not block on style alone.
- Begin the verdict with exactly one line: `REVIEW_STATUS: approve` or `REVIEW_STATUS: changes`.
