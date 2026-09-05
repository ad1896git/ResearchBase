# PR-17DR2 Contract, Test, and Evidence Closure Implementation Plan

> **Execution note:** Follow this plan task by task with `superpowers:executing-plans`. Every production behavior change and every regression-test change follows `superpowers:test-driven-development`: add the smallest failing test, run it to observe the failure, implement the change, then rerun the focused test.

## Goal

Close the eight authorized PR-17DR2 findings while preserving PR-17D Design v1.6, the accepted 18-function/40-trigger/0-constraint architecture, accepted HTTP and CLI response shapes, `phase1-final`, and the no-PR-18/no-Phase-2 boundary.

## Task 1: Establish the canonical Application write contract

Files:

- Modify `src/researchbase/application/commands.py`.
- Modify `src/researchbase/application/dto.py` only if a non-public projection target type is required; keep the frozen five `WriteResult` fields unchanged.
- Add focused tests in `tests/unit/test_pr17dr2_write_result.py`.
- Add or update compatibility tests in `tests/integration/test_pr15_api.py` and `tests/integration/test_pr16_cli.py` only where the existing public-shape assertions need to exercise the new path.

Steps:

1. Add a unit test that invokes a real `ApplicationService` write command with an in-memory/fake UoW and asserts the return value is the existing immutable `WriteResult`, has exactly the five frozen fields, validates a UTC-aware timestamp, and rejects extra fields.
2. Run that test and record the expected failure because the current write command returns a typed read model.
3. Define an explicit internal registry of `ApplicationService` write command names. Keep queries and `to_write_result` out of the registry. Convert each registered successful command result at the Application boundary using the existing `write_result` helper and the Application clock.
4. Preserve the existing immutable `WriteResult` field set and semantics: stable `id`, optional `version_id`, optional `content_hash`, optional `row_version`, and `server_timestamp`; do not add a payload field or adapter-only field.
5. Add deterministic Application-owned projection targets and query methods for any version or evidence relation currently missing from the Application query surface. Each target resolves by the exact identifier in `WriteResult`; no latest-row lookup, broad search, or business decision is allowed.
6. Add tests proving the projector uses the exact id/version id, rejects a missing required identifier, and treats mutable projections as post-commit reads rather than command-time snapshots.
7. Run the focused unit and Application contract tests until green.

## Task 2: Preserve HTTP/CLI compatibility and prove the Agent-ready boundary

Files:

- Modify `src/researchbase/api/routes.py`.
- Modify `src/researchbase/cli/common.py` and the affected command modules under `src/researchbase/cli/commands/`.
- Modify `tests/architecture/test_pr17_agent_ready_architecture.py`.
- Add adapter-path coverage to `tests/unit/test_pr17dr2_write_result.py` or a focused integration test module.

Steps:

1. Add failing adapter tests that call real HTTP and CLI composition paths, assert the Application command returns `WriteResult`, and assert the existing response models/JSON and error mappings remain unchanged.
2. Run the focused adapter tests and observe the failure caused by adapters receiving a `WriteResult` instead of the legacy read model.
3. Add one small adapter orchestration helper per transport boundary, or a shared transport-neutral helper, that performs only `command -> Application deterministic query -> existing serialization`. Keep all target selection explicit at the route/command mapping; do not reconstruct domain semantics in adapters.
4. Use stable identifiers from the `WriteResult` and explicit command outcome for every compatibility projection. Preserve UoW commit boundaries; do not hold a write transaction open for a legacy read-after-write payload.
5. Add a direct Application contract test that acts as a future Agent caller: invoke a real write command without importing FastAPI or Typer and assert the shared `WriteResult` is returned.
6. Run focused HTTP, CLI, cross-adapter equivalence, and architecture tests until green.

## Task 3: Remove historical broad trigger weakening and repair the legal race fixture

Files:

- Modify `tests/integration/test_pr12_closure.py`.
- Modify `tests/integration/test_pr09_application.py`.
- Add focused static/behavioral assertions in `tests/unit/test_pr17dr2_write_result.py` only if needed to prevent recurrence.

