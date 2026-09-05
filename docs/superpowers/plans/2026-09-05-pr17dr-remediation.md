# PR-17DR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate only the rejected PR-17D implementation gaps while preserving frozen Design v1.6, accepted D0, external adapter shapes, and Phase 1 scope.

**Architecture:** Keep migration 0016 as the sole database enforcement boundary, but make its SQL schema-qualified, field-exact, and self-verifying. Keep Application commands returning accepted typed read models while adding the frozen internal WriteResult conversion boundary; emit normalized command/UoW events without changing transaction ownership. Build independent catalog/lifecycle evidence from static frozen expectations plus real PostgreSQL observations, never from observed objects alone.

**Tech Stack:** Python 3.12, SQLAlchemy 2, Alembic, PostgreSQL 18, pytest, FastAPI, Typer, Ruff, Pyright, JSON evidence artifacts.

## Global Constraints

- Preserve `execution/phase1/PR-17D_Design_Specification_v1.6.md` and `execution/phase1/PR-17D_Implementation_Plan_v1.6.md` unchanged.
- Preserve accepted D0 candidate data and do not add SAFE_MIGRATION transformations.
- Preserve `phase1-final -> 5fe5dd90310d68d6df1683307f0d24dd2233c3dd` and do not rewrite history.
- Touch only PR-17D remediation production code, migration 0016, focused tests, CI needed for PostgreSQL verification, and PR-17D/PR-17DR evidence.
- Do not add PR-18, Phase 2, DecisionRecord, Approval, workflow, scheduler, or Agent Runtime production capability.
- Freeze production/test/migration remediation before generating evidence; no semantic changes after subject freeze.

---

### Task 1: Record the frozen remediation design and establish verification scaffolding

**Files:**
- Create: `docs/superpowers/plans/2026-09-05-pr17dr-remediation.md`
- Test: `tests/unit/test_pr17d_migration_graph.py`
- Inspect: `execution/phase1/PR-17D_Design_Specification_v1.6.md`

**Interfaces:**
- Consumes: frozen v1.6 invariant and object tables, original subject `2e96361d`, evidence parent `1a78b6a`.
- Produces: a tracked remediation plan and a clean baseline on branch `codex/pr17dr`.

- [x] **Step 1: Create the isolated worktree and confirm the baseline.**

  Run `git worktree add .worktrees/pr17dr -b codex/pr17dr` from the accepted evidence checkout. Confirm HEAD is `1a78b6a73c582a8b108eb295e94f51704ba10cca`, `phase1-final^{}` is `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`, and `uv run pytest -q -rN` has zero failures.

- [x] **Step 2: Save this plan and inspect it for scope drift.**

  Confirm every planned production change maps to P1-A through P1-E or the explicitly authorized logging/config/test/evidence closures. Do not add a generic settings rewrite, new adapter command, or PR-18 capability.

- [ ] **Step 3: Commit the plan only.**

  Run:

  ```bash
  git add docs/superpowers/plans/2026-09-05-pr17dr-remediation.md
  git commit -m "docs: plan PR-17DR remediation"
  ```

  Confirm the existing review checkout remains unchanged.

---

### Task 2: Correct migration 0016 guards and deterministic schema qualification

**Files:**
- Modify: `migrations/versions/0016_pr17d_history_protection.py`
- Test: `tests/integration/test_pr17dr_adversarial.py`
- Test: `tests/integration/test_pr17dr_migration.py`

**Interfaces:**
- Consumes: `FUNCTION_NAMES`, `TRIGGER_DEFINITIONS`, existing 0015 tables, frozen v1.6 field matrix.
- Produces: public-schema 18-function/40-trigger migration whose guards enforce exact finalized version and Run post-state rules.

- [ ] **Step 1: Add failing PostgreSQL tests for finalized version mutation.**

  Seed a frozen version, execute direct SQL that changes `content_hash`, `support_set_hash`, or `frozen_at` together with `status='SUPERSEDED'`, assert SQLSTATE `P17D1`, and query the row in a new transaction to prove status and protected fields are unchanged. Add the legal status-only `FROZEN -> SUPERSEDED` case and assert `row_version` increments exactly once.

- [ ] **Step 2: Add failing PostgreSQL tests for the complete Run terminal matrix.**

  Seed a running Run and exercise direct SQL for legal `SUCCEEDED`, `FAILED`, and `CANCELLED` states plus illegal combinations: `SUCCEEDED` with `failure_reason`, `CANCELLED` with `exit_code` or `failure_reason`, and any matrix-forbidden seal/timestamp mutation. Assert `P17D2` and unchanged persisted rows for illegal cases.

