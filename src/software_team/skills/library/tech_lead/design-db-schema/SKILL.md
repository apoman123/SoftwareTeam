---
name: design-db-schema
description: Designs a SQL schema that enforces the domain's invariants. Use when the system needs persistence.
---

# Design the database schema

Design the persistence schema as **SQL DDL** inside a ```sql block.

- Pick keys, required columns, types and constraints that enforce the domain's invariants.
- **Normalise** unless a measured read pattern justifies denormalisation.
- Note indexes for the expected query paths.
