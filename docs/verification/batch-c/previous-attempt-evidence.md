# Batch C integration evidence — 2026-10-16

Status: **OPEN P1 / not accepted**. No full-suite or gate-success claim.

The incoming B09/B10 migrations were renumbered to 0055/0056. Their complete
non-metadata bytes match the incoming index copies; a unit regression pins the
normalized SHA-256 digests. B07/B08/B11 migration files remain unchanged.
Application/domain/repository conflicts retain both lanes' commands and typed
ports. Issue inserts now use the later of the requested timestamp and the saved
review timestamp, preserving B10's DB clock and B08's chronology invariant.

The current linear head is `0057_batch_c_dispatch`. Two compatibility migrations
restore the legacy constraint names expected by B10 and compose the existing
finite Decision policies/dispatch branches. The composed dispatch retains B11's
fixed search path. CI, baseline, lineage allowlists, migration expectations and
inventory were updated.

## Open P1: populated B07/B11 upgrade

Target: `migrations/versions/0056_b10_reconsideration.py`,
`UPGRADE_SQL`, `ADD CONSTRAINT ck_b10_decision_pair`.

B10 adds an immediately validated release/reconsideration-only CHECK. A retained
`REVISION_RESPONSE` or `READY_FOR_SUBMISSION` row fails this CHECK before a later
compatibility migration can widen it. PostgreSQL reports SQLSTATE `23514`.
This violates populated cross-phase compatibility if reported as a successful
integration. The incoming B10 DDL is still byte-identical apart from metadata.
The owner was asked to authorize the narrow constraint/dispatch compatibility
edits; no affirmative response has been received. A concrete, unapplied proposal
is at `docs/verification/batch-c/proposed-b10-compatibility.diff`. Applying that
proposal would also remove the two workaround migrations and make B09 directly
follow B11. Do not bypass validation or mutate retained scientific history to
make this check pass.

B08 migration regressions now explicitly exercise their historical checkpoints;
the populated test still exercises upgrading retained B07 data to the integrated
head and exposes this blocker. It is deliberately not weakened into a pass.

## Environment and checks

All commands ran from the repository root with `UV_CACHE_DIR=.uv-cache`.
PostgreSQL: **18.6 (Homebrew), aarch64-apple-darwin27.0.0**. Integration fixtures
create/drop isolated PostgreSQL databases. Results below are separate runs and
must not be summed as distinct coverage.

```sh
UV_CACHE_DIR=.uv-cache uv run alembic heads
```

Result: exactly `0057_batch_c_dispatch (head)`.

```sh
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run pyright
```

Results: **608 files already formatted**; **All checks passed!**;
**0 errors, 0 warnings, 0 informations**.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture tests/test_architecture.py
```

Result: **4870 passed, 42 warnings in 67.87s**. Later migration/history checks:

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/test_ci_migration_head.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/architecture/test_import_boundaries.py tests/test_architecture.py
```

Result: **36 passed, 4 warnings in 1.16s**.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_b10_reconsideration_concurrency.py -x
```

Result: **122 passed, 366 warnings in 163.75s**.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py -x
```

Result: **202 passed, 503 warnings in 180.65s**.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade tests/integration/phase2/test_b07_schema.py::test_revision_history_refuses_downgrade_and_late_append tests/integration/phase2/test_b11_readiness_schema.py::test_downgrade_restores_live_0053_function_definitions
```

Result: **4 passed, 20 warnings in 4.08s**. Includes empty upgrade to head,
downgrade to base, re-upgrade; original checkpoint function restoration; composed
head roundtrip; and explicit refusal to discard retained Decision history.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b10_reconsideration_schema.py tests/integration/phase2/test_b11_readiness_schema.py
```

Final result: **67 passed, 248 warnings in 89.10s**. An earlier run reported
**1 failed, 66 passed** because of the obsolete assumption that B11 checkpoint
function definitions must equal the integrated head. That regression now checks
both checkpoint restoration and the composed head. B10's
forged-predecessor test now also asserts B07's earlier SQL rejection, retaining
B10's historical-corruption checks via a privileged disposable negative fixture.

Full suite: **not run**, as requested. The loop's subsequent check owns that
result; none has been supplied to this session.

Git index: the working files contain no merge markers and `git diff --check HEAD`
is clean. Marking index conflicts resolved was attempted, but the filesystem
sandbox denied creation of `.git/index.lock`. The index therefore still reports
unmerged entries. No commit, push, or branch was created.

## Additional focused lane verification

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b07_schema.py tests/integration/phase2/test_b07_concern_carry_forward.py tests/integration/phase2/test_b07_concurrency.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b08_issue_history.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b08_concurrency.py tests/integration/phase2/test_b11_readiness_decision.py tests/integration/phase2/test_b11_readiness_replay.py tests/integration/phase2/test_b11_readiness_races.py
```

Initial result: **8 failed, 298 passed, 1005 warnings in 515.42s**. This run started
before the migration-checkpoint and cross-lane race test fixes. Seven failures
were obsolete table/checkpoint/lock-order assumptions; the eighth is the open
populated-upgrade blocker. Targeted final rerun is recorded below.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b08_concurrency.py::test_release_and_disposition_keep_independent_blocker_gate_both_orders tests/integration/phase2/test_b08_concurrency.py::test_approval_and_disposition_both_orders_preserve_grant_gate
```

Result: **4 passed, 12 warnings in 13.71s**. The tests witness actual PostgreSQL
relation-lock waits under B09's first-SHARE protocol. Approval/release before a
disposition fails on the still-open blocker; a waiting gate after the disposition
commits succeeds. No stale approval grant is admitted.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b11_readiness_decision.py -x
```

Result: **33 passed, 131 warnings in 37.71s**.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade tests/integration/phase2/test_b07_schema.py::test_revision_history_refuses_downgrade_and_late_append tests/integration/phase2/test_b08_schema.py::test_populated_b07_upgrade_open_downgrade_and_terminal_refusal tests/integration/phase2/test_b08_schema.py::test_upgrade_preflight_refuses_corrupt_legacy_root_without_partial_ddl tests/integration/phase2/test_b08_concurrency.py::test_release_and_disposition_keep_independent_blocker_gate_both_orders tests/integration/phase2/test_b08_concurrency.py::test_approval_and_disposition_both_orders_preserve_grant_gate
```

Final result: **1 failed, 7 passed, 34 warnings in 12.47s**. The sole failure is
`test_populated_b07_upgrade_open_downgrade_and_terminal_refusal`: B10's validated
`ck_b10_decision_pair` rejects retained `REVISION_RESPONSE` rows (SQLSTATE `23514`).
The other seven initially failing lane cases now pass together. This is an open
P1, not a passing integration or permission to skip that case in the full loop.