- [ ] **Step 3: Add failing migration schema/search-path tests.**

  Run upgrade with a controlled non-public search path and assert all PR-17D functions/triggers are created in `public`; inspect `pg_proc`, `pg_trigger`, and `pg_constraint` using the literal `public` schema and `pr17d_` ownership predicate.

- [ ] **Step 4: Implement the minimal guard corrections.**

  Generate each version guard from explicit per-table material/provenance field names. For draft material updates, allow only the table’s material fields plus `row_version`; for `DRAFT -> ABANDONED` and `FROZEN -> SUPERSEDED`, allow only status plus `row_version`; for `DRAFT -> FROZEN`, preserve all non-finalization fields and require the finalization fields expected by the existing Application path. Require `NEW.row_version = OLD.row_version + 1` for every UPDATE.

  Extend the Run guard with exact predicates for all three terminal outcomes, preserving identity, seal, start, and assigned timestamp fields and enforcing NULL/non-NULL outcome metadata exactly as v1.6 specifies.

  Qualify every PR-17D table, function, trigger, and catalog query reference with `public`; use `public.` in downgrade drops and keep reverse trigger/function order.

- [ ] **Step 5: Run the focused PostgreSQL tests and inspect post-state.**

  Run `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest -q tests/integration/test_pr17dr_adversarial.py tests/integration/test_pr17dr_migration.py`. Confirm the tests fail before implementation, then pass after it, with no raw SQLSTATE assertions replacing persisted-state assertions.

- [ ] **Step 6: Commit the migration correction.**

  Run `git add migrations/versions/0016_pr17d_history_protection.py tests/integration/test_pr17dr_adversarial.py tests/integration/test_pr17dr_migration.py && git commit -m "fix: close PR-17D database guard gaps"`.

---

### Task 3: Normalize database errors and add the shared WriteResult boundary

**Files:**
- Modify: `src/researchbase/persistence/uow.py`
- Modify: `src/researchbase/application/dto.py`
- Modify: `src/researchbase/application/commands.py`
- Test: `tests/unit/test_pr17dr_contracts.py`
- Test: `tests/integration/test_pr17dr_error_contract.py`
- Test: `tests/e2e/test_phase1_cross_adapter_equivalence.py`

**Interfaces:**
- Consumes: `ResearchBaseError`, `ErrorCode`, `ExecutionContext`, existing typed read models and adapter serializers.
- Produces: `_normalize_database_error()` coverage for all expected PR-17D SQLSTATEs and `WriteResult`/`write_result(value, server_timestamp)` with fields `id`, `version_id`, `content_hash`, `row_version`, `server_timestamp`.

- [ ] **Step 1: Add failing unit tests for complete SQLSTATE mapping.**

  Construct SQLAlchemy DBAPI wrappers with driver metadata for `P17D1`, `P17D2`, `P17D3`, `P17D4`, and `P17D5`. Assert each maps to the frozen semantic `ErrorCode`, with `P17D5` mapping to `CONCURRENT_MODIFICATION`; unknown database errors remain unexpected rather than being mislabeled.

- [ ] **Step 2: Add failing tests for WriteResult extraction and timestamp semantics.**

  Convert representative project, version, run, and content-addressed read models. Assert exact fields, UTC-aware timestamp, version/hash population when present, and no ORM/persistence import. Assert the existing read model and adapter JSON shape remain unchanged.

- [ ] **Step 3: Implement minimal error and WriteResult contracts.**

  Add `P17D4` as a migration/preflight semantic mapping only where the Application can receive it, map `P17D5` to `CONCURRENT_MODIFICATION`, and preserve existing duplicate/FK messages and details. Add the immutable application-level `WriteResult` dataclass plus a deterministic `write_result(value, server_timestamp)` conversion over typed read models. Keep existing command return annotations and HTTP/CLI response models unchanged under strategy A.

- [ ] **Step 4: Add representative Application write-result access without changing accepted adapters.**

  Add a narrow Application helper/facade that captures the supplied Application clock timestamp immediately before commit and returns `WriteResult` for new internal callers; route existing HTTP/CLI commands through their current typed projection. Do not expose a new HTTP route, CLI command, or public response envelope.

- [ ] **Step 5: Add real PostgreSQL trigger-path normalization tests.**

  Exercise a guarded update through repository flush, UoW commit, and direct trigger SQL. Assert public Application callers receive only `ResearchBaseError` semantic codes and never `IntegrityError`, `DBAPIError`, psycopg exceptions, or raw SQLSTATE/message.

- [ ] **Step 6: Commit the Application contract correction.**

  Run `git add src/researchbase/persistence/uow.py src/researchbase/application/dto.py src/researchbase/application/commands.py tests/unit/test_pr17dr_contracts.py tests/integration/test_pr17dr_error_contract.py tests/e2e/test_phase1_cross_adapter_equivalence.py && git commit -m "fix: normalize PR-17D errors and add WriteResult"`.

