# B14a entry implementation evidence — 2026-10-18

The owner-approved first slice adds exact frozen-manuscript DRAFTING→INTERNAL_REVIEW entry and historical event readback to PublicationService. The proposal status now reads **APPROVED by owner 2026-10-18 — first slice authorized for implementation**.

## Changes and compatibility

- One forward migration, `0060_b14a_publication_entry`, follows actual head `0059_b13_grant_consumption`. Existing migration bytes remain unchanged. Only Publication/event DDL is extended; the exact same-parent manuscript FK, initial/entry uniqueness, retained immutable events, preflight, deferred atomic final graphs and retention-safe downgrade are enforced.
- Closed command/query/result DTOs select the explicit manuscript ID/hash. Entry verifies B04 closure/bytes/current validity, saved applicable review attribution/hash and B08 Issue history. Zero reviews and adverse recommendations are allowed; applicable OPEN BLOCKING Issues deny entry. No Decision, approval, receipt, review or external effect is created.
- Writes use the frozen N literal, W and A in FIRST-SQL order under READ COMMITTED, then command advisory, manuscript and Publication row locks. Fresh DB time governs authorization after waits and constraints. Only 40001/40P01 permit up to three fresh write attempts.
- Exact reads and completed replay use REPEATABLE READ, READ ONLY with plain dependency readers. Scoped saved-seal verification retains literal hash/graph checks while skipping CAS readmission, including source/correction-basis bytes. Saved facts survive later blockers, invalidity and loss of write role. Artifact review verification remains confined to entry; its payload is the already registered architecture-15 payload.
- Head expectations and migration inventories were updated by values/appended entries only, including the CI head expectation. No existing migration, dependency definition, governing Harness file, API route or CLI command was changed.

The guide's existing-equivalent substitutions are recorded here: `configure_revision_transaction(readonly=True)` and `enable_revision_action_snapshot_reads()` supply the snapshot configuration/read toggles; B11 `_readiness_authorize`, applicable-review traversal and B08 history mechanisms supply shared in-UoW policy. Existing Publication had an untyped port; its repository protocol is now explicit. The frozen literal inventory matches current B13, without runtime inheritance.

B14 has no implementation at this head. B14a owns the nullable event manuscript reference; a future B14 migration must preserve it and the entry guards/indexes when widening READY. No B14 file was changed, and real READY/downstream acceptance was not run.

Identity contract 16 reserves authenticated Service/Agent enrollment for a separate reviewed adapter. The existing human binding ceremony cannot enroll an Agent. The shared entry method adds no HUMAN restriction; real HUMAN entry and unbound AGENT denial are tested. Successful enrolled-Agent entry is unavailable and is not claimed as verified. No identity guard was weakened or disabled.

## Exact focused commands and observed results

The focused implementation commands in the following table used this environment prefix (the connected test database URLs were inherited):

```sh
UV_CACHE_DIR=/tmp/researchbase-b14a-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after the common prefix | Observed result | Retained output |
| --- | --- | --- |
| `uv run --no-sync ruff check .` | All checks passed. | [Ruff](b14a-entry-evidence/ruff-check.txt) |
| `uv run --no-sync ruff format --check .` | 646 files already formatted. | [Format](b14a-entry-evidence/ruff-format.txt) |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | 0 errors, 0 warnings, 0 informations. | [Pyright](b14a-entry-evidence/pyright.txt) |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py --tb=short` | 5,180 passed; 42 warnings; 72.06s. | [Unit/architecture](b14a-entry-evidence/unit-architecture.txt) |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b14a_publication_entry.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_b14a_entry_replay.py tests/integration/phase2/test_b14a_entry_concurrency.py --tb=short` | 113 passed; 373 warnings; 102.82s. | [B14a PostgreSQL](b14a-entry-evidence/b14a-postgresql.txt) |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b14a_entry_schema.py --tb=short` | 18 passed; 60 warnings; 13.39s. Adds the corrupt-legacy preflight case after the preceding run; 17 cases overlap. | [Schema follow-up](b14a-entry-evidence/schema-followup.txt) |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b04_*.py tests/integration/phase2/test_b05_*.py tests/integration/phase2/test_b09_*.py tests/integration/phase2/test_b10_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_b12_*.py tests/integration/phase2/test_b13_*.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py --tb=short` | 471 passed, 1 skipped; 1,629 warnings; 530.72s. | [Dependency PostgreSQL](b14a-entry-evidence/dependency-postgresql.txt) |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b11_readiness_decision.py --tb=short` | 54 passed, 1 skipped; 214 warnings; 53.59s. Rechecked after the final entry-only verifier scoping refinement. | [Review regression](b14a-entry-evidence/review-regression.txt) |
| `uv run --no-sync alembic heads` | `0060_b14a_publication_entry (head)` | Observed directly. |

