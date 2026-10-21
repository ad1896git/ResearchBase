# B09 first-slice implementation evidence — 2026-10-16

> Historical lane evidence. Integrated head: `0056_b10_reconsideration`.
> Owner-authorized remediation on 2026-10-17 preserves B09 SQL, composes B10's
> existing Decision policies with B07/B11, and removes both workaround revisions.
> Current verification is in `docs/verification/batch-c/integration-evidence.md`.

Owner authorization: [approved B09 contract](../../proposals/B09_Approval_Tuples_Contract_DRAFT.md).
This evidence covers the authorized first slice, not full B09/Phase 2 acceptance.

Implemented the three finite purpose/target/command shapes, closed optional-target
DTOs, unchanged literal decision hashes, new-write bounds, project/purpose
rejection fences (including older pending requests), atomic grant staleness/events,
and historical replay with timestamped current usability. No consumption,
reconsideration, Publication transition, consent capture, submission effect or
transport surface was added.

The single forward revision is `0052_b09_approval_tuples`, directly after inspected
head `0051_b06_revision_action`. No accepted migration was edited. The forward
migration preserves populated historical hashes and staleness, validates narrowly
identified old CHECK definitions before replacing them, and refuses populated
rollback. Other migration-related edits update head expectations or append
inventory entries only, with required formatter normalization.

Writes use READ COMMITTED, disabled autoflush, the fixed 43-table SHARE inventory
as the first transactional SQL statement, then UUID/scope/target/Publication/
request/ordered-grant exclusion. Direct SQL guards enforce preheld inventory and
isolation. Reads/replay use REPEATABLE READ, READ ONLY and plain SELECT paths;
no explicit table, advisory or row locks or status maintenance occur there.
A duplicate discovered by a writer closes that UoW before reopening historical
readback. Final deferred validation, live authorization and conditional expiry
precede commit. Retry classification remains limited to 40001/40P01, three
fresh attempts; timeout/business errors are not retried.

Existing equivalents/substitutions used:

- The inspected head is 0051; B09 is the new 0052 revision.
- `configure_revision_transaction` / `configure_revision_connection` provide the
  existing pre-BEGIN connection timeout configuration. B09's typed UoW preparation
  reuses this mechanism, bounding the first SHARE wait before its later SET LOCAL.
- `enable_revision_action_snapshot_reads` supplies protected plain closure reads.
  B09 adds plain target/review variants instead of invoking locking Decision helpers.
- `InternalReviewService._manuscript_target` and `_verify_manuscript_review` are
  the existing B05 exact-target/review paths; the former invokes B04
  `ManuscriptFreezeService.verify_in_uow` for full seal/CAS/transitive verification.
  These are used within the same UoW, without a nested service transaction.
- The guide describes a B04/B05 preheld-inventory guard pattern, but no reusable SQL
  helper exists in those revisions. B09 adds its own fixed-inventory precondition.

Matching manuscript Decision commands/basis remain a separately authorized,
unimplemented dependency. Both new manuscript purposes deny missing/mismatched
basis with DECISION_BASIS_INVALID and produce no approval records; the test uses
an actually B04-frozen manuscript. The in-UoW manuscript lifecycle path denies an
unavailable required state with APPROVAL_GATE_FAILED, but cannot be accepted end
to end until its matching Decision extension exists. No fixture fabricates that
extension or a Publication lifecycle transition. API/CLI exposure is deferred by
§12.3 step 5 and was not added.

Read-only sub-agents investigated existing SQL/application/test paths and reviewed
the final source/migration; the primary agent performed all writes and test runs.
The final reviews reported no remaining concrete P0/P1. Earlier findings concerning
final expiry, projection time, error normalization and forged nested-trigger events
were corrected and tested.

All commands below ran in this repository, using its installed environment and
existing disposable PostgreSQL configuration. `UV_CACHE_DIR` redirects the sandbox-
inaccessible default cache; `--no-sync` uses the installed local environment.
The server version query returned **18.6 (Homebrew)**. No full-suite invocation,
commit, push or branch creation occurred.

| Exact command | Observed final result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync ruff check .` | All checks passed |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync ruff format --check .` | 573 files already formatted |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pyright` | 0 errors, 0 warnings, 0 informations |
| `git diff --check` | exit 0, no output |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py --tb=short` | 2397 passed, 41 warnings in 54.43s |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b05_manuscript_review.py --tb=short` | 182 passed, 1 skipped, 555 warnings in 195.38s |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py --tb=short` | 199 passed, 474 warnings in 177.26s |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pytest tests/integration/phase2/test_b09_approval_schema.py --tb=short` | 16 passed, 55 warnings in 18.78s |
| `UV_CACHE_DIR=/tmp/rb-b09-cache uv run --no-sync pytest tests/integration/phase2/test_b09_approval_concurrency.py --tb=short` | 15 passed, 42 warnings in 18.63s |

The final two focused runs cover the final schema fixture refinement and additional
isolation/uncertain-commit concurrency cases; their counts overlap the combined
PostgreSQL run and must not be summed as unique tests. The single skipped test is
the inherited B05 SUPERSEDED-manuscript case, explicitly awaiting a later
supersession contract; it is not evidence of manuscript tuple acceptance. Warnings
are the inherited Alembic `path_separator` deprecation.

Retained terminal output: [unit/architecture](unit-architecture.txt),
[focused PostgreSQL](focused-postgresql.txt), [head regressions](head-regressions.txt),
[final schema](schema.txt), [final concurrency](concurrency.txt).

Earlier development runs failed on the new SQL CASE expression, missing direct-SQL
preheld inventory, old head expectations, in-progress lint/type errors, and the
manuscript fixture's readback field name. Those were corrected before the final
runs above. Earlier failures are not counted as passing evidence.

STOP: no later-slice effects or dependency implementation is authorized here.
