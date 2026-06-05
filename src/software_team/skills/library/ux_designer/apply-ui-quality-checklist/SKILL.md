---
name: apply-ui-quality-checklist
description: Reviews a UI against a priority-ordered quality checklist (accessibility, touch, performance, style, layout, typography, animation, forms, navigation, charts). Use when finalising a design or reviewing UI for professional polish.
---

# Apply the UI quality checklist

Pass the design through these categories in priority order — fix higher categories first.
They encode the recurring issues that make a UI feel unprofessional.

1. **Accessibility (critical).** Contrast ≥ 4.5:1 (3:1 large text), visible focus rings,
   alt text, labelled icon-only buttons, full keyboard nav, never colour alone for meaning,
   respect `prefers-reduced-motion`.
2. **Touch & interaction (critical).** Targets ≥ 44×44px with ≥ 8px spacing; tap/click for
   primary actions (not hover-only); disable buttons during async work; visible press feedback.
3. **Performance (high).** Reserve space for async content and images (low CLS); lazy-load
   below-the-fold; skeletons for waits > 1s.
4. **Style (high).** One consistent style and icon set; SVG icons, never emoji; effects
   (shadow/blur/radius) match the chosen style; one primary CTA per screen.
5. **Layout & responsive (high).** Mobile-first; systematic breakpoints (375/768/1024/1440);
   no horizontal scroll; consistent spacing scale; never disable zoom.
6. **Typography & colour (medium).** Base 16px, line-height 1.5; semantic colour tokens, not
   raw hex; design light and dark variants together.
7. **Animation (medium).** 150–300ms; animate transform/opacity only; motion conveys meaning;
   honour reduced-motion.
8. **Forms & feedback (medium).** Visible labels (not placeholder-only); errors beside the
   field with a recovery path; validate on blur; confirm destructive actions.
9. **Navigation (high).** Predictable back; highlight the active location; bottom nav ≤ 5;
   key screens reachable by URL/deep link.
10. **Charts & data (low).** Match chart type to data; legends and tooltips; don't rely on
    colour alone; provide a table fallback.

Flag each violation with the category and the concrete fix.

> **Source:** Distilled from the UX rule set in
> [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
> (MIT licence, © 2024 Next Level Builder).
