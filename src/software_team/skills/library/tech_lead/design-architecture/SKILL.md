---
name: design-architecture
description: Describes the system structure with the C4 model and a mermaid diagram, optimising for testability. Use when designing how the system fits together.
---

# Design the architecture (C4 model)

Describe the architecture top-down with the **C4 model**:

1. **Context** — the system, its users and external systems.
2. **Container** — deployable/runnable units and how they communicate.
3. **Component** — the key parts inside a container.

Include at least one **mermaid** diagram. Separate **pure business logic from framework/IO**
so the core is unit-testable. Note how the design supports scalability and high availability.
