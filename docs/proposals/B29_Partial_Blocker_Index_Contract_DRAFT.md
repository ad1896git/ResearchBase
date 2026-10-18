# B29 Partial Blocker-index Admission Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B29 decides whether a smaller physical index helps the existing OPEN/BLOCKING
gate. It adds no scientific fact, command, disposition policy or read model.
The candidate is `ix_pr220_issue_open_blocking_review`, already proposed by
[PR2-20 §13.1](PR2-20_Hardening_Plan_DRAFT.md#131-exact-ddl-sketch-and-catalog-assertions).
An index is optional; an evidence-backed rejection is a valid outcome.

Build only after owner approval **and separate implementation authorization**:

1. Verify B08 and the live catalog, including the actual Alembic predecessor
   (§§1, 12.1). Do not edit historical migration 0040.
2. Measure realistic Issue cardinalities and captured gate queries with existing
   PR2-20 tooling (§§3, 11.3). Compare identical populated disposable databases.
3. Present before/after plans, timings, storage and write costs for explicit owner
   admission (§9). No automatic threshold authorizes DDL.
4. If admitted, append one transactional index-only migration (§12.1); retain
   the existing composite index and every scientific constraint and trigger.
5. Run catalog, migration, blocker, history and race regressions (§12.4), record
   exact results, and stop. This is neither B08 nor Phase 2 acceptance.

Five rules whose violation fails review:

1. Preserve complete matching review scope and all terminal-history validation.
2. Never treat favorable reviews or index membership as scientific authority.
3. Keep snapshot-consistent writes and lock order unchanged; measurement adds no
   explicit locks. Reads use one lock-free REPEATABLE READ snapshot (§12.2).
4. Never weaken the historical 0040 all-OPEN guard to justify an index. B08 alone
   owns the admitted status extension (§1).
5. No migration without measured benefit and explicit owner admission; missing
   evidence is BLOCKED, never PASS.

Read §§1–3 first; use the glossary (§10), pinned decisions (§11) and build guide
(§12) for detail. This document alone authorizes no schema or executable change.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried forward |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §3; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md) | Deterministic facts precede authority; immutable history and one Application transaction per command. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§12–18, 24 | No new canonical concept, weakened FK, rewritten history or changed stable error semantics. |
| [Phase 2 Spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §19, PR2-20; [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md) | Review/Issue ownership and query/index hardening; physical optimization cannot redefine blocking. |
| [ADR-0016](../architecture/adr/ADR-0016-b08-issue-disposition.md); [B08 evidence](../phase2/B08-first-slice-evidence.md) | B08 is implemented: immutable terminal events, guarded status projection, complete history validation, SHARE-first writes and lock-free historical reads. |
| [PR2-20](PR2-20_Hardening_Plan_DRAFT.md), §§5, 12–13; [Harness Spec](../harness/09_Harness_Integration_Specification_v1.0.md) | Measure first; owner-admitted migration only; engineering evidence never writes canonical facts directly. |

[0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py)
creates `review_issues_status_check CHECK(status='OPEN')` and
`ix_pr214_issue_review_severity(review_record_id,severity)`.
That frozen migration remains unchanged. The current schema is different:
[0053](../../migrations/versions/0053_b08_issue_disposition.py) replaces that CHECK
with `ck_b08_issue_status` allowing OPEN/ADDRESSED/DISMISSED, under B08 event and
projection guards. Its downgrade restores the all-OPEN rule only after refusing
terminal history. B29 preserves both historical and current contracts; it must
neither restore all-OPEN on a current database nor relax it at an old checkpoint.

[Decision repository `has_blockers`](../../src/researchbase/persistence/decision_repository.py)
first validates non-OPEN Issue history through `b08_check_history`, then tests
`status='OPEN' AND severity='BLOCKING'` across exact matching reviews.
[The PR2-20 catalog test](../../tests/integration/phase2/test_pr2_20_catalog_plans.py)
already asserts the candidate index is absent and the B08 CHECK is present.
Older PR2-20 prose describing a current all-OPEN schema predates B08; it is not
permission to change guards. No B29 execution pack or implementation is supplied
by this draft. Recheck the actual head before future authorization.

## 2. Scope, dependency boundaries and non-goals

Dependencies: implemented B08 plus PR2-20 cardinality/query-plan measurement.
The only possible production change is one nonunique B-tree index. Preserve
existing SQL, DTOs, hash payloads, permissions, retries and transaction behavior.
If a useful plan requires query or lock changes, stop and seek a separate contract.
The present task creates only this proposal.

## 3. Invariants and admission evidence

Measure total Issues, OPEN Issues, BLOCKING Issues and OPEN/BLOCKING Issues, both
globally and per review/project/target class; include zero-Issue reviews, one
blocker among many favorable reviews, mostly OPEN data and legal B08 terminal
history. Record exact distributions, fixture seed/identity, database version,
statistics freshness, catalog/index sizes and captured SQL/parameter classes.
Generate terminal rows through B08, never direct status UPDATE or disabled guards.

Compare the same legal fixture before/after candidate installation in disposable
PostgreSQL 18 databases. Reuse PR2-20 warmups, repetitions, 1/4 worker profiles,
nearest-rank percentiles and regression/noise policy; do not invent measured
counts or promise index selection. Capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`
for actual read SQL, including hit/miss and different selectivities, plus service
latency, buffer traffic, query count, index bytes, build duration and Issue
INSERT/disposition overhead. Include the terminal-history scan: the partial
index cannot replace it. Never force `enable_seqscan=off` as benefit evidence.

Canonical row/ID/hash/edge manifests, exact service results, denial codes and
complete basis must agree. Only the physical index catalog may differ. Ordinary
EXPLAIN can describe a write plan; do not EXPLAIN ANALYZE a mutating statement.
No evidence is collected from a retained application database by this workflow.

## 4. Proposed commands, DTOs and historical readback

No B29 Application command, query, HTTP route, CLI command or canonical DTO.
Use existing owning services for fixture writes and behavior measurements;
engineering evidence stays in the existing PR2-20 file layouts (§11.3).
Completed replay returns the same historical result under current read entitlement.
Index installation never authorizes re-execution or a new interpretation of history.

## 5. Persistence/schema proposal — no migration

Only the candidate in §12.1 is proposed. Retain the existing composite index:
it also serves severity and nonpartial access. No tables, columns, relationships,
status transitions, receipts, materialized views, caches or persistence mechanism
are added. Do not edit ORM mappings for a canonical fact that has not changed.

## 6. Error contract — existing categories only

No new ErrorCode or transport mapping. Existing service errors retain their
mapping (§11.2). Alembic/driver failures are operator failures with a nonzero
process result and rollback; they are not invented HTTP/CLI business errors.
Evidence validation failure is a failed engineering check, not a new API response.

## 7. Transactions, concurrency and failure recovery

Index installation is a normal transactional Alembic migration, without
CONCURRENTLY/autocommit. PostgreSQL's index-build table lock can delay writers;
the owner must admit a deployment window and rollback plan. Set any deployment
timeouts explicitly in the future execution pack; timeouts roll back, never PASS.
No service transaction is held while generating reports or waiting for approval.
No command retry policy changes. Reads, including nested history validation,
take no explicit table, advisory or row locks; PostgreSQL implicit ACCESS SHARE
for SELECT is expected. See §12.2 for the unchanged writer protocols.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Require predicate/catalog fidelity, no duplicate/equivalent index, unchanged
scientific guards and manifests, transactional failure recovery and index-only
downgrade. Re-run actual complete blocker gates, historical replay, B08 history
validation and both race commit orders. Timing tests must retain raw samples and
plans; do not assert literal planner text or require an index scan on tiny data.
Concrete files/cases are pinned in §12.4.

## 9. Acceptance criteria and evidence boundary

Before DDL: identify the exact subject/diff, B08 admission, real predecessor,
catalog baseline, workload distributions and before/after evidence. Owner admission
must name the candidate/predicate, measured benefit, write/storage/build costs,
deployment window and rollback, with a durable local approval reference.
PR2-20's 10% regression/15% noise classifications are evidence policy, not an
automatic admission vote. Redundant, noisy or unjustified candidates remain absent.

After separately authorized implementation: required checks pass with exact
commands/counts and no open P0/P1; catalog differs only as admitted; blocker,
history, hash, authorization and race behavior remains intact. Stop at B29.
Draft creation proves none of those future acceptance conditions.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Blocker | An applicable Issue whose current verified status is OPEN and severity BLOCKING. |
| Partial index | Physical index containing only rows matching its predicate; never a source of scientific truth. |
| Cardinality | Measured row counts and distributions relevant to selectivity and plan cost. |
| Admission | Owner's explicit acceptance of measured DDL and deployment costs; distinct from contract approval and execution authorization. |
| All-OPEN guard | Historical 0040 CHECK, preserved at that checkpoint; current status extension is owned by B08. |
| Terminal history | B08 OPEN root plus verified ADDRESSED/DISMISSED event and matching projection. |
| Snapshot | One consistent read transaction; write consistency uses existing exclusion protocols, not an index. |
| UoW | Existing Application transaction boundary, not a new B29 persistence abstraction. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Exactly one optional candidate; no replacement of the composite index, query
rewrite, guard relaxation or automatic tuning. B08 prerequisite is implemented,
but measurement and explicit owner migration admission remain mandatory. No new
schema registry entry or runtime dependency is needed for this physical index.

### 11.2 Pinned error mappings

These existing categories are relevant to measured service calls. Values match
[api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); no B29 wrapper remaps them.

| Code | HTTP | CLI exit |
| --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 |
| AUTHENTICATION_REQUIRED | 401 | 3 |
| FORBIDDEN | 403 | 3 |
| NOT_FOUND | 404 | 3 |
| CONFLICT_OF_INTEREST | 403 | 3 |
| INVALID_STATE_TRANSITION | 409 | 4 |
| IMMUTABLE_RECORD | 409 | 4 |
| CONCURRENT_MODIFICATION | 409 | 4 |
| IDEMPOTENCY_CONFLICT | 409 | 4 |
| LEGACY_STATE_INVALID | 409 | 4 |
| APPROVAL_GATE_FAILED | 409 | 4 |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 |

Unexpected HTTP `INTERNAL_ERROR` is 500; unexpected CLI failure exits 1. It is not
an ErrorCode member. Other owning-service categories retain their existing maps.

### 11.3 DTO fields, Python types, limits and enums

No new public fields or enums. Reuse the frozen, closed, keyword-only dataclasses
in [tests/contracts/pr2_20_evidence.py](../../tests/contracts/pr2_20_evidence.py):

| Existing layout/field group | Exact types and limits |
| --- | --- |
| EvidenceRecord common fields | `schema_version: Literal[1]`, `subject_revision: str`, `dirty_diff_sha256: str`, `status: Literal['PASS','FAIL','BLOCKED','NOT RUN','DEFERRED']`, `reason: str \| None`, `evidence_refs: tuple[str, ...]`. Non-PASS requires nonblank reason. |
| QueryPlanEvidence identity/references | `case_id`, `service_method`, `repository_method`, `parameter_class`, `sql_sha256`, `profile_ref`, `sample_ref`: `str`; `plan_refs`, `index_definitions`: `tuple[str, ...]`. |
| QueryPlanEvidence measurements | `calls`, `warmups`: `int`; `concurrency: Literal[1,4]`; `p50_ms`, `p95_ms`, `max_ms`, `lock_wait_ms`: `float \| None`; `buffer_hits`, `buffer_reads`, `query_count`: `int \| None`; `correctness_equal: bool \| None`. PASS requires actual calls, query count and true parity. |
| File bounds | 1 MiB serialized record, 10,000 array members; strict UTF-8/NFC; text 16,000 characters except identifiers/revisions 128; lowercase 64-hex SHA-256 fields. Times finite/nonnegative; counts nonnegative. |
| Evidence references | Canonical relative POSIX paths, at most 1,024 characters, beneath `pr_evidence/pr2-20/<subject_digest>/`; no traversal, absolute paths, credentials or authenticated URLs. Split large plans/samples using existing chunk writer. |

Cardinality observations use existing `save_observation` files, not a canonical
DTO. Record the counts named in §3 as nonnegative JSON integers, exact predicate
and catalog text, fixture/profile references and before/after manifests. An
absent measurement is unavailable, never zero. Reuse existing MigrationEvidence
for migration observations; do not extend its schema silently.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

| Existing column | SQL type | Guard retained |
| --- | --- | --- |
| review_issues.id | UUID NOT NULL | `review_issues_pkey` |
| review_record_id | UUID NOT NULL | `review_issues_review_record_id_fkey`, ON DELETE RESTRICT; `review_issues_review_record_id_ordinal_key` |
| severity | VARCHAR(16) NOT NULL | `review_issues_severity_check`: INFO/MINOR/MAJOR/BLOCKING |
| status | VARCHAR(16) NOT NULL | Current `ck_b08_issue_status`: OPEN/ADDRESSED/DISMISSED; historical `review_issues_status_check`: OPEN only |
| ordinal | INTEGER NOT NULL | `review_issues_ordinal_check`, ordinal >= 0 |

```sql
-- Candidate only; no execution authorized by this draft.
CREATE INDEX ix_pr220_issue_open_blocking_review
  ON review_issues USING btree (review_record_id)
  WHERE status = 'OPEN' AND severity = 'BLOCKING';
-- Index-only downgrade:
DROP INDEX ix_pr220_issue_open_blocking_review;
```

No `IF NOT EXISTS` masking a wrong definition; preflight detects equivalent or
conflicting indexes. Keep `ix_pr214_issue_review_severity`, `uq_b08_issue_open`,
`uq_b08_issue_terminal`, `ck_b08_event_shape`, concrete event FKs and all guards.
Keep `b08_complete_issue` and `b08_complete_event`, and the deferred
`pr215_complete_decision`, `pr215_complete_conclusion`, `pr215_complete_review`
constraint triggers from [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py).
All remain DEFERRABLE INITIALLY DEFERRED; B29 adds no new trigger. Exercise final
deferred checks as well as `SET CONSTRAINTS ALL IMMEDIATE` regressions.

### 12.2 Exact lock order and transactions

B29 adds **no command** and **no lock**. The measurement wrapper does not acquire
locks before calling services. Existing commands retain their complete owning
protocol, including trigger and FK locks. Do not copy the older PR2-20 target-first
sequence over current SHARE-first code.

| Exercised operation | Ordered existing protocol to preserve |
| --- | --- |
| `record_issue_disposition` | READ COMMITTED UoW → FIRST SQL `LOCK TABLE <REVISION_SNAPSHOT_TABLES> IN SHARE MODE` from `revision_action_repository.py` via `internal_review_repository.prepare_disposition` → local timeouts 10s/30s → advisory `b08:disposition:<event id>` → authority/replay/basis reads → distinct old/new review IDs sorted by UUID string, each FOR SHARE → union of primary Issue and selected re-review Issues sorted by UUID string, primary FOR UPDATE, others FOR SHARE → reread/validate → event INSERT and trigger projection → constraints/readback/fresh authorization → commit. No action or scientific target/parent/project row lock. |
| `record_decision` (internal PROCEED) | READ COMMITTED configured by `configure_approval_transaction` → FIRST SQL `B09_SHARE_SQL` from `approval_repository.py` → local timeouts 10s/30s → advisory `pr215:decision:<id>` → advisory `pr216:scope:<project>:<decision_type>` → exact conclusion version FOR UPDATE → authority/closure/history and complete reviews → existing typed Decision/basis INSERTs and deferred checks → fresh authorization → commit. Existing replay closes writer and opens historical read; no execution on replay. |
| `record_ready_for_submission_decision` / `record_prepare_submission_decision` | READ COMMITTED → FIRST SQL `B11_SHARE_SQL` from `decision_repository.py` → timeouts 10s/30s → respective advisory `b11:decision:<id>` / `b12:decision:<id>` → exact manuscript FOR UPDATE → project FOR SHARE → publication FOR SHARE → existing closure, complete basis and blocker verification → owning INSERTs/checks/fresh authorization → commit. |
| Novelty fixture writes, if exercised | `novelty_repository.prepare`: READ COMMITTED → FIRST SQL SHARE over literal `N` → timeouts 10s/30s → advisory `pr218:<kind>:<id>` → ClaimVersion FOR UPDATE for non-coverage writes → existing authorization/material validation/INSERT/readback → commit. No change to this inventory. |
| Exact/history reads and evidence SELECT/EXPLAIN | One REPEATABLE READ, READ ONLY snapshot before data access; plain authorization/closure/history reads; no explicit table/advisory/row lock in nested helpers. Fresh DB-time entitlement before returning service results. Observer SELECT/EXPLAIN adds no explicit locks. |
| Alembic upgrade/downgrade | Existing migration transaction → catalog preflight → CREATE INDEX / DROP INDEX → catalog validation → commit. PostgreSQL acquires its normal DDL locks; this is not an Application UoW or a read path. |

Literal inventories referenced above are the tuples in the named source files,
not newly assembled subsets. Revalidate them and capture emitted SQL at execution
freeze. If any owning command has changed, reconcile this contract first rather
than rewriting its lock protocol inside B29. Other commands are outside this
measurement slice; fixture setup still uses their owning service protocols.

### 12.3 Ordered build steps and module paths

1. Freeze approved subject, evidence/profile and actual Alembic head in the future
   execution pack. Review B08/ADR-0016, current catalog and equivalent indexes.
2. Extend `tests/integration/phase2/pr2_20_support.py` and
   `tests/integration/phase2/test_pr2_20_catalog_plans.py` for cardinality and
   candidate comparisons; reuse `b08_support.py`, owning services and
   `tests/disposable_postgres.py`. Retain absence assertion in baseline tests.
3. Reuse `tests/contracts/pr2_20_evidence.py`, `pr2_20_scaled.py` and
   `tests/e2e/test_pr2_20_benchmark.py` for bounded files and declared profiles.
   Collect evidence, then obtain explicit owner index admission. No production
   DDL precedes this decision.
4. Only if admitted, append
   `migrations/versions/<assigned_revision>_pr2_20_measured_indexes.py`, following
   PR2-20's existing naming plan. Assign exact revision/down_revision at execution
   freeze; do not guess a number or edit 0040/0053. Implement §12.1 only.
5. Add/adjust the cases below, separating pre-index baseline and admitted-index
   fixtures. No changes to `application/decision.py`, `internal_review.py`,
   `application/ports.py`, repository lock helpers, API or CLI are authorized.
6. Run focused checks, attach exact results and independent spec/diff/evidence
   review, resolve P0/P1, and stop. Whole-suite evidence belongs to the external
   loop for the present documentation task.

### 12.4 Test artifacts and required cases

Paths below exist; candidate-specific extensions are planned only.

| File(s) | Required cases |
| --- | --- |
| `tests/unit/phase2/test_pr2_20_evidence.py` | Closed layouts, bounds, missing/nonfinite measurements, distinct non-PASS statuses, secret redaction and evidence path rejection; no synthetic PASS. |
| `tests/architecture/test_pr2_20_boundaries.py`, `test_b08_issue_disposition.py` | No new canonical entity/command/DTO/ORM exposure; observer nonmutation; reads and nested verifiers lock-free; historical migrations unchanged. |
| `tests/integration/phase2/test_pr2_20_catalog_plans.py` | Baseline absent/candidate exact nonunique B-tree/predicate/validity; equivalent-index preflight; realistic selectivities and terminal history; complete one-blocker-among-many gate; DTO/error/query-count/manifest parity. |
| `tests/integration/phase2/test_pr2_20_migrations.py` | Empty and populated legal B08 upgrade; all constraints/triggers retained; interruption/DDL timeout rollback; reconnect; index-only downgrade retains terminal history; historical 0040 checkpoint remains all OPEN. |
| `tests/integration/phase2/test_b08_schema.py`, `test_b08_issue_disposition.py`, `test_b08_issue_history.py`, `test_b08_concurrency.py` | Terminal index entry removal on legal disposition, root/terminal projection integrity; forged terminal rows fail; same transaction late concern/deferred checks; both actual writer commit orders and unchanged lock ordering; historical read snapshot and denied replay. |
| `tests/integration/phase2/test_pr2_15_decision.py`, `test_pr2_15_decision_schema.py`, `test_pr2_15_coordination.py`, `test_pr2_20_governance_races.py` | Exact complete review scope; blocker denial/no partial effect; terminal history validation; zero-Issue review and late blocker INSERT races; deferred Decision-basis integrity. |
| `tests/integration/phase2/test_b11_readiness_decision.py`, `test_b11_readiness_races.py` | Direct/upstream exact-version blocker coverage and both commit orders; no favorable-subset filtering. |
| `tests/e2e/test_pr2_20_benchmark.py` | Before/after declared profiles, 1/4 workers, repetitions, buffers/storage/write costs; noisy or missing large-profile evidence never admission. |

Future implementation checks: Ruff lint/format, Pyright, unit and architecture
tests, then these owning PostgreSQL suites using fixture-owned disposable PG18.
Record exact commands, collected/pass/fail/error/skip counts and environment;
large opt-in benchmark skips remain NOT RUN measurement. Never use SQLite.

### 12.5 Not in this slice

Issue disposition/reopening, new manuscript disposition, review selection or
severity changes; scientific validity overrides; new Approval/Decision purposes;
new locks/retries/isolation; query rewrites or dropping the composite index;
CONCURRENTLY, autocommit migration machinery, online tuning infrastructure;
new canonical tables/JSON semantics, APIs/CLI, runtime dependencies, external
effects, Phase 3 work or a Phase 2 exit declaration.

## 13. Open questions for the owner — override register

| Admission point | Draft decision awaiting approval |
| --- | --- |
| Is the candidate worth installing? | Decide from actual cardinality/plans, service benefit and write/storage cost; no presumed yes. |
| Exact deployment | Future execution pack pins revision/predecessor, timeout/window, rollback and durable owner admission evidence. |
| Unsupported benefit claim or required query rewrite | Reject/defer candidate or request a separate contract; never broaden this slice. |

## 14. Documentation verification note

Only this draft is authored. Verification results reported with this task concern
the current baseline, not candidate implementation or admission. No migration,
test, source, architecture or governing Harness file is changed here.

Observed baseline verification (2026-10-18): the commands below use prefix
`PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/`
immediately before the executable. This reads the existing shared tool environment;
it does not establish a successfully synced environment for this checkout.

| Exact command after that prefix | Observed result |
| --- | --- |
| `ruff check .` | Exit 0; All checks passed. |
| `ruff format --check .` | Exit 0; 639 files already formatted. |
| `pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `pytest -o addopts='' -q tests/unit tests/architecture` | Exit 1; 5,104 passed, 5 failed, 12 errors, 8 warnings, 69.20s. |
| `pytest -o addopts='' -q tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_pr2_15_decision_schema.py` | Exit 1; 56 setup errors, 1.31s; no PostgreSQL acceptance. |
| `pytest -o addopts='' -q --tb=short tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence` | Diagnostic rerun: exit 1; 1 failed, 1 error, 1 warning, 9.00s. |

The static-acceptance test launches Pyright without the standalone venv override
and reports missing imports against the empty local `.venv`. Four HG1 socket
tests fail with sandbox PermissionError. The 12 architecture and 56 PostgreSQL
setup errors require an unset `RB_TEST_ADMIN_URL` (or owning alias). No database
selector was guessed and no test failure was repaired in this documentation task.

Initial `uv --cache-dir /tmp/b29-uv-cache run --offline --no-sync` attempts for
`ruff check .`, `ruff format --check .`, `pyright` and
`pytest -o addopts='' -q tests/unit tests/architecture` each exited 2 because
the local tools were absent. `uv --cache-dir <cache> sync --locked --offline
--group dev` exited 1 for each of `/tmp/b29-uv-cache`,
`/tmp/researchbase-uv-cache`, `/tmp/rb-lane22-uv`, `/tmp/b08-uv-cache`:
required wheels were unavailable offline. No dependency definition was changed.

A local Python audit checked every Markdown link/anchor and all 14 HTTP/CLI
mapping rows against the imported source: 19 links/anchors passed, balanced code
fences, 14 matching mappings. `git diff --check` exited 0. The only authored
change is this draft. The whole test suite was not run; its evidence is reserved
for the external loop.
