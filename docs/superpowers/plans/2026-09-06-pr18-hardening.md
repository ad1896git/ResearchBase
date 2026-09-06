# PR-18 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden and verify the finalized Phase 1 surface against the frozen PR-18 contract, producing reproducible PR-18 evidence without implementing Phase 2 or changing accepted Phase 1 semantics.

**Architecture:** Verification-first additions around the existing Application/Core, API, CLI, PostgreSQL catalog, and evidence boundaries. No new runtime subsystem. No migration unless a live catalog audit and a focused failing invariant test prove one is required.

**Tech Stack:** Python 3.12, uv, pytest, PostgreSQL 18, SQLAlchemy/psycopg, FastAPI, Typer, Ruff, Pyright, Alembic, JSON/Markdown evidence.

## Global Constraints

- Work only in `/Users/onephone/Documents/Codex/ResearchBase-pr18`.
- Preserve the dirty primary worktree and the immutable `phase1-final` tag.
- Do not implement Phase 2, agent runtime, agent persistence, new APIs, or speculative architecture changes.
- Keep `PHASE_1_FINALIZED: YES`, `PR18_AUTHORIZED: YES`, and `PHASE_2_AUTHORIZED: NO`.
- Prefer tests, audits, documentation, and evidence over production changes.
- Use `apply_patch` for file edits and keep commits chronologically reviewable.

## Frozen acceptance-to-verification matrix

| Frozen criterion | Test/evidence task | Acceptance signal |
| --- | --- | --- |
| Catalog/index verification | Task 2 integration tests and catalog artifact | Required Phase 1 indexes exist with expected definitions; no migration is added when the audit passes |
| Query EXPLAIN baselines | Task 2 integration tests and normalized JSON artifact | Critical existing read paths produce reviewed, reproducible plans without unbounded query shape |
| Error/log hardening | Task 3 unit tests and audit artifact | Nested secrets, database URLs, raw exception details, and CLI tracebacks are redacted or withheld |
| Architecture coverage | Task 4 architecture tests and report | Existing import, adapter, API/CLI, and persistence boundaries remain enforced |
| Agent-ready Core audit | Task 4 boundary tests and report | Core remains framework-neutral and application-mediated; no agent implementation is added |
| API/CLI examples | Task 5 documentation and contract tests | Examples use only frozen Phase 1 routes/commands and remain repository-relative/reproducible |
| TODO/FIXME disposition | Task 4 marker audit and gate test | Every relevant marker is classified as `RESOLVED_IN_PR18`, `ACCEPTED_NON_BLOCKING`, `DEFERRED_WITH_EXPLICIT_FUTURE_OWNER`, or `OUT_OF_SCOPE`; no unexplained architecture-critical marker remains |
| Evidence protocol | Task 6 generator/tests and reproduction | Exact commands, tokens, fingerprints, counts, redaction, path, and stale-result checks are fail-closed and reproducible |
| Phase 1 preservation | Task 7 full, integration, and closure-critical regressions | Baseline passes remain green; any count delta is explained by direct PR-18 tests |

## Task 1: Freeze the contract and verify the starting point

- [x] Confirm the dedicated worktree is clean and starts at `3ba3c6a0ad94fbeb01acaf1bac381ec1d352b404`.
- [x] Confirm the reviewed PR-17DR5 candidate, PR-17DR5 tooling subject, and historical Phase 1 baseline are reachable.
- [x] Record the recovered design in `docs/superpowers/specs/2026-09-06-pr18-hardening-design.md`.
- [x] Record this implementation plan in the repository plan hierarchy.
- [ ] Commit only the plan/specification documents before implementation work.

## Task 2: Add catalog and EXPLAIN tests before any production change

- [ ] Add failing-first tests in `tests/integration/test_pr18_hardening.py` for the required catalog/index invariants from the Phase 1 schema and history-protection contract.
- [ ] Add tests for normalized EXPLAIN JSON on the existing provenance, claim-trace, and governance-impact read paths, using deterministic fixture data and bounded plan assertions.
- [ ] Run only these new tests and capture their initial failure reason before adding implementation or evidence code.
- [ ] Make the minimum test/audit implementation needed for the current catalog to pass.
- [ ] Do not add a migration unless the focused tests prove a required invariant is absent or incorrect.

