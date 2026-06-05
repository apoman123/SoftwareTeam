---
name: karpathy-guidelines
description: Behavioural guidelines (after Andrej Karpathy) that reduce common LLM coding mistakes. Load first, before writing, reviewing, or refactoring any code, to avoid overcomplication, keep changes surgical, surface assumptions, and define verifiable success criteria.
---

# Karpathy guidelines

Apply these four principles to every coding task — load and follow them *before* any
other skill.

## 1. Think before coding

State your assumptions explicitly; if uncertain, ask. If multiple interpretations exist,
present them — don't silently pick one. If a simpler approach exists, say so and push
back when warranted. When something is unclear, stop and name what's confusing.

## 2. Simplicity first

Write the minimum code that solves the problem. No features beyond what was asked, no
abstractions for single-use code, no "flexibility" that wasn't requested, no error
handling for impossible scenarios. If 200 lines could be 50, rewrite it. Ask: "would a
senior engineer call this overcomplicated?" If yes, simplify.

## 3. Surgical changes

Touch only what you must. Don't "improve" adjacent code, comments, or formatting; don't
refactor what isn't broken; match the existing style even if you'd do it differently.
Remove only the imports/variables/functions *your* change made unused — leave
pre-existing dead code alone (mention it instead). Every changed line should trace
directly to the request.

## 4. Goal-driven execution

Turn the task into verifiable success criteria, then loop until they pass:

- "Add validation" → write tests for invalid inputs, then make them pass.
- "Fix the bug" → write a test that reproduces it, then make it pass.
- "Refactor X" → ensure the tests pass before and after.

For multi-step work, state a brief plan with a verification check per step. Strong,
testable criteria let you work independently; weak ones ("make it work") force constant
clarification.

> **Source:** Adapted from the `karpathy-guidelines` skill in
> [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/tree/main/skills/karpathy-guidelines)
> (MIT licence per its `SKILL.md`), itself derived from
> [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on
> common LLM coding pitfalls.
