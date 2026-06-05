# Vendored knowledge base — UI/UX Pro Max

The CSV files in this directory are the design-intelligence knowledge base of the
**UI UX Pro Max** skill, vendored here so the UI/UX Designer's design-system reasoning
engine (`software_team/skills/common/design_system.py`) can run fully offline.

- **Source:** [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- **Licence:** MIT (see `LICENSE` in this directory), © 2024 Next Level Builder.
- **Project site:** <https://uupm.cc>

## Files

| File | Contents (one row per item) |
|------|-----------------------------|
| `products.csv` | Product/industry types → recommended style, landing pattern, palette focus |
| `ui-reasoning.csv` | Per-product reasoning rules: pattern, style priority, colour/type mood, effects, anti-patterns |
| `styles.csv` | UI styles (glassmorphism, minimalism, brutalism, …) with effects, mode support, a11y |
| `colors.csv` | Industry colour palettes as semantic tokens (primary/accent/surface/…) |
| `typography.csv` | Font pairings with Google Fonts URL and CSS import |
| `landing.csv` | Landing-page section orders and CTA/conversion strategies |
| `charts.csv` | Chart-type recommendations with accessibility guidance |
| `ux-guidelines.csv` | UX best practices and anti-patterns with do/don't and severity |

The full upstream collection also ships additional domains (icons, Google Fonts catalogue,
per-stack guidelines, etc.); we vendor the subset the design-system generator needs plus the
highest-value supplementary search domains. Re-sync from upstream by copying the matching
files out of `src/ui-ux-pro-max/data/`.

Only the data is vendored. The search/ranking and design-system synthesis are a
dependency-free re-implementation in `design_system.py`, which cites the same source.
