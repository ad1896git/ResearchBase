# B11 first-slice implementation evidence — 2026-10-16

Authority: owner authorization in the task and the approved status in
[the B11 contract](../proposals/B11_Ready_For_Submission_Decision_Contract_DRAFT.md).
This records the bounded readiness judgment implementation, not Phase 2 or
publication-readiness gate acceptance. The initial task reserved the whole-suite run for the external loop; the owner
subsequently requested the exact full check during reviewer remediation below.

## Implemented boundary

- Added closed readiness command/query/readback DTOs and the two DecisionService
  methods. Existing literal R2 material builders and release vectors are unchanged.
- Added only `decision_basis_manuscripts` in forward migration
  `0054_b11_ready_for_submission`, after actual head `0053_b08_issue_disposition`.
  It retains the accepted release and REVISION_RESPONSE branches. Immutable,
  same-transaction typed basis, exact-purpose scope exclusion and deferred complete
  review-set guards cover normal-role SQL. Functions pin canonical schema lookup;
  a temporary-table inventory spoof is rejected.
- Writes start with the literal, frozen SHARE inventory in READ COMMITTED, followed
  by request advisory, exact manuscript UPDATE, project SHARE and publication SHARE
  locks. Connection timeout settings precede BEGIN. Reads use one REPEATABLE READ,
  READ ONLY snapshot and plain nested queries; tests inspect SQL and `pg_locks`.
- New judgments verify B04 retained bytes/seals/closure/current validity, complete
  adverse-inclusive B05 reviews, material-author independence and direct/upstream
  blockers. B08 terminal history is verified before excluding closed upstream
  concerns. Manuscript disposition remains unavailable.
- Replay/history preserves saved membership and hashes, reports timestamped current
  diagnostics, and requires current read entitlement. Named primary-key collisions
  roll back before a fresh authorized history comparison. Only 40001/40P01 retry,
  with three fresh UoWs maximum; uncertain commits recover with the same UUID.
- ArtifactStore is injected through existing composition; no API/CLI commands,
  publication transitions, approvals, grants, receipts or external effects added.

## Baseline substitutions

1. The inspected draft predates accepted B07/B08. The actual predecessor policy
   constraint is `ck_b07_decision_tuple`, replacing the original 0042 generated
   checks. B11 preserves its exact release and revision tuples. Downgrade restores
   B07 dispatch byte-for-byte; AST equality and the migration inventory digest
   were checked.
2. B08 is implemented here. Its `b08_check_history` and Application history verifier
   are reused; no B08 implementation or manuscript-disposition extension was added.
3. Existing `revision_decision_text` is the equivalent NFC/nonblank/16,000-character
   validator; readiness wraps it. Existing Decision basis references already admit
   ManuscriptVersion, so the material builders required no modification.
4. The existing Decision UoW property is an `Any` port alongside
   `DecisionConcernTraversal`, rather than a named full DecisionRepository protocol.
   A bounded `ReadinessDecisionRepository` protocol documents the additive typed
   manuscript operations. Existing revision transaction/snapshot adapters are reused.
5. Composition had no direct DecisionService construction. Optional `decisions`
   fields now construct it with the existing store in API/CLI service bundles,
   without adding transport commands.
6. B04 still restricts actual publication lifecycle to DRAFTING. Future-stage
   Application policy tests use read projections; B11 does not enable those states.

## Verification environment

All commands ran inside this repository using its installed `.venv` environment;
no dependencies or lockfile changed. PostgreSQL tests used disposable databases
through `RB_TEST_ADMIN_URL` pointing to local `localhost:5432/postgres` (credentials
omitted here), never retained scientific installations. Normal-role SQL tests use
unique NOLOGIN NOSUPERUSER roles. Server probe:

```sh
/opt/homebrew/opt/postgresql@18/bin/psql -h localhost -p 5432 -U researchbase -d postgres -Atc 'select version()'
```

Observed: PostgreSQL 18.6 (Homebrew), aarch64-apple-darwin27.0.0, 64-bit.

## Exact focused commands and final observed results

| Command | Result |
| --- | --- |
| `.venv/bin/ruff check .` | All checks passed. |
| `.venv/bin/ruff format --check .` | 595 files already formatted. |
| `.venv/bin/pyright` | 0 errors, 0 warnings, 0 informations. |
| `.venv/bin/python -m pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -q` | 4,806 passed; 41 warnings; 50.74s. |
| `git diff --check` | Exit 0. |

The three PostgreSQL command groups below overlap; their counts must not be added
as a unique-test total.

B11 final run:

```sh
.venv/bin/python -m pytest tests/integration/phase2/test_b11_readiness_decision.py tests/integration/phase2/test_b11_readiness_replay.py tests/integration/phase2/test_b11_readiness_schema.py tests/integration/phase2/test_b11_readiness_races.py -o addopts='' -q
```

