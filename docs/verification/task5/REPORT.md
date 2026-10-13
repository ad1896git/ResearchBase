# Task 5 — PostgreSQL test-suite verification

Status: final verification complete, **suite FAIL**. Nine P1 production schema gaps remain under the explicit no-migrations rule. No gate acceptance is claimed.

## Environment and scope

PostgreSQL 18.6 (Homebrew), Python 3.12, repository uv environment.
`UV_CACHE_DIR="$PWD/.uv-cache"` is required because this session cannot access the default user cache. No dependencies were added.

The interrupted changes were reviewed against AGENTS.md and applicable architecture/execution contracts. Three sub-agents reviewed disjoint groups read-only; the primary agent is the only writer. No migrations, architecture documents, accepted transaction semantics, branches, commits or remote state were changed.

All PostgreSQL invocations use:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

## Completed resumed full run (before the additional repairs)

Command: `uv run pytest -o addopts='' -q -rfE -p no:cacheprovider` with the environment above.
`full-resumed.log`: **4911 passed, 33 failed, 0 errors, 3 skipped**, 2535 warnings,
4705.04 seconds (1:18:25), exit 1, 4947 cases. This began with the inherited partial
changes; it is not an untouched HEAD benchmark. The original interrupted run has
no complete full-suite counts.

Intermediate `full-after.log`: **4913 passed, 32 failed, 0 errors, 3 skipped**,
2536 warnings, 4702.20 seconds (1:18:22), exit 1, 4948 cases. This started after the
UTC and transaction-identity repairs but before the later fixture corrections.

Intermediate `full-final.log`: **4934 passed, 11 failed, 0 errors, 3 skipped**,
2539 warnings, 4744.10 seconds (1:19:04), exit 1. The two additional failures beyond
the nine schema blockers are the old top-level architecture scan and stale HG1
proof timestamp; this run started before those late fixes and before enabling
the two disposable migration cases. It is not verification of the final tree.

## Final full run on all permitted fixes

