---
name: define-acceptance-criteria
description: Use when a story needs a testable definition of done, to write Gherkin Given/When/Then acceptance criteria covering happy and failure paths.
---

# Define acceptance criteria

For each story, write the **definition of done** as verifiable conditions.

Prefer the **Gherkin** format inside a ```gherkin block:

```gherkin
Scenario: <intent>
  Given <precondition>
  When <action>
  Then <observable outcome>
```

- Cover the **happy path** and the **failure paths** (invalid input, missing resource, unauthorised).
- Make each criterion testable and unambiguous so QA can trace a test back to it.
