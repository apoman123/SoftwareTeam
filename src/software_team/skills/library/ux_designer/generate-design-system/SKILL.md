---
name: generate-design-system
description: Recommends a complete design system — page pattern, visual style, semantic colour tokens, font pairing, key effects, and anti-patterns — for the product type. Use first, before designing flows, wireframes, or any UI.
tool: design_system
---

# Generate a design system

Before sketching screens, ground the design in a concrete system so colours, typography,
style and layout are deliberate rather than ad hoc. The `design_system` tool searches a
knowledge base of product types, styles, palettes and font pairings and applies
per-industry reasoning rules to return a tailored recommendation.

- **Run it first** with a short product description that names the product/industry and
  any tone keywords, e.g. `"fintech banking trust secure"` or `"beauty spa wellness booking"`.
  The deterministic pipeline already does this and folds the result into your brief.
- **Design *to* the system it returns:** use its **page pattern** (section order, CTA
  placement), the named **visual style**, the **semantic colour tokens** (reference
  `--color-primary`, `--color-accent`, … — never raw hex in components), and the **font
  pairing** (heading/body).
- **Honour the anti-patterns** it lists for the industry (e.g. avoid AI purple/pink
  gradients for banking). Treat them as hard constraints.
- For an API/backend product, still apply the palette, typography and the listed states
  to the small reference client so it looks intentional.

Deep-dive any single dimension with the `ui_ux_search` tool (domains: `product`, `style`,
`color`, `typography`, `landing`, `chart`, `ux`) when you need more options than the
recommendation gives.

> **Source:** Reasoning model and knowledge base adapted from
> [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
> (MIT licence, © 2024 Next Level Builder). See `skills/common/uiux_data/ATTRIBUTION.md`.