The **de-duplicated count is 114 distinct new PostgreSQL cases**, verified by the 113-case run plus the added schema case. Counts from overlapping runs are not additive. PostgreSQL 18.x catalog assertions ran against real disposable databases; the available server was identified as PostgreSQL 18.6. Normal-role SQL attacks did not disable owning guards.

The existing skip is `test_b05_manuscript_review.py::test_superseded_manuscript_review`: “B04 only creates DRAFT/FROZEN; exact SUPERSEDED history awaits the later supersession contract.” Warnings are existing Alembic path-separator deprecations and existing SQLAlchemy connection/isolation warnings from dependency writers.

Concurrency evidence includes separate backend/blocker witnesses for FIRST-SQL preparation, exact row order, zero-review INSERT phantoms, real authority/validity changes in both commit orders, B04/B05/B11/B13 writers, lock-free reads during writes, clock-based credential expiry (including actor-FK waits), a real legacy deadlock with bounded fresh-UoW recovery, injected SQLSTATE retry limits, atomic rollback and lost commit acknowledgment/restart replay.

Read-only schema and Application reviews found no remaining P0/P1 after remediation. Earlier development runs exposed SQL alias/timezone issues, incomplete test scaffolding and stale head expectations; these were corrected, and the final outputs above are the completion evidence. No passing claim is made for those earlier failing runs.

`git diff --check` reported no whitespace errors during focused implementation verification. At that stage no whole-suite run, commit, push or branch creation was performed. The reviewer subsequently authorized the full check; its results are recorded below. No later lifecycle/package/external slice was implemented.


## Reviewer remediation

### Wrong-parent regression

The requested command reproduced the failure on this tree:

```sh
uv run pytest "tests/integration/phase2/test_pr2_17_authorship_schema.py" -k "wrong_parent" -x
```

The failure was `complete initial history required` from `b14a_verify_entry`, during fixture setup: the second Publication was inserted without its initial lifecycle event. This is a B14a compatibility regression in the old test fixture, not a flaky or pre-existing failure. No parent-commit comparison is claimed. The fixture now creates the second Publication through the existing Application command. The original normal-role wrong-parent `P17A2` expectation and rollback assertions remain unchanged. No migration, FK, tuple CHECK, or same-parent guard was weakened.

| Run | Exact observed outcome | Output |
| --- | --- | --- |
| Before fixture correction | 1 failed, 37 deselected, 1 warning in 0.70s; exit 1. | [Reproduction](b14a-entry-evidence/review-wrong-parent-before.txt) |
| After fixture correction, same command | 1 passed, 37 deselected, 1 warning in 0.62s; exit 0. | [Corrected test](b14a-entry-evidence/review-wrong-parent-after.txt) |
| `uv run pytest tests/integration/phase2/test_b14a_entry_schema.py --tb=short` | 18 passed, 63 warnings in 12.64s; exit 0. | [Downgrade/catalog checks](b14a-entry-evidence/review-downgrade.txt) |

These review runs used the repository-local `.venv`, with `UV_CACHE_DIR=/tmp/researchbase-b14a-review-uv-cache`, an explicit disposable localhost PostgreSQL admin URL in `RB_TEST_ADMIN_URL`, and the task-specific `DATABASE_URL` database prefix `researchbase_lane19_b14a_review`. The shell commands above retain the reviewer's exact arguments. The default uv cache was not writable in the sandbox, so the cache location was configured before running them.

### Exact approval text and distinct coverage

The proposal's status value is exactly:

```text
APPROVED by owner 2026-10-18 — first slice authorized for implementation
```

The full literal Markdown line in the [proposal](../proposals/B14a_Publication_Internal_Review_Entry_Contract_DRAFT.md) is:

```text
**Status: APPROVED by owner 2026-10-18 — first slice authorized for implementation**
```

A direct assertion against that line passed. `uv run pytest --collect-only -o addopts='' -q tests/integration/phase2/test_b14a_publication_entry.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_b14a_entry_replay.py tests/integration/phase2/test_b14a_entry_concurrency.py` collected **114 unique node IDs**, with no duplicates. The [retained collection](b14a-entry-evidence/distinct-postgresql-cases.txt) gives this de-duplicated breakdown:

| Source file | Distinct PostgreSQL cases |
| --- | ---: |
| [Publication entry](../../tests/integration/phase2/test_b14a_publication_entry.py) | 41 |
| [Schema and migration](../../tests/integration/phase2/test_b14a_entry_schema.py) | 18 |
| [Historical replay](../../tests/integration/phase2/test_b14a_entry_replay.py) | 15 |
| [Concurrency](../../tests/integration/phase2/test_b14a_entry_concurrency.py) | 40 |
| **Total** | **114** |