---

### Task 4: Implement Application/UoW logging and configuration wiring

**Files:**
- Modify: `src/researchbase/foundation/structured_logging.py`
- Modify: `src/researchbase/application/commands.py`
- Modify: `src/researchbase/persistence/uow.py`
- Modify: `src/researchbase/api/app.py`
- Modify: `src/researchbase/cli/composition.py`
- Modify: `src/researchbase/persistence/config.py`
- Test: `tests/unit/test_pr17dr_logging_config.py`

**Interfaces:**
- Consumes: `ExecutionContext`, existing `load_settings()`, `logging` configuration, UoW transaction lifecycle.
- Produces: frozen structured event fields `timestamp`, `level`, `request_id`, `correlation_id`, `command_name`, `actor_id`, `project_id`, `target_id`, `result`, `error_code`, `duration_ms`, and applied `LOG_LEVEL`/`APPLICATION_ENV` behavior.

- [ ] **Step 1: Add failing logging/config tests.**

  Capture logger records for a successful command, semantic failure, rollback, and unexpected database failure. Assert required fields, UTC timestamp, duration in milliseconds, rollback marker, and absence of URLs/passwords/tokens. Assert `LOG_LEVEL` changes the configured logger threshold, `APPLICATION_ENV` is applied to runtime logging context, and `ARTIFACT_STORE_ROOT` remains the artifact-store root.

- [ ] **Step 2: Implement structured event emission at Application/UoW boundaries.**

  Add a small event builder that derives only identifiers from `ExecutionContext`/command fields. Instrument Application commands without logging scientific payloads. Emit UoW rollback/failure events from the existing rollback path; do not call commit or rollback from the logger. Preserve CLI transport events as adapter-level events.

- [ ] **Step 3: Apply settings at both composition roots.**

  Configure the command logger level from `Settings.log_level` and attach `application_env` as non-secret logger metadata/context. Keep `database_url()` as the source of `DATABASE_URL` override/default behavior and keep `.researchbase/artifacts` as the default root.

- [ ] **Step 4: Run focused unit/architecture tests and commit.**

  Run `uv run pytest -q tests/unit/test_pr17dr_logging_config.py tests/architecture` and commit with `git commit -am "fix: close PR-17D logging and config contract"` after confirming no adapter shape changed.

---

### Task 5: Restore narrow historical trigger controls and add non-vacuous concurrency tests

**Files:**
- Modify: `tests/e2e/test_phase1_historical_exactness.py`
- Modify: `tests/integration/test_pr09r2_proof.py`
- Modify: `tests/integration/test_pr10_application.py`
- Modify: `tests/integration/test_pr12_application.py`
- Modify: `tests/integration/test_pr12_closure.py`
- Modify: `tests/integration/test_pr14_governance_integration.py`
- Create: `tests/integration/test_pr17dr_concurrency.py`

**Interfaces:**
- Consumes: exact pre-PR-17D trigger names, two-session SQLAlchemy connections, parent lock behavior.
- Produces: narrow fixture bypasses and two-transaction tests that prove overlap and final invariant state.

- [ ] **Step 1: Add failing overlap assertions.**

  Coordinate two independent PostgreSQL transactions with `threading.Barrier`/`Event`, record lock acquisition and SQL issuance from both connections, and assert both transactions overlap before the conflicting operation. Include RunInput attach versus Run start/cancel and EvidenceRelation insert/delete versus ClaimVersion freeze.

- [ ] **Step 2: Restore narrow trigger suppression in historical tests.**

  Replace every `DISABLE TRIGGER ALL` used only to seed invalid historical data with the exact legacy trigger name that blocked the fixture. Use `try/finally` to re-enable only that trigger, and keep PR-17D triggers enabled so unrelated defenses remain active.

- [ ] **Step 3: Implement the real two-transaction tests.**

  Hold Tx A after parent lock acquisition, start Tx B, prove Tx B is blocked or reaches the intended race point, release Tx A, then assert exactly one legal winner and no child mutation under a protected parent. Query persisted parent/child state in a fresh transaction.

- [ ] **Step 4: Run concurrency and historical tests against PostgreSQL 18 and commit.**

  Run `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest -q tests/integration/test_pr17dr_concurrency.py tests/integration/test_pr12_concurrency.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_historical_exactness.py` and commit the narrow test restoration and concurrency suite.

---

### Task 6: Implement independent catalog/lifecycle verification and evidence generation

