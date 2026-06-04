---
name: analyze-edge-cases
description: Use when hunting for defects beyond the happy path, to enumerate edge cases and failure modes.
---

# Analyse edge cases

Use error guessing and experience to find defects beyond the happy path:

- Empty / whitespace / oversized inputs.
- Zero and negative numbers; null / missing fields.
- Duplicate and out-of-order operations; concurrency.
- **Idempotency** of repeated actions (double-complete, double-delete).

List each edge case and the **expected behaviour**.