Steps:

1. Add a static test or focused search assertion that the PR-17D/PR-17DR-touched tests contain no `DISABLE TRIGGER ALL` or `ENABLE TRIGGER ALL`.
2. Run the test to fail against the eight existing broad occurrences.
3. For each statistical-result-input and evidence-relation historical fixture, inspect the live trigger catalog and replace broad suppression with the exact trigger(s) required by the fixture, or construct a valid fixture that avoids suppression. Keep all unrelated history and invariant triggers active and restore any temporarily disabled exact trigger in a `try/finally` path.
4. Change the historical concurrent Run-finish fixture so every competing terminal row has legal metadata under v1.6. A `SUCCEEDED` contender must not carry `failure_reason`; failed contenders must carry the required failure metadata. Keep the real coordination and final-state assertions.
5. Run the affected historical closure and concurrency tests, then search the complete touched test surface to verify broad trigger suppression is absent.

## Task 4: Add direct-SQL adversarial and dedicated real-PostgreSQL concurrency coverage

Files:

- Add `tests/integration/test_pr17dr2_adversarial.py`.
- Add `tests/integration/test_pr17dr2_concurrency.py`.
- Extend existing helpers only when they preserve independent direct-SQL setup and final-state inspection.

Steps:

1. Add failing parameterized direct-SQL tests for legal `FROZEN -> SUPERSEDED` and rejected status-plus-mutation attempts for `content_hash`, `frozen_at`, and `support_set_hash` on applicable version tables. Assert persisted status and protected fields after every rejected transaction.
2. Add failing direct-SQL Run terminal matrix tests for `SUCCEEDED`, `FAILED`, and `CANCELLED`, explicitly attacking `finished_at`, `started_at`, seal/seal-related fields, `exit_code`, and `failure_reason`, with legal controls and post-state assertions.
3. Run the new adversarial tests against the existing implementation and confirm the tests fail only where the fixture/coverage is currently missing; do not alter the already-accepted database guard implementation.
4. Add a standalone concurrency test module using two separate PostgreSQL connections, explicit barrier/event coordination, observable transaction overlap, the intended lock path, and final persisted-state inspection. Assert two distinct backend connection identities, not merely elapsed-time behavior.
5. Run the standalone module and the repaired historical concurrency test with PostgreSQL 18. Require zero current-remediation skips and retain the exact two inherited PR11R2 opt-in skips only when those exact tests require `PR11R2_MIGRATION_DB_URL`.

## Task 5: Make migration preflight rollback evidence complete and deterministic

Files:

- Modify `tests/integration/test_pr17dr_migration.py`.
- Add a small test-only snapshot helper under `tests/integration/` if keeping the migration test readable requires it.

Steps:

1. Add a failing assertion that snapshots every relevant Phase 1 scientific table before the intentionally failing `0015 -> 0016` upgrade and compares the complete state afterward.
2. Define the table inventory explicitly from the Phase 1 schema contract, derive primary-key ordering from PostgreSQL metadata, quote the fixed public identifiers, and normalize UUIDs, timestamps, decimals, bytes, arrays, and nested values deterministically. Never order by an inferred “latest” column.
3. Capture the Alembic revision and complete PR-17D object catalog before the failure. After failure, assert every scientific-row snapshot is identical, the revision is unchanged, and functions/triggers/constraints show no partial PR-17D creation.
4. Keep the existing fresh install, populated upgrade, downgrade, roundtrip, search-path, and preflight-failure lifecycle assertions. Run the focused migration tests on PostgreSQL 18 until green.

## Task 6: Replace hard-coded evidence with execution-derived PR-17DR2 artifacts

Files:

- Modify `scripts/pr17dr_evidence.py`.
- Add/update `tests/unit/test_pr17dr2_evidence.py` for generator contracts.
- Generate new artifacts only under `artifacts/pr_evidence/PR-17DR2/` after subject freeze.

Steps:

