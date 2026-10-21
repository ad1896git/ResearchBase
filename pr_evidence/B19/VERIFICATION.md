# B19 first-slice implementation evidence

Authority: owner approval and implementation authorization dated 2026-10-18,
B19's approved first slice, and ACCEPTED ADR-0017 (B19-AQ-01/B21-AQ-01).
Status: both reviewer-reported failures are fixed and independently pass. The
requested exact check is BLOCKED before shard execution by sandbox permissions
on the pipeline lock directory. A separate six-shard full-suite run passed:
10,721 passed, 53 skipped, 0 failures, 0 errors. Historical focused results below
do not establish an overall check PASS; the exact requested command remains BLOCKED.

## Reviewer remediation — 2026-10-19

The reviewer reported a check exit of 1: B07's empty forward round trip and B15's
clean catalog round trip failed. Both failures were reproduced independently;
each expected table set omitted `novelty_assessment_prior_art_inputs`. Only that
entry was appended to each existing test expectation. The 0066 migration did not
need a change. A new B19 test compares a pristine 0065 catalog with the catalog
after 0066 upgrade/downgrade: relations, columns/defaults, constraints, functions,
triggers and indexes must match exactly, with the original
`ck_pr218_novelty_initial_slice` explicitly present.

Post-fix reproduction: B07 1 passed (5 warnings), B15 1 passed (4 warnings), and
the new exact-catalog round trip 1 passed (4 warnings). All three also passed
inside the full local sharded run, as retained in `review-target-junit.json`.

Remediation commands use the same PYTHONPATH and UV_CACHE_DIR as below, with:

```sh
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export UV_NO_SYNC=1
export DATABASE_URL=postgresql+psycopg://fengwang@localhost/researchbase_b19_review_lane38
export RB_TEST_ADMIN_URL=postgresql+psycopg://fengwang@localhost/postgres
```

`UV_NO_SYNC=1` uses the installed locked environment: an initial sync attempt
was denied permission to rewrite the shared environment's researchbase executable
and ran no tests. The full script receives a dedicated test-database prefix.

| Exact remediation command | Observed result |
| --- | --- |
| `uv run pytest tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade -x` | Before: exit 1, 1 failed, 3 warnings in 0.73s. After: exit 0, 1 passed, 5 warnings in 0.86s. |
| `uv run pytest tests/integration/phase2/test_b15_package_schema.py::test_clean_upgrade_catalog_and_empty_downgrade -x` | Before: exit 1, 1 failed, 2 warnings in 0.75s. After: exit 0, 1 passed, 4 warnings in 0.84s. |
| `uv run pytest tests/integration/phase2/test_b19_close_prior_art_schema.py::test_empty_downgrade_restores_exact_parent_catalog -x` | Exit 0, 1 passed, 4 warnings in 0.71s. |
| `uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6` | Static stages passed: Pyright 0 errors/warnings/informations; 718 files formatted; Ruff and HEAD diff-check clean. Script pre-check: 573 passed, 912 warnings in 357.49s. Then blocked: creating its external `.pipeline/logs/full_suite.lock` returns `Operation not permitted`; stopped with exit 130 before any full shard started. An earlier attempt stopped with exit 2 for a trailing blank line in the retained pyright log; that whitespace is fixed. |
| `uv run python /private/tmp/b19_review_local_shards.py` | Exit 0; all six shards passed: 10,721 passed, 53 skipped, 8,512 warnings, 0 failures/errors; 1,794.71s elapsed. Runner source retained as `review-local-shards-runner.txt`. |
| `uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD` | Final rerun exit 0: 0 Pyright errors/warnings/informations, 718 files already formatted, Ruff passed, no HEAD whitespace errors. |

The pipeline script was not modified. Its lock and duration paths are outside
this session's writable roots; permission escalation is unavailable. The local
runner reads the same measured durations and uses the same file selection,
greedy six-way balance, Alembic head setup and pytest options. It writes logs and
JUnit XML under `/private/tmp/b19-review-local-shards`, uses separate disposable
databases, and does not write the pipeline lock or duration file. This separately
verifies the full tests; it is not evidence that the requested exact command passed.

| Local shard | Passed | Skipped | Warnings | Pytest seconds | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 630 | 0 | 630 | 1790.47 | 0 |
| 1 | 1784 | 0 | 1033 | 1435.12 | 0 |
| 2 | 1559 | 0 | 1419 | 1441.46 | 0 |
| 3 | 1436 | 1 | 1477 | 1410.36 | 0 |
| 4 | 3809 | 0 | 1469 | 1465.04 | 0 |
| 5 | 1503 | 52 | 2484 | 1379.77 | 0 |

The 53 skips are 48 opt-in large benchmarks, 2 opt-in novelty sampling profiles,
1 opt-in B29 measurement, 1 live M2 check requiring HG1_RUN_LIVE, and 1 later
manuscript supersession contract case. They are not reported as passed.

Retained remediation evidence: `review-b07-before.txt`, `review-b07-after.txt`,
`review-b15-before.txt`, `review-b15-after.txt`, `review-catalog.txt`,
`review-full-command.txt`, `review-shard-0.txt` through `review-shard-5.txt`,
`review-local-shards.txt`, `review-local-shards-results.json`,
`review-local-shards-runner.txt`, and `review-target-junit.json`.

## Implemented scope