**Files:**
- Create: `tests/integration/test_pr17dr_catalog.py`
- Create: `tests/integration/test_pr17dr_migration.py`
- Create: `tests/support/pr17d_manifest.py`
- Create: `scripts/pr17dr_evidence.py`
- Create: `artifacts/pr_evidence/PR-17DR/migration_object_manifest.json`
- Create: `artifacts/pr_evidence/PR-17DR/migration_catalog_verification.json`
- Create: `artifacts/pr_evidence/PR-17DR/invariant_to_test_projection.json`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: frozen v1.6 exact function/trigger tables and actual PostgreSQL catalogs.
- Produces: independent static expectations, runtime exact-set/projection checks, fresh/populated/downgrade/roundtrip evidence, and reproducible reports tied to the frozen remediation subject.

- [ ] **Step 1: Add failing manifest/schema tests.**

  Define frozen expected function and trigger rows as checked-in data independent of migration constants. Assert manifest schema, 18/40/0 counts, every trigger/function projection, no discarded v1.5 names, and no function-to-function edges.

- [ ] **Step 2: Add failing runtime catalog tests.**

  Query `pg_proc`, `pg_trigger`, and `pg_constraint` in `public` using literal `left(name, 6) = 'pr17d_'`. Compare `missing` and `unexpected` sets exactly. Assert trigger table/event/timing/level/bound function and function signature/result/language plus consumer/classification metadata.

- [ ] **Step 3: Add failing migration lifecycle tests.**

  Run fresh install, conforming populated 0015 upgrade, downgrade, and upgrade/downgrade/upgrade on disposable PostgreSQL 18 databases. Snapshot scientific rows and revision before preflight failure, inject one nonconforming enum value, assert migration failure leaves revision/objects/data unchanged, and verify post-downgrade owned sets are empty.

- [ ] **Step 4: Implement the independent manifest and runtime verifier.**

  Keep expected rows in the verifier/manifest source, not generated from `pg_*` observations or migration constants. Serialize deterministic JSON with protocol version, subject metadata, expected/observed projections, missing/unexpected sets, and overall status. Use the same verifier for post-upgrade, fresh install, downgrade, and roundtrip phases.

- [ ] **Step 5: Add CI PostgreSQL 18 lifecycle execution.**

  Keep service readiness before Alembic migration and integration tests. Add the PR-17DR catalog/lifecycle suite to CI without changing unrelated CI behavior.

- [ ] **Step 6: Commit verification tooling before evidence generation.**

  Run all focused PostgreSQL tests, then commit code/tests/tooling. Do not commit evidence until the implementation subject is frozen.

---

### Task 7: Full verification, subject freeze, and evidence generation

**Files:**
- Modify/Create: `artifacts/pr_evidence/PR-17DR/*`
- Inspect: all changed production/test/migration/CI files

**Interfaces:**
- Consumes: frozen remediation implementation commit and real PostgreSQL 18 execution results.
- Produces: `PR17DR_IMPLEMENTATION_SUBJECT_HEAD`, `PR17DR_EVIDENCE_HEAD`, reproducible evidence, and a stop-ready remediation report for an independent reviewer.

- [ ] **Step 1: Run the complete PostgreSQL-backed verification matrix.**

  Run full pytest, all integration/e2e PR-17DR suites, architecture tests, Ruff, Pyright, and `git diff --check`. Record exact collected/passed/skipped/deselected counts and PostgreSQL version/revision. Any PostgreSQL skip is a hard stop with `READY_FOR_INDEPENDENT_PR17DR_REVIEW = NO`.

- [ ] **Step 2: Review scope and formatting debt.**

  Confirm no PR-18/Phase 2 production identifiers, no unrelated dependencies/refactors, inherited formatting debt remains exactly eight files, and new formatting debt is zero.

- [ ] **Step 3: Freeze the remediation implementation subject.**

  Commit only production, migration, tests, CI, and verification tooling changes. Record the full `PR17DR_IMPLEMENTATION_SUBJECT_HEAD`; do not alter semantic files afterward.

- [ ] **Step 4: Generate evidence from executed output.**

  Run `scripts/pr17dr_evidence.py` against PostgreSQL 18 after subject freeze. Write only factual catalog/lifecycle/test results, include full subject SHA and evidence parent, preserve `non-self-referential-v1`, and ensure no credential-bearing URL appears.

- [ ] **Step 5: Freeze the evidence commit and verify chronology.**

  Commit evidence separately, record `PR17DR_EVIDENCE_HEAD`, verify it is a child of the implementation subject, and confirm `phase1-final^{}` remains the canonical baseline.

- [ ] **Step 6: Stop for independent review.**

  Return the required remediation report with `PR17DR_SELF_APPROVED: NO`, `PR18_AUTHORIZED: NO`, `PHASE_1_FINAL_GATE_READY: NO`, and `PHASE_2_AUTHORIZED: NO`. Do not begin PR-18 or Phase 2.