## Task 3: Add error and logging hardening coverage before production edits

- [ ] Add focused tests for nested structured-log redaction, PostgreSQL URL/password/token redaction, generic HTTP 500 behavior, and CLI internal-error output.
- [ ] Confirm malformed and boundary values cannot leak credentials or exception text.
- [ ] Run the focused tests and change production code only if a frozen invariant fails.

## Task 4: Add architecture, Agent-ready Core, and TODO/FIXME gate coverage

- [ ] Add architecture tests for Application/Core ownership, API/CLI mediation, adapter persistence isolation, frozen DTOs, and forbidden agent/Phase 2 runtime imports.
- [ ] Add an explicit Agent-ready Core audit that checks framework neutrality and prohibits agent runtime, persistence, scheduling, and vendor-state implementation.
- [ ] Add a repository marker audit for production and architecture documentation scope.
- [ ] Classify every relevant marker using one of the four approved dispositions and record the result in `artifacts/pr_evidence/PR-18/todo_fixme_disposition.md`.
- [ ] Make the final architecture-TODO gate fail on unexplained architecture-critical markers.

## Task 5: Add frozen Phase 1 API and CLI examples

- [ ] Add concise repository-relative API examples using existing Phase 1 routes and response contracts.
- [ ] Add concise CLI examples using the existing command map and deterministic output contract.
- [ ] Add documentation contract tests that reject Phase 2/agent runtime examples and verify referenced routes/commands exist.

## Task 6: Add PR-18 evidence tooling and namespace

- [ ] Add focused evidence-contract tests before implementing the PR-18 evidence generator.
- [ ] Implement a narrow PR-18 evidence generator or recorder that does not modify PR-17DR5 tooling or artifacts.
- [ ] Enforce exact command tokens, fingerprints, current-result accounting, repository-relative paths, credential redaction, stale-result rejection, and non-self-referential semantics.
- [ ] Generate `artifacts/pr_evidence/PR-18/` artifacts for catalog verification, EXPLAIN baselines, error/log audit, architecture verification, Agent-ready Core audit, API/CLI examples, TODO/FIXME disposition, commands/results, and implementation verification.

## Task 7: Verify, reproduce, and commit

- [ ] Run the focused PR-18 selectors using authoritative repository conventions.
- [ ] Run `uv run ruff check .`, `uv run pyright`, and `git diff --check`.
- [ ] Run the accepted full suite and PostgreSQL integration suite; reconcile discovered, selected, deselected, passed, failed, and skipped counts.
- [ ] Re-run WriteResult, adversarial, concurrency, migration lifecycle, rollback, catalog, architecture, atomicity, historical exactness, hash, provenance, adapter-equivalence, DB-invariant, and evidence-tool selectors.
- [ ] Reproduce final evidence from a clean disposable clone/worktree and verify direct execution equals generator execution equals stored artifact where applicable.
- [ ] Commit the implementation subject with no hidden evidence-only changes.
- [ ] Generate and validate evidence from the implementation subject.
- [ ] Commit evidence as a separate evidence-only commit.
- [ ] Verify chronology, clean worktree, no post-subject semantic changes, no remote push, and no Phase 2 artifacts.
- [ ] Use the finishing-development-branch workflow, then report readiness for independent review without setting the final gate to PASS.

## Required final report state

The final report must be headed `PR-18 HARDENING IMPLEMENTATION REPORT` and must state:

```text
PR18_IMPLEMENTED: YES/NO
PR18_IMPLEMENTATION_VERIFIED: YES/NO
PR18_READY_FOR_INDEPENDENT_REVIEW: YES/NO
PR18_FINAL_GATE: PENDING INDEPENDENT REVIEW
PHASE_2_AUTHORIZED: NO
```

No Phase 2 implementation, authorization, tag mutation, or remote push is permitted.
