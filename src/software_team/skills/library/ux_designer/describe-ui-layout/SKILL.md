---
name: describe-ui-layout
description: Describes each key screen's layout, content hierarchy, and primary action in words for engineering. Use when communicating the UI to the Tech Lead without drawing it.
---

# Describe the UI layout

Describe each key screen in prose and bullets so the Tech Lead can design and build it
from your words alone. **Never draw** — no ASCII art, wireframes, diagrams, or images.

- Name the screen and its purpose, then walk its layout in reading order (top-to-bottom,
  and left-to-right where it matters): header, the main content regions, and any
  footer/navigation.
- State the content hierarchy explicitly — what is most prominent, what is secondary —
  and name the **single primary action** per screen.
- Describe responsive behaviour in words: how the layout reflows on mobile versus desktop.
- For an API/backend product, describe a minimal **reference client** (the calls it makes
  and what it shows) instead of screens.