The migration inventory changes remain appended entries/head values in [migration history](../../tests/unit/test_task12_migration_history.py), [linear history](../../tests/unit/test_batch_c_migration_history.py), [import boundaries](../../tests/architecture/test_import_boundaries.py), and the existing head expectation sites. The [B14a boundary tests](../../tests/architecture/test_b14a_entry_boundaries.py) and [closed DTO tests](../../tests/unit/phase2/test_b14a_entry_contract.py) are separate from the 114 PostgreSQL cases.

### Downgrade proof

`test_fresh_upgrade_catalog_and_empty_downgrade[base]` and `[0059_b13_grant_consumption]` in the schema suite now capture the complete logical public-schema inventory at 0059, upgrade to 0060, cleanly downgrade with empty entry history, and re-upgrade. They assert exact predecessor inventory equality after downgrade and exact extension inventory equality after re-upgrade, including live columns/types/defaults/nullability, constraint definitions/flags, indexes, triggers, and public function signatures/definitions. Physical OIDs and dropped-column slots are excluded.

`test_populated_creation_and_b04_seal_survive_forward_roundtrip` upgrades a populated creation/frozen-manuscript history, performs a real Application entry, then proves downgrade refusal with `P14I1`. The revision remains 0060, and both data and the complete catalog inventory remain unchanged. The empty-history downgrade path uses separate disposable databases: immutable entry history is never deleted to force a downgrade.

Read-only review of the remediation found no remaining P0/P1 or unmet P2 finding in these changes.

### Full-check execution

The reviewer-authorized command is:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

It uses the review environment described above and the repository-local `.venv`. An initial static-check attempt found an import-order error in the corrected fixture; that was fixed. The next complete invocation passed Pyright (0 errors), formatting (646 files), and Ruff, then reported **9,745 passed, 50 skipped, 4 failed, 4 errors**, exit 1. The [raw full-check output](b14a-entry-evidence/review-full-check-resource-failure.txt) retains the exact shard counts. Seven [retained failing-case reports](b14a-entry-evidence/review-resource-failures.json) explicitly show PostgreSQL `out of shared memory` with its `max_locks_per_transaction` hint; the eighth setup error is listed in the raw output, but its detailed traceback was not retained. These are not passing evidence or a claim of pre-existing/flaky behavior. The connected server reports `max_locks_per_transaction=64` and `max_connections=100`.

The runner additionally reported `PermissionError` when updating the shared duration cache outside this repository. Its final exit status was 1 from the failing shards. The runner and shared cache were not modified. A task-local PostgreSQL 18 initialization attempt failed at bootstrap because the host could not allocate its required shared-memory segment. No product guard or assertion was relaxed.

After all workers exited, a clean retry of the exact command again passed Pyright (0 errors), formatting (646 files), and Ruff, then exited **1: 9,746 passed, 50 skipped, 3 failed, 4 errors**, with 6,852 warnings. The longest shard took 2,119.51s. See the [exact retry output](b14a-entry-evidence/review-full-check-retry.txt), [shard diagnostics](b14a-entry-evidence/review-retry-shard-diagnostics.json), and [seven failing-case reports](b14a-entry-evidence/review-retry-failing-cases.json). Five failing cases explicitly reported PostgreSQL shared-memory exhaustion. The other two were an observed B13 blocker timestamp after its two-second expiry deadline and an execution ownership-race loser returning `CONCURRENT_MODIFICATION` where the test expected a result or `INVALID_STATE_TRANSITION`. No claim that these are pre-existing or flaky is made, and neither test was modified.

With the five shorter workers finished, this exact focused command passed on the current tree:

```sh
uv run pytest 'tests/integration/phase2/test_b13_grant_concurrency.py::test_real_wait_crosses_grant_expiry_with_zero_partial_history[scope]' 'tests/integration/phase2/test_pr2_04_ownership_races.py::test_pg_competing_execute_keys_get_only_one_reservation_owner[A-first-4]' -x --tb=short
```

Its [retained output](b14a-entry-evidence/review-retry-two-assertions.txt) is **2 passed, 4 warnings in 4.32s**, exit 0. This does not replace the failing full-check evidence. The originally reported authorship `wrong_parent` case passed in both complete invocations. All B14a cases passed in the retry. The full-check gate remains **NOT PASSED**. Further six-shard verification needs a PostgreSQL 18 test profile with sufficient shared lock-table capacity; a request for an available higher-capacity test URL is pending. Host server configuration and the external runner were not changed. The retry also retained the shared duration-cache permission error.