1. Add failing generator tests for hard-coded status detection, expected/observed/verdict separation, `NOT_VERIFIED` for unexecuted checks, exact pytest count capture, repository-relative command rendering, live catalog observation, and separate implementation-verification output.
2. Run the generator tests to observe the current hard-coded PASS fields and missing artifact/count fields.
3. Keep the static frozen manifest as the only source for expected catalog sets. Query PostgreSQL system catalogs for observed objects and compute missing, unexpected, orphan, stale-reference, non-public, discarded-helper, and exact-set verdicts from the query results.
4. Add a verification runner that executes the required commands, captures command identifier, repository-relative command, collected, passed, failed, skipped, deselected, return code, status, and relevant database identity, including static-tool results. Render interpreter invocations as repository-relative `python -m ...`/`uv run ...` command forms without absolute worktree paths.
5. Compute invariant projection statuses from the recorded command/test results. Emit `NOT_VERIFIED` whenever the required test/query did not execute; do not synthesize PASS from an expected value.
6. Write `artifacts/pr_evidence/PR-17DR2/implementation_verification.json` separately from `migration_object_manifest.json`, `migration_catalog_verification.json`, and `invariant_to_test_projection.json`. Validate all generated JSON against the repository’s evidence schema/tests, redact credentials, and include implementation subject and evidence-head chronology.
7. Run generator unit tests without creating authoritative evidence, then run the generator only after the implementation subject is frozen.

## Task 7: Full verification, subject freeze, evidence generation, and stop

Steps:

1. Run all semantic tests and static gates before freezing: full pytest, PostgreSQL integration, focused PR17DR2 contract/adversarial/concurrency tests, migration lifecycle and complete rollback snapshot, catalog exactness, architecture, atomicity, historical exactness, hash invariance, provenance, adapter equivalence, Ruff, Pyright, and `git diff --check`.
2. Reconcile every count against the exact command output. Record the server version, redacted `DATABASE_URL` source, database, schema, and Alembic revision; identify only the two inherited PR11R2 opt-in skips if present.
3. Inspect the diff from the PR17DR2 starting HEAD and classify every changed file as authorized closure scope. Search production code for PR-18, DecisionRecord, Approval, and Phase 2 implementation; reject any implementation scope expansion.
4. Verify the frozen design file, `phase1-final`, prior subjects, and prior evidence commits are unchanged and that there is no history rewrite.
5. Freeze the implementation subject at the commit containing all semantic production/test/migration changes. Record it separately as `PR17DR2_IMPLEMENTATION_SUBJECT_HEAD`.
6. Generate evidence from a clean-checkout-compatible repository-relative command at that subject, with live PostgreSQL 18 observations, then commit only the evidence artifact changes as the evidence head. Record it separately as `PR17DR2_EVIDENCE_HEAD`.
7. Run evidence schema/reproducibility/credential/chronology checks after generation without changing semantic code, tests, or migrations. If any required verification is unexecuted or skipped unexpectedly, record `NOT_VERIFIED` and stop without claiming readiness.
8. Report the exact commands, counts, artifacts, findings, and commit heads. Set `PR17DR2_SELF_APPROVED: NO`, `PR18_AUTHORIZED: NO`, and `PHASE_2_AUTHORIZED: NO`, then stop for independent PR17DR2 re-review.

## Verification commands

Use the repository’s configured PostgreSQL 18 environment and repository-relative command forms. The implementation-verification artifact will record exact actual results for each command identifier:

- `full_pytest`
- `postgresql_integration`
- `pr17dr2_focused_contract`
- `pr17dr2_adversarial`
- `pr17dr2_concurrency`
- `migration_lifecycle`
- `migration_rollback_snapshot`
- `catalog_exact`
- `architecture`
- `atomicity`
- `historical_exactness`
- `hash_invariance`
- `provenance`
- `adapter_equivalence`
- `ruff`
- `pyright`
- `git_diff_check`

The final handoff must distinguish implementation-subject verification from evidence-head verification and must not present a self-approval.