- One forward migration, `0066_b19_close_prior_art_basis`, after actual head
  `0065_b22_prior_art_correction`. No accepted migration bytes changed.
- One immutable typed assessment/basis relation, ordered TEXT[] criteria, scope,
  and strict material-version admission. Deferred normal-role guards enforce
  structural closure, independent verification, terminal B22 selection, and seals.
- Positive CLOSE_PRIOR_ART_FOUND uses v2; INCONCLUSIVE retains literal v1 material.
  Negative novelty remains unavailable. Exact saved basis membership is retained.
- Existing command/read, UoW/repository, HTTP and CLI surfaces extended additively.
  Writes retain FIRST-statement N SHARE locks and READ COMMITTED; exact reads
  retain one read-only REPEATABLE READ snapshot and no explicit locks or writes.
- Historical replay checks saved hashes and current reader entitlement; later
  source changes, disputes, B22 succession and ambiguity alter current usability.
- Populated downgrade refuses v2/basis history; v1-only round trips preserve hashes.
  Migration preflight rejects unexpected shared guards and broken v1 closure.

## Reconciliation and substitutions

- The proposal's inspected 0064 baseline was reconciled to actual B22 head 0065.
- HashRef already supported PriorArtRelation through B22; only the missing
  SearchResultResolution literal was added.
- SearchResultResolution has no project_id column. Its project is derived through
  the existing exact result → query → execution joins, without duplicating ownership.
- Plain resolution reads reuse existing metadata_observation._hash. Joined project
  and execution projection fields are excluded before calling that unchanged verifier.
- Existing guide paths and fixture builders were used; no semantic substitution
  or architecture deviation was required. Head assertions/inventories only received
  updated values or appended migration entries.

## Environment and exact commands

PostgreSQL: 18.6 (Homebrew). Tests create disposable databases and temporary
non-superuser roles; normal-role structural guards run without superuser bypass.

All uv commands below ran after:

```sh
export PYTHONPATH="$PWD/src:$PWD"
export VIRTUAL_ENV=/Users/fengwang/Documents/ResearchBaseProject/.venv
export UV_CACHE_DIR=/private/tmp/rb-b19-uv-cache
export DATABASE_URL=postgresql+psycopg://fengwang@localhost/postgres
export RB_TEST_ADMIN_URL=postgresql+psycopg://fengwang@localhost/postgres
```

| Exact command | Observed result |
| --- | --- |
| `uv run --active --offline --no-sync ruff check .` | Exit 0; all checks passed. |
| `uv run --active --offline --no-sync ruff format --check .` | Exit 0; 718 files already formatted. |
| `uv run --active --offline --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `uv run --active --offline --no-sync pytest tests/unit tests/architecture tests/test_architecture.py` | Exit 0; 5534 passed, 49 warnings in 112.66s. |
| `uv run --active --offline --no-sync pytest tests/integration/phase2/test_b19_*.py` | Exit 0; 74 passed, 80 warnings in 117.74s. |
| `uv run --active --offline --no-sync pytest tests/integration/phase2/test_pr2_19_novelty.py::test_g7_novelty_restart_denials_and_later_resolution` | Exit 0; 1 passed, 1 warning in 1.16s after correcting the old test premise. |
| `uv run --active --offline --no-sync pytest tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_b01_resolution_*.py tests/integration/phase2/test_b22_prior_art_*.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py` | Exit 0; 212 passed, 224 warnings in 597.12s. |
| `uv run --active --offline --no-sync pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py` | Exit 0; 238 passed, 626 warnings in 331.49s. |
| `git diff --check` | Exit 0; no whitespace errors. |

Pytest warnings include existing Alembic path_separator deprecation, fixture
assert-rewrite notice, and the established internal review connection-option
SAWarning. Pyright also prints an available-version notice, separate
from its zero diagnostic counts. Incomplete interrupted runs are not PASS evidence.
Early authoring runs found transport error mapping and test-fixture role-event/UUID
issues. The adjacent novelty run also found an old CLOSE-denial test premise;
its incomplete CLOSE command now correctly raises VALIDATION_ERROR at construction,
and the negative outcome still raises INVALID_STATE_TRANSITION. These were
corrected before the retained successful runs.

## Retained evidence and review

- `unit-architecture.txt`, `b19-postgresql.txt`, `novelty-regressions.txt`,
  `migration-head-regressions.txt`, `pyright.txt`: completed command output.
- `novelty-v2-vector.json`: independent literal payload; all IDs are UUID integers 1..7.
  Relation IDs 5/6 share witness 7; predecessor 3 can be a saved v1 record.
  NFC canonical JSON bytes, excluding the file's trailing newline, hash to
  `6e9be985368217d4e9283a45a9d1574d73d7bc0ea7cf9a81d2fc9e3d71a55254`.
- The unchanged v1 literal oracle remains in test_pr2_18_hash_vectors.py.
- Read-only sub-agent reviews used the approved specification, ADR and diff.
  Reported transport defects and required-case gaps were addressed; final source
  review reported no concrete remaining P0/P1 issue. Sub-agents made no edits.
- B19 cases include observed two-backend waits in both B19/B22 Claim-lock orders,
  source/evidence validity and resolution-range commit orders, snapshot reads,
  expiry, retry normalization, uncertainty recovery, SQL closure/seals and rollback.

The original implementation ran only focused selections. The owner's reviewer
remediation request explicitly authorizes the full sharded check. No commit,
push or branch creation was performed.