Exact command with the environment above:

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider > docs/verification/task5/full-verified.log 2>&1
```

**4938 passed, 9 failed, 0 errors, 1 skipped**, 2541 warnings,
4770.74 seconds (1:19:30), exit 1, 4948 cases. All nine failures match
`remaining-schema-failures.txt`; eight are physical schema inventory/index cases
and one is the concrete scoped-FK case. The original protective expectations
remain enabled. This run includes every permitted source/test correction.

| Full run | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Resumed baseline, inherited changes present | 4911 | 33 | 0 | 3 |
| Final permitted fixes | 4938 | 9 | 0 | 1 |

One additional timezone parameter was collected; two previously skipped
historical migration tests now execute against owned disposable databases.
The interrupted original attempt has no complete counts.

## Original interrupted evidence

The inherited `full-before.log` was interrupted: no complete full-suite counts exist. Its progress records 826 pass markers, 34 failure markers, 0 error markers and 1 skip marker, ending before 18%. These are partial observations, not full-suite totals.

Inherited `phase1-integration.log`: 914 passed, 2 failed, 0 errors; failures were exact Phase1 index inventory checks against an additive Phase2 catalog. Inherited focused evidence was reverified during this resumed task.

`challenge-timezone-red.log`: 1 failed, 0 passed, 0 errors. The existing challenge proof failed its UTC-offset assertion under America/New_York (`-04:00` instead of UTC).

## Failure groups and reviewed fixes

| Group | Classification | Evidence and change |
|---|---|---|
| Exhaustive stable error mapping | (b) obsolete expectation | Add five already authorized Phase2 errors to explicit HTTP/CLI expected registries; preserve exhaustive enum/set equality. |
| Migration topology/head | (b) obsolete expectation | Update unique repository-head assertions to accepted 0042, preserve exact target revision/parent/table delta checks; compare installed head for failed downgrade rollback; use fixture revision parameter for populated parent setup. |
| Frozen Phase1 index catalog | (b) obsolete expectation | Verify exact original inventory on disposable DB at frozen 0018; retain exact required index definitions on live head. |
| Enrollment timestamp representation | (a) production bug | Normalize fresh PostgreSQL clock value to UTC in identity persistence adapter; preserve instant and post-lock sampling. Existing expiry proof now runs UTC and America/New_York, retaining zero-offset and no-write assertions. |
| Authority race retry expectation | (b) obsolete expectation | Require explicit first-attempt 40001 rollback followed by a fresh second-attempt FORBIDDEN result and zero effects. Accepted serialization retry contract is unchanged. A same-process rerun reproduced recycled Python transaction-object identity at line480; retained object references prevent recycling and distinct real PostgreSQL transaction IDs prove fresh retries even when a pooled backend is reused. Ten same-process runs passed all 80 cases after correction. |
| Percent-escaped Alembic URL | (c) environment dependence | Use encoded application_name slash over TCP or sockets; assert ConfigParser roundtrip and decoded PostgreSQL SHOW application_name plus database/revision identity. |
| Evidence row representation | (c) environment dependence | Convert SQLAlchemy RowMapping to dict before strict evidence serialization; retain page ordering, IDs, counts and zero provider effects. |
| Provider cancellation fixtures | (b) obsolete expectation | Supply accepted confirmed provider request ID and exact execution/attempt/request-key binding; retain certainty matrix and immutable replay/conflict proofs. |
| Referenced parent deletion | (c) PostgreSQL diagnostic dependence | Accept native 23001 RESTRICT diagnostic and prove it names a real RESTRICT FK to the exact parent; retain unchanged full provenance rows. |
| Exact plan lifecycle/binding fixtures | (b) obsolete expectation | Reuse bound principal rather than duplicate bootstrap; freeze successors to actually supersede originals; explicitly verify old state/current pointer and exact material.plan_id provenance. |

## Completed resumed checks

Exact shell invocations are recorded in `commands.txt`; the final reviewed tracked diff is in `final.diff`.

Every pytest invocation below uses `-o addopts='' -q -rfE -p no:cacheprovider`.

- `uv run pytest tests/unit tests/architecture ...`: 1809 passed, 0 failed, 0 errors (`unit-architecture-resumed.log`); repeated on final tree: 1809 passed in 35.04s (`unit-architecture-final.log`); repeated after all permitted fixture corrections: 1809 passed in 35.92s (`unit-architecture-final2.log`).
- `uv run pytest` for all 14 changed Phase2 files listed in `git diff`: 203 passed, 0 failed, 0 errors (`changed-phase2-resumed.log`).
- `uv run pytest tests/integration/phase2/test_pr2_00_challenges.py tests/integration/phase2/test_pr2_00_concurrency.py tests/integration/phase2/test_pr2_00_identity.py ...`: 8 passed, 0 failed, 0 errors (`challenge-timezone-green.log`).
- `uv run pytest tests/integration/phase2/test_pr2_00_bootstrap.py tests/integration/phase2/test_pr2_00_temporal_auth.py tests/integration/phase2/test_pr2_00_ownership.py tests/integration/phase2/test_pr2_00_identity_guards.py tests/integration/phase2/test_pr2_00_transaction_isolation.py ...`: 20 passed, 0 failed, 0 errors (`identity-clock-regression.log`).
- `uv run pytest tests/integration/test_pr18_hardening.py tests/e2e/test_phase1_failure_recovery.py ...`: 7 passed, 0 failed, 0 errors (`catalog-errors-resumed.log`).
- `uv run pytest tests/integration/phase2/test_pr2_03_effective_authority.py ...`: 8 passed in focused rerun, followed by ten independent runs of 8 passed each (`authority-investigation.log`, `authority-repeat-red.log`). These do not erase the full-run failure.
- `uv run ruff check .`: passed, all checks passed (`ruff-check-final2.log`; repeated after all permitted fixture corrections).
- `uv run ruff format --check .`: passed, 438 files formatted (`ruff-format-final2.log`; repeated after all permitted fixture corrections).
- `uv run pyright`: 0 errors, 0 warnings (`pyright-final2.log`; repeated after all permitted fixture corrections).
- `git diff --check`: passed.

A temporary indentation error in the receipt-field test correction stopped collection: 1 error, no executed tests (`full-final-collection-error.log`, `success-coordinates-green.log`). It was corrected; full collection now finds 4948 tests and focused receipt coordinates pass both cases. The failed collection is not a pass.

One attempted regression invocation named nonexistent `test_pr2_00_application.py`; pytest exited 4 with no tests run. It was corrected to the actual identity test file above. This failed invocation is not a test pass.

## Final static and architecture checks on completed permitted fixes

`uv run pytest tests/unit tests/architecture tests/test_architecture.py
-o addopts='' -q -rfE -p no:cacheprovider`: **1821 passed, 0 failed, 0 errors**
in 35.58 seconds (`unit-architecture-completed-fixes.log`). This includes the
additional top-level architecture file outside `tests/architecture`.

`uv run ruff check .`: PASS. `uv run ruff format --check .`: PASS, 438 files
already formatted. `uv run pyright`: 0 errors, 0 warnings. Exact logs are
`ruff-check-completed-fixes.log`, `ruff-format-completed-fixes.log`,
`pyright-completed-fixes.log`. `git diff --check`: PASS.

## NOT_RUN

`tests/integration/phase2/test_hg1_runner_live.py::test_four_durable_deployments_authenticate_and_clean_up`: requires the authorized four durable M2 installations on another host, evidence at `/Users/onephone/ResearchBaseData`, and that host's PostgreSQL Unix socket on port 55440. Those installations and durable databases are unavailable here. The existing test's opt-in skip is unchanged; no replacement provider, credentials or deployment state was fabricated.

- Final authority same-process verification: ten explicit pytest invocations in one Python process, 8 passed each (80 passed aggregate), 0 failed, 0 errors (`authority-process-repeat-green.log`). The preceding reproduction failed 1 case and passed 7 (`authority-process-repeat-red.log`).

## Additional groups found beyond the interrupted run

- Provider budget event field: (b) incorrect Phase2 field expectation (`event_kind` versus frozen `kind`). Before: 3 failed/3 passed. Corrected exact field only; provider/budget/history/replay assertions unchanged. Related budget and provider suites: 52 passed (`provider-budget-green.log`).
- R8A reservation fixtures: (b) later accepted start-attribution and downgrade guards. Replace backdated initial start with actual one-second execution budget; explicitly initialize the populated 0025↔0024 fixture at 0025. Before: 2 failed/15 passed. Reservation plus both retrieval suites: 45 passed (`reservation-retrieval-green.log`).
- Terminal retrieval immutability: (b) guard precedence expectation. Terminal parent rejects attempt changes with exact P17D3; existing nonterminal companion still proves exact P17D1. Before: 1 failed/13 passed; covered by 45-pass run above.
- Direct-SQL schema negative fixtures: (b) later accepted attribution/sealing guards. Preserve intended rejection/rollback evidence by using valid transient retry reasons, observed retrieval timestamps, and unoccupied query parent; assert exact attribution diagnostic plus a coherent missing-actor FK control. Before: 21 failed/205 passed; after fixture corrections: 8 failed/218 passed (`schema-fixtures-after.log`). Eight production inventory/index failures are unchanged.
- Success receipt coordinates: (b) incorrect Phase2 field expectation (`result_json` versus frozen `result_dto`). Before: 2 failed/0 passed; exact DTO/admission/replay assertions retained (`success-coordinates-investigation.log`, corrected focused rerun: 2 passed (`success-coordinates-green-corrected.log`)).
- Frozen physical schema: (a) genuine production database gaps. Eight inventory/index parameter cases and one concrete scoped-FK case fail. See `SCHEMA-BLOCKERS.md` and read-only `schema-live-catalog.json`. The proper repair requires a migration; the current no-migrations rule prevents applying it. These are FAIL, never NOT_RUN or PASS. A concrete additive repair proposal has been presented for explicit authorization; no migration has been modified.

## Late full-suite portability corrections

- `(b)` Top-level `tests/test_architecture.py` migration/table registry lacked
  exact authorized later references. Added per-file/table exceptions only for
  accepted references and strengthened the `run_versions` prohibition across all
  migrations. Before: 1 failed/18 passed in the paired architecture/HG1 probe.
- `(c)` HG1 positive signed proof used a module-import timestamp. Full-suite
  collection precedes execution by more than the production 15-minute proof
  freshness window. A function-scoped current-time fixture now anchors each real
  signed proof, credentials and time assertions; production freshness and all
  cryptographic/expiry rejection checks remain unchanged.
- `(c)` Two PR11R2 historical migration tests previously skipped because the
  extra `PR11R2_MIGRATION_DB_URL` selector was absent. They now allocate an owned
  disposable PostgreSQL DB per case via the existing fixture, restore its head,
  and drop it. Destructive historical resets never target the shared DB. UV cache
  stays inside the repository. These are runnable here and are **not NOT_RUN**.

Combined final focused command: `uv run pytest tests/test_architecture.py
 tests/unit/test_hg1_identity.py tests/integration/test_pr11r2_migration.py
 -o addopts='' -q -rfE -p no:cacheprovider`: **21 passed, 0 failed, 0 errors** in
12.88 seconds (`late-portability-final.log`). Read-only review found no weakening.

## Database cleanup and remaining authorization boundary

After the final full process exited, all per-test databases from completed runs
had been dropped by their fixtures. Three verified initial interrupted-run
orphans remained; each was dropped via the configured PostgreSQL admin connection
with AUTOCOMMIT. `database-cleanup.log` records exact names and before/after
inventory. **Zero test databases remain**, and the main `researchbase` database
was preserved. No external installation was modified.

The only unimplemented repair is the frozen physical schema group. The user
explicitly prohibits modifying `migrations/`; its correct fix requires a governed
migration. No response authorizing that exception was received. The concrete
reviewable proposal is `SCHEMA-BLOCKERS.md`. These nine executed failures remain
**FAIL**, not NOT_RUN. No migration or architecture document was modified; no
commit, branch or push was created.
