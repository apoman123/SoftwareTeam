---
name: write-unit-tests
description: Writes fast, isolated, behaviour-focused unit tests — including correct use of stubs and mocks and the isolation principle — that form the base of the test pyramid. Use when implementing logic.
---

# Write unit tests

> Adapted from [**clear-solutions/unit-tests-skills**](https://github.com/clear-solutions/unit-tests-skills)
> (see the References section for the full origin and further reading).

Write fast, isolated unit tests for the business logic with the project's standard test
framework (e.g. pytest for Python, Jest/Vitest for Node.js, JUnit 5 + Mockito + AssertJ for
Java, `go test` for Go).

## Workflow

1. **Analyse the target and its context** — read the code under test, follow its imports
   (DTOs, entities, enums, collaborators), and read any existing tests so you extend coverage
   instead of duplicating it.
2. **Enumerate test cases first** — list the scenarios as `Given / When / Then` before writing
   code, covering every branch (success, validation, error/exception paths, edge cases).
3. **Write the tests** — one scenario per test, matching the project's existing conventions.
4. **Run them and fix failures** — the suite must compile and pass before you hand it off.

## Test isolation (the core principle)

A unit test exercises **one unit** (a function / class / module) in isolation from everything
it collaborates with, so a failure points at exactly that unit and the suite stays fast and
deterministic.

- **No real I/O or infrastructure.** No network, filesystem, database, clock, randomness, or
  framework/container startup. Replace each such collaborator with a test double. Spinning up
  the web framework, a DI container (e.g. Spring), or a real database makes it an *integration*
  test, not a unit test — keep those separate and few.
- **No shared state between tests.** Each test arranges its own data and must not depend on
  another test's side effects or on execution order; construct a fresh subject under test per
  test rather than relying on suite-level mutable state.
- **Deterministic.** The same inputs give the same result every run. Inject the clock, random
  source, and id generator so time/randomness are fixed — never assert against `now()`.
- **One scenario per test** (see *How to write each test*).

## Test doubles: stubs vs mocks

A *test double* stands in for a real collaborator so the unit runs in isolation. Pick the
right kind:

- **Stub** — feeds the unit **canned inputs** so you can drive a code path, then you assert on
  the unit's **return value / resulting state** (*state verification*). Use stubs for the
  unit's **queries** — data it reads: repository fetches, config lookups, a clock returning a
  fixed time.
  - Python (`unittest.mock`): `repo.get.return_value = User("123", "John")`
  - Java (Mockito): `when(repo.findById("123")).thenReturn(Optional.of(user))`
  - JS (Jest): `repo.get.mockReturnValue(user)`
- **Mock** — a double whose **interactions you verify**: that the unit called a collaborator
  with the right arguments (*behaviour verification*). Use mocks for the unit's **commands** —
  effects it causes on the outside world: sending an email, publishing an event, persisting a
  write.
  - Python: `email.send.assert_called_once_with(to="john@test.com")`
  - Java: `verify(email).send(captor.capture())`
  - JS: `expect(email.send).toHaveBeenCalledWith(expect.objectContaining({ to: "john@test.com" }))`

**Rule of thumb: stub queries, verify commands.** Most tests need only a stub (arrange inputs,
assert the output); reach for a verifying mock only when the outbound effect *is* the behaviour
and cannot be observed through the return value or state.

### When to use a double — and when NOT to

Replace with a stub/mock:
- repositories / DAOs / databases, external service or API clients, message producers, caches,
- the clock, randomness / uuid, and any other I/O or non-deterministic dependency.

Use the **real** object (do **not** double these):
- the **system under test** itself — never mock what you are testing;
- **plain value objects / DTOs / entities** and pure functions — construct them for real.
  Mocking a simple value object adds noise without buying isolation, and is a smell.

### Use doubles well (so tests stay resilient)

- **Don't over-mock.** Stub only the calls the scenario actually needs, and verify only the
  interactions that *are* the behaviour under test. Over-specified interactions make tests
  brittle — they break on harmless refactors.
- **Assert real arguments, not wildcards.** Capture the actual argument and assert the fields
  that matter (Java `ArgumentCaptor`; Python `mock.call_args`; Jest `mock.calls`) rather than
  matching `any()`. Reserve `any()` / `anyString()` for values irrelevant to the scenario
  (e.g. asserting a call count).
- **Prefer state over interaction.** When an effect is observable through the return value or
  resulting state, assert that instead of verifying the call — it survives refactoring.

## What to test (INCLUDE)

- All code branches: happy path, validation logic, error/exception paths, edge and boundary
  cases.
- The **public API / observable behaviour**, not implementation details.
- Only the arguments and effects relevant to the behaviour under test.

## What not to test (EXCLUDE)

- Private-method internals (cover them through the public methods that call them).
- Trivial constructors/getters with no logic.
- Paths already covered by existing tests.

## How to write each test

- **One behaviour per test**, structured as **Arrange-Act-Assert** (a.k.a. Given-When-Then);
  prefix variables with `actual`/`expected` so the assertion's intent is obvious. Multiple
  assertions are fine only when they verify the *same* behaviour (e.g. several fields of one
  created object). A test name containing "and", or a second Act section, means split it.
- Name tests for the behaviour: **`{method}_{givenState}_{expectedOutcome}`**, e.g.
  `calculateTotal_emptyList_throwsIllegalArgumentException`.
- **No logic in tests** — no loops, conditionals, or computed expected values; prefer literal
  values and small data builders/helpers so the cause→effect is explicit.
- Aim for the four qualities of a good test: **Clarity** (understandable in ~10 seconds),
  **Completeness** (all relevant data visible in the test, not hidden in suite-level setup),
  **Conciseness** (irrelevant setup pushed into helpers/builders), and **Resilience** (only
  fails when the tested behaviour breaks, never on an unrelated refactor).

## References

- clear-solutions/unit-tests-skills — the skill these conventions are adapted from (its
  `rules/tests/general` and `rules/tests/java/unit` rules on isolation, mocking, and argument
  matching): https://github.com/clear-solutions/unit-tests-skills
- openskills (skill packaging): https://github.com/numman-ali/openskills
- Anthropic, *The Complete Guide to Building Skills for Claude*:
  https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- Google Testing Blog (test design fundamentals): https://testing.googleblog.com
- Vercel, *AGENTS.md outperforms skills in our agent evals*:
  https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