Observed: **109 passed, 441 warnings, 80.47s**.

Dependent regression run:

```sh
.venv/bin/python -m pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b05_review_races.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b08_issue_history.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b08_concurrency.py -o addopts='' -q
```

Observed: **418 passed, 1 skipped, 1,348 warnings, 471.81s**. The existing skip is
B04 SUPERSEDED manuscript history, which remains deferred.

Touched migration-inventory suites and final shared-helper compatibility run:

```sh
.venv/bin/python -m pytest tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b06_revision_concurrency.py -o addopts='' -q
```

Observed: **291 passed, 753 warnings, 224.35s**.

## Review and execution limits

Read-only sub-agent reviews compared the contract and diff. The concrete P1
finding (legacy project advisory/UPDATE helper) was fixed with a dedicated project
SHARE helper. The readback DTO's readiness-specific shape was tightened after a
P2 finding. Final source reviews reported no open P0/P1. Only the primary agent
wrote files.

Development runs exposed test-fixture mistakes, an inventory omission and source
inspection invalidated by editing a loaded module during a test run; the final
unit/architecture result above supersedes those failures. An early membership-race
barrier also reproduced the contract's acknowledged older-writer deadlock: a
partial SHARE inventory and a target-first writer can form a cycle. Intended
commit-order tests now pause after the complete membership projection/event
mutation; separate fault injection verifies bounded 40001/40P01 retry. No claim of
deadlock freedom or timeout retry is made.

At the initial handoff, no whole-suite run had been performed. The focused runs
above did not establish a full-suite PASS and omitted `test_b07_schema.py`. The
reviewer subsequently reported a full-check failure; remediation and the newly
authorized full run are recorded below. No commit, push, branch creation or
retained-data mutation was performed. Implementation remains within B11's first slice.


## Reviewer remediation — full-check rejection and repair

The reviewer reported **1 failed, 8,932 passed**, with
`test_b07_schema.py::test_empty_forward_upgrade_and_downgrade` failing. This failure
was absent from the initial focused evidence because that file was not run.
The initial focused results must not be read as a full-suite acceptance claim.

Reproduction confirmed the exact cause: upgrading from 0051 to `head` now adds
`decision_basis_manuscripts` alongside B07's three tables. The stale added-table
inventory omitted that relation. The repair appends that single expected table
at the assertion; B07's three-table FK inspection and seven-FK expectation remain
unchanged. No migration or production implementation was changed in remediation.

The test-result commands in this remediation use `UV_CACHE_DIR="$PWD/.uv-cache"`.
An initial default-cache launch exited 2 before test collection because the external
cache is not writable in this sandbox; it is not test evidence. PostgreSQL retains
the explicit disposable local admin selector described above.

| Exact command | Observed result |
| --- | --- |
| `uv run pytest -o addopts='' -q tests/integration/phase2/test_b07_schema.py` (before repair) | Exit 1: 1 failed, 18 passed, 60 warnings, 13.10s. |
| `uv run pytest -o addopts='' -q tests/integration/phase2/test_b07_schema.py` (after repair) | Exit 0: 19 passed, 62 warnings, 12.72s. |
| `uv run pytest -o addopts='' -q tests/integration/phase2/test_b11_readiness_schema.py::test_downgrade_restores_live_0053_function_definitions` | Exit 0: 1 passed, 5 warnings, 0.72s. |

The new live PostgreSQL test captures `pg_get_functiondef` and `pg_proc.proconfig`
for `public.pr215_basis_guard()` and `public.pr215_complete_basis()` at actual 0053.
Both have `proconfig IS NULL`, with no pinned search path. It upgrades to 0054 and
asserts the new `pg_catalog, public, pg_temp` setting, downgrades to 0053 and compares
both complete definitions/settings for exact equality, then re-upgrades and compares
again. Thus 0054 faithfully restores its predecessor; it does not discard a 0053
search-path clause. `_RESTORE_DISPATCH` also remains byte-identical to the B07
installed dispatch after inventory substitution; 0053 does not redefine it.

The required proposal line is present at line 3:

```text
**Status: APPROVED by owner 2026-10-16 — first slice authorized for implementation**
```

Owner-requested full check:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Observed: **exit 0**. Pyright: **0 errors, 0 warnings, 0 informations**;
Ruff format: **595 files already formatted**; Ruff check: **All checks passed**.
Pytest: **8,934 passed, 50 skipped, 5,368 warnings, 6,400.87s (1:46:40)**.
This is the executed full-suite result following repair, superseding the reviewer's
reported failing check. No P0/P1 finding remains open from that review.
