# PR2-04 acceptance coverage execution plan

**Goal:** Complete every safely executable frozen acceptance dimension without product changes.

**Architecture:** Real PostgreSQL 18.6, existing application paths, and test-layer instrumentation. Candidate-bound traces are generated after bounded commits. No production test hooks or policy relaxation.

**Tech stack:** Python 3.12, uv, pytest, PostgreSQL 18.6, existing PR2-04 evidence producer and validator.

## Constraints

Product closed base: `25b6994d218f221aa5b2c38e03af768d9d9b8de0`. Freeze src, migrations, schema, dependencies, architecture and authorization policy. Preserve all assertions and 231 accepted regressions. Historical authorization denial remains INSUFFICIENT_EVIDENCE. No closure review or PR2-05.

## Authoritative inventory

`execution/phase2/PR2-04_Acceptance_Coverage_Inventory.json` records all 28 rows before test authoring: exact requirements, bindings, observed assertions, missing dimensions, prerequisites and concrete strategies. The committed gap register incorrectly omitted IDEM-01; actual R7D evidence correctly retained it. Starting effective counts are 37 FULL / 28 PARTIAL and 37 PASS / 28 NOT_RUN.

## Ordered bounded groups

- [ ] A: Correct binding gaps and bind existing BOUND-02 phase-local retry nodes and TRACE-01 uncertainty/cross-project nodes. Change decorators and `scripts/pr2_04_requirement_bindings.json` only; preserve assertions. Execute reused exact nodes and all checkpoint gates.
- [ ] B: Deterministic missing dimensions IDEM-04/05, PROV-02/04 and SUCCESS-01. Follow exact per-row inventory strategies; distinguish fake adapter conformance from production parsing. Use new test files or additive assertions, no product changes.
- [ ] C: PostgreSQL state/outcome/parent-delete/reservation dimensions DOM-01/02, DB-01/05, AUTH-04 and CRASH-06. Use causal valid fixtures so the intended guard executes. Retain exact SQLSTATE and zero-effect assertions.
- [ ] D: Restart paired cases CONC-02/CRASH-03/04 with fresh sessions/service graphs and separate OS processes where required. Report exact reconstruction level.
- [ ] E: Real concurrency IDEM-01, DB-04, AUTH-02, CONC-03/04 using independent connections and barriers, both orderings and five repetitions wherever frozen pack requires.
- [ ] F: TX-A/B/C and C1/C2 commit-boundary faults BOUND-03, IDEM-06, CRASH-05/07, CONC-05/06, through existing test seams. Assert durable state and provider invocation counts; no hidden reruns.
- [ ] G: Verify authoritative AGENT provisioning prerequisite; preserve AUTH-01 NOT_RUN if unsupported. Never fabricate identity rows.
- [ ] Final: Run complete/focused/non-DB/PG/accepted/migration/architecture/host/static/scope stack; regenerate all65 audit, seal candidate evidence, report precise blockers. Stop before independent closure review.

## Every group checkpoint

Commit only bounded authorized test/binding/documentation changes. Execute changed nodes, accepted231, relevant focused suite, matrix producer/validator, coverage audit and scope guards. Major groups also run full preservation stack. Require current candidate SHA and fresh trace digests. New legitimate product defects retain deterministic failing regression and FAIL evidence; stop only that root and continue independent work. Never convert absence into PASS.
