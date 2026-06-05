---
name: design-test-cases
description: Derives traceable test cases using black-box design techniques. Use when acceptance criteria are ready.
---

# Design test cases

Derive traceable test cases (`TC-n → US-n`) from the acceptance criteria using black-box techniques:

- **Equivalence partitioning** — one representative per class of inputs that behave the same.
- **Boundary-value analysis** — test the edges of each partition, valid and invalid (defects cluster at boundaries).
- **Decision tables** — for combinations of conditions.

Aim for **high coverage with the fewest cases**.
