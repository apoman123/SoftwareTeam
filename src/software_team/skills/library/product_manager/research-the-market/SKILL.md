---
name: research-the-market
description: Searches the web for current facts before a spec is written or revised — today's stable technology versions and recommended stacks, domain/regulatory considerations, and comparable existing products — so the spec's Technology section and assumptions reflect reality rather than a model's stale training data. Use when generating or revising a spec.
tool: web_search
---

# Research the market

A local model's knowledge has a cut-off, so anything version-specific or fast-moving it
"remembers" may already be wrong. Before committing the spec, **look it up**. Ground the
document in what is true today, not what was true at training time.

Search the web for the few facts that most change the spec, then fold the findings in:

1. **Technology** — If the stakeholder named a stack, confirm its *current* stable
   release, support status, and any notable recent change, so the `## Technology` section
   is accurate. If they stated no preference, research the technologies teams actually
   reach for today for this kind of product, and record those as candidate options for the
   Tech Lead (still deferring the final choice).
2. **Domain & compliance** — Surface regulations, standards, or platform rules the product
   must respect (privacy, payments, accessibility, data residency…). These become concrete
   non-functional requirements or explicit open questions, not afterthoughts.
3. **Comparable products** — Skim how similar tools frame the problem and what users expect
   as table stakes, to sharpen the use cases and scope.

Keep it lean and honest: a couple of high-signal queries, not a literature review. Prefer
the searched facts over recollection where they disagree, cite a source inline when a claim
rests on one, and never let a search result invent a requirement the stakeholder did not
ask for — if research only *raises* a question, record it under `## Open questions`. When
the web is unavailable the search simply returns nothing; carry on and write the spec.
