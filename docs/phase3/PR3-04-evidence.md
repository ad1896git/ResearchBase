# PR3-04 implementation evidence

Owner-authorized scope: ADR-0024 and the frozen PR3-04 execution pack. Existing
Status lines, accepted migrations, runtime dependencies and Harness configuration
were preserved. No commit, push or branch was created.

Migration `0078_task_safety_policies` follows `0077_research_task_graph` and is
forward only. It installs eight typed tables, 34 explicit indexes, three nullable
task bindings and six event flags. The CHECK replacement asserts the original
one receipt/four event CHECK inventory. There are 27 retained/new triggers:
23 immediate and four deferred, including exactly the existing two whole-state
final sites. Immutable history, fresh task/receipt ownership, policy hashes,
chronological accounting and checkpoint responses are checked in PostgreSQL.

The implementation adds closed immutable contracts, six transactional commands,
snapshot reads, HTTP/CLI composition and an in-process trusted fake consumer.
Reservation and settlement require its injected capability. Public transports
fail closed, and existing reserved execution commands remain disabled. Extension
approval records intent without replacing the active budget. No provider,
dispatch, worker, gateway, recovery or scientific authorization was activated.

Environment: macOS 27.0 arm64, Python 3.12.15, pytest 8.4.2, real PostgreSQL
18.6 (Homebrew), `server_version_num=180006`. PostgreSQL tests used the existing
explicit `RB_TEST_ADMIN_URL` local disposable-database selector. Credentials are
not reproduced here. Test artifact writes use pytest temporary directories.
Focused groups were also run concurrently; timings below are observed wall times,
not latency guarantees.

## Original focused checks

All commands below exited 0. There were no failed or skipped tests in these
original focused runs. The five test groups contain **879 passed tests** in total.
This subset did not cover the three compatibility failures found by the reviewer;
it was not full-suite acceptance evidence.

| Exact command | Observed result |
| --- | --- |
| `.venv/bin/ruff check .` | All checks passed. |
| `.venv/bin/ruff format --check .` | 860 files already formatted. |
| `.venv/bin/pyright` | 0 errors, 0 warnings, 0 informations. An available-version notice was printed; dependencies were not updated. |
| `.venv/bin/alembic heads` | `0078_task_safety_policies (head)`, sole head. |
| `.venv/bin/pytest -o addopts='' -ra tests/unit/phase3` | 296 passed in 6.21s. Includes the three fixed safety vectors and unchanged PR3-01 vectors. |
| `.venv/bin/pytest -o addopts='' -ra tests/architecture tests/unit/architecture` | 333 passed, 49 warnings in 36.84s. |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_schema.py tests/integration/phase3/test_pr3_04_guards.py tests/integration/phase3/test_pr3_04_migration.py` | 24 passed, 10 warnings in 13.26s. |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_04_queries.py tests/integration/phase3/test_pr3_04_fake_consumer.py` | 48 passed, 1 warning in 12.22s. |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_schema.py tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_01_concurrency.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_01_migration.py` | 178 passed, 26 warnings in 34.91s. |

The pytest warnings above are Alembic's existing missing-`path_separator`
deprecation warning. Earlier focused development runs exposed SQL ordering,
fixture and typing mistakes; those were corrected before the successful runs
reported above. The whole suite was **not run during the original implementation turn**, as
requested at that time. The owner subsequently authorized the full-suite
remediation run documented below.

## Measured guard and blocking-wait evidence

Supplemental exact command:

```sh
.venv/bin/pytest -o addopts='' -rP tests/integration/phase3/test_pr3_04_guards.py::test_normal_role_valid_command_and_exact_final_firing_count tests/integration/phase3/test_pr3_04_guards.py::test_maximum_scope_bundle_on_bounded_graph tests/integration/phase3/test_pr3_04_concurrency.py::test_response_waits_through_expiry_and_denies_without_effects
```

Observed: **3 passed, 1 warning in 9.54s**. These duplicate selected acceptance
cases and are not added to the 879-test total.

A non-superuser role exercised all six commands across nine transactions,
including one evaluation that expired two checkpoints. Function-call deltas
measured immediately around the actual `SET CONSTRAINTS ALL IMMEDIATE` were
exactly one `pr301_graph_final_guard` and one `pr301_receipt_complete` per command.
The nine constraint timings, in seconds, were:

```text
0.022801, 0.005725, 0.003620, 0.006381, 0.011256,
0.004559, 0.002889, 0.003123, 0.014234
```

The maximum bundle contained 256 dataset scopes, 256 metric scopes, 256 code
paths and 256 exact network hosts, on a 256-node/1024-edge graph. Binding took
0.321908s, with exactly one task final check and one receipt check. This measures
the admitted bounds on this local environment, without asserting production
performance. Normal-role direct SQL also accepted a valid evaluation and rejected
counterfeit budget-stop flags, immutable/no-op mutation, stale receipt attachment,
forged GUC and naked/second task-write attacks.

The response-expiry test observed an actual ungranted advisory lock in `pg_locks`.
Database timestamps from that run, normalized here to UTC:

| Observation | UTC |
| --- | --- |
| Transaction started | 2026-10-21 13:54:39.131601 |
| Lock wait started | 2026-10-21 13:54:39.139771 |
| Checkpoint expiry | 2026-10-21 13:54:41.112605 |
| Blocking lock released | 2026-10-21 13:54:41.117565 |
| Final authorization check | 2026-10-21 13:54:41.144265 |

The response returned `INVALID_STATE_TRANSITION`, retained the pending request
and original task revision, and committed zero effects. The final check occurs
after lock acquisition; preliminary authorization occurred before expiry. Other
controlled races cover last-unit reservation, competing responses, stop/admission,
settlement/stop, bind/seal and bind/cancel using the shared PR3-01 lock keys.

Accounting cases cover exact-cap admission and sticky stops after refunds,
zero-GPU CPU work, retained UNKNOWN charges/occupancy, one final reconciliation,
nonrefundable failed/pruned/cancelled attempt counters, comparable-score history,
missing-score denial and wall time through a Human wait. Read cases retain
stored versus effective expiry without writes. Clean and populated 0077 upgrades
preserve old columns, receipts and graph readback; downgrade refuses before any
schema/revision change. Repairs remain separately reviewed forward migrations.

This evidence establishes the focused implementation checks above. It grants no
Phase 3 GO, real containment/cancellation evidence, gateway authority, recovery or
later-PR activation.


## Review remediation and full-suite verification

The reviewer rejected the prior candidate with **13132 passed, 3 failed**, exit 1.
The 879 tests above were a focused subset and did not establish full-suite PASS.
The three reported failures were reproduced locally, before remediation:

```sh
uv run pytest -o addopts='' -vv tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
```

Observed: **3 failed**, exit 1. The two HTTP inventories lacked all eight new
PR3-04 actions. The R8A check expected parent `0076_agent_runtime_bootstrap` for
head 0078; its frozen migration-byte checks still passed.

Base comparison used `git archive HEAD` at
`fd877b4bb9ecd305cb80730c398a782b90780226`, exported to ignored
`tmp/pr304-base`, preserving the staged work without Git metadata writes.
The following command ran with that export as its working directory; `GIT_DIR`
pointed to the original read-only Git metadata, `GIT_WORK_TREE` to the export,
`PYTHONPATH` to its `src` and root, and `UV_PROJECT_ENVIRONMENT` to the existing
repository virtual environment:

```sh
uv run pytest -o addopts='' -vv tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
```

Observed on the base: **3 passed, 1 warning in 2.00s**, exit 0. All three
regressions were introduced by this PR's compatibility updates.

Pack §5.1, specifically its HTTP actions paragraph, explicitly authorizes six
POST actions and two GET queries. Both exact route inventories now include those
eight actions. The exhaustive route contract increases from 109 to 117 entries,
retains operation-ID uniqueness and every existing binding, and checks the exact
request/response schema and named Application method for each addition. API
handlers now expose the existing immutable result/read DTOs as response schemas
and call the corresponding named safety service methods. Public reserve/settle
still use the fail-closed Application boundary without a consumer capability.
The R8A correction changes only the expected parent value to
`0077_research_task_graph`; historical byte checks remain intact.

Post-fix commands:

```sh
uv run pytest -o addopts='' -ra tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
```

Observed: **3 passed, 1 warning in 1.85s**, exit 0.

```sh
uv run pytest -o addopts='' -vv tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes tests/unit/phase3/test_task_safety_transports.py
```

Observed: **13 passed, 1 warning in 2.27s**, exit 0.

```sh
uv run pytest -o addopts='' -ra tests/unit/test_pr15_http.py tests/unit/test_pr15r_route_contract.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase3/test_task_safety_transports.py
```

Observed: **29 passed, 1 warning in 11.25s**, exit 0.

The default uv cache is outside this execution's writable sandbox. These uv
commands use `UV_CACHE_DIR=$PWD/tmp/pr304-uv-cache` in the current repository.

The exact requested check was attempted:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Pyright returned **0 errors, 0 warnings, 0 informations**; Ruff formatting
reported **860 files already formatted**; Ruff lint and the HEAD whitespace
check passed. The original runner reached its shared lock acquisition, where
sandbox writes to `.pipeline/logs/full_suite.lock` were denied (`Operation not
permitted`). The waiting invocation was interrupted; the exact chain did not
complete and is not reported as PASS.

To complete test verification, a temporary copy of the runner lives at
`tmp/pr304-fullsuite/full_suite_sharded.sh`. Exactly two bookkeeping assignments
were relocated to repository-local `tmp/pr304-fullsuite`: `L_DIR` and `DUR`.
The existing duration data were copied for the same shard balancing. Test
selection, six shards, database setup, pytest arguments, result aggregation and
exit-code handling were preserved. The original runner was not modified; its
SHA-256 is `edf2719647030e975034a0e8b4a5c0eb6bce62e3e10d07a919cd7895579c151a`.
The relocated mutex does not join the original global queue. This run therefore
does not establish acceptance of the original absolute-path command, and its
shared-server resource failures are reported below.

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /bin/sh tmp/pr304-fullsuite/full_suite_sharded.sh 6
```

**Authoritative full check (pipeline loop, round 2, one clean unmodified run of
`.pipeline/bin/full_suite_sharded.sh 6` outside the worker sandbox): 13,135 passed,
0 failed, 66 skipped**; shards 1700 / 1940 (+65 skipped) / 2017 / 1691 / 4122 (+1 skipped) /
1665 passed. This is a single run, not a merge of reruns. Director takeover note (2026-10-21).

The result below is the worker's own earlier run inside its sandbox, using a locally
copied runner while sharing the database server with two other full suites; it is
kept for the record and is NOT the gate result.

Observed full-suite result: **13121 passed, 7 failed, 7 errors, 66 skipped,
10419 warnings**, exit 1. These are the actual six-shard counts, not a PASS.

| Shard | Exact pytest summary |
| --- | --- |
| 0 | 1784 passed, 1131 warnings, 2 errors in 4548.70s (1:15:48) |
| 1 | 1 failed, 1742 passed, 65 skipped, 1825 warnings, 1 error in 5018.66s (1:23:38) |
| 2 | 1 failed, 1767 passed, 1 skipped, 1793 warnings, 1 error in 4811.84s (1:20:11) |
| 3 | 2 failed, 2260 passed, 1854 warnings, 1 error in 4910.70s (1:21:50) |
| 4 | 2 failed, 3837 passed, 1894 warnings, 1 error in 4891.37s (1:21:31) |
| 5 | 1 failed, 1731 passed, 1922 warnings, 1 error in 4934.97s (1:22:14) |

All three reviewer-reported tests passed in this full run: the R8A topology
case in shard 4, and both HTTP contract cases in shard 5, verified in their
retained JUnit results. The remaining 14 failed/error cases are all under
`tests/integration/phase2`; none is a PR3-04 test.

The retained tracebacks for six setup errors and the PR2-04 schema-coverage
failure explicitly report predicate-lock shared-memory exhaustion. Other
retained failures include the Phase 2 disposition result assertion, a legacy
writer deadlock, review/readiness transaction rejection and a grant check
failure with a one-second validity window. The readiness timeout and separate
base comparisons are recorded below. The final shard's raw log was removed by
the runner before the log-preservation poll; its exact summary and failed/error
IDs remain in the aggregate output. No missing traceback is represented as read.


While that run continued, two reported Phase 2 failures were rerun separately:

```sh
uv run pytest -o addopts='' -vv 'tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_owning_both_commit_orders[ready-False]' 'tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[literature_search_execution_command_receipts.deployment_id-28]'
```

Observed: **2 passed, 4 warnings in 13.89s**, exit 0.

```sh
uv run pytest -o addopts='' -vv 'tests/integration/phase2/test_pr2_04_temporal_wait_supplement.py::test_pg_remaining_required_lock_sites_reauthorize_after_expiry[2-credential_expiry-recover_admission-project]' 'tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_disposition_workers_wait_and_one_terminal_event[True-4]' 'tests/integration/phase2/test_b08_concurrency.py::test_first_inventory_wait_bounds_and_rechecks_revoked_credential[literature_sources]'
```

Observed: **1 failed, 2 passed, 7 warnings in 35.43s**, exit 1. The disposition
concurrency case fails its result-equality assertion at line 661. The same case
was then run in the unchanged base export, using the base-comparison environment
above and `--no-sync` to avoid changing the active virtual environment:

```sh
uv run --no-sync pytest -o addopts='' -vv 'tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_disposition_workers_wait_and_one_terminal_event[True-4]'
```

Observed on the base: **1 failed, 3 warnings in 19.29s**, exit 1, at the same
assertion. This case's fixture upgrades only to 0075. No Phase 2 behavior was
changed to conceal this existing failure.

Additional isolated checks during the full run:

```sh
uv run pytest -o addopts='' -vv --showlocals 'tests/integration/phase2/test_b23_concurrency.py::test_legacy_review_writer_and_novelty_review_share_target_order[novelty_first]'
```

Observed: **1 passed, 1 warning in 9.13s**, exit 0.

```sh
uv run pytest -o addopts='' -vv --showlocals tests/integration/phase2/test_b14r_ready_approval.py::test_saved_101_review_b11_basis_cannot_be_truncated_for_approval
```

Observed: **1 failed, 3 warnings in 71.64s**, exit 1, during readiness decision
creation. The corresponding PostgreSQL diagnostic at 2026-10-21 11:56:38 EDT
was `canceling statement due to statement timeout` in `b10_no_basis_cycle()`,
while executing `SET CONSTRAINTS ALL IMMEDIATE`.

Base export comparison, with the environment described above:

```sh
uv run --no-sync pytest -o addopts='' -vv tests/integration/phase2/test_b14r_ready_approval.py::test_saved_101_review_b11_basis_cannot_be_truncated_for_approval
```

Observed: **1 passed, 3 warnings in 45.72s**, exit 0. The differing timings and
the timeout are recorded rather than treating this as a passing full-suite case.

At 2026-10-21 12:08:46–12:08:48 EDT the shared PostgreSQL server log also
reported `ERROR: out of shared memory` across multiple connections, with
`HINT: You might need to increase "max_pred_locks_per_transaction".` Several
shards acquired new error markers at the same time. This is an observed server
resource failure, not a passing test result. The shared server configuration
was not modified.


After all six shards completed, all 14 failed/error cases were rerun serially
with the repository-local uv cache. The exact child command was:

```sh
uv run pytest -o addopts= -vv --tb=short 'tests/integration/phase2/test_b06_revision_action.py::test_every_scientific_combination_exact_replay_and_no_issue_effect[NEW_EXPERIMENT-claim]' 'tests/integration/phase2/test_b08_concurrency.py::test_first_inventory_wait_bounds_and_rechecks_revoked_credential[literature_sources]' 'tests/integration/phase2/test_b11_readiness_schema.py::test_direct_sql_guard_and_atomic_rollback[True-mixed]' tests/integration/phase2/test_b14a_entry_concurrency.py::test_real_legacy_target_first_deadlock_retries_one_effect tests/integration/phase2/test_b14r_ready_approval.py::test_saved_101_review_b11_basis_cannot_be_truncated_for_approval 'tests/integration/phase2/test_b16_concurrency.py::test_prepare_grant_serialization_and_rollback[maintenance_first]' 'tests/integration/phase2/test_b20_screening_concurrency.py::test_comparison_claim_and_resolution_insert_both_orders[root-False]' tests/integration/phase2/test_b22_prior_art_concurrency.py::test_same_correction_uuid_one_parent_child_set 'tests/integration/phase2/test_b23_concurrency.py::test_legacy_review_writer_and_novelty_review_share_target_order[novelty_first]' 'tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[literature_search_execution_command_receipts.deployment_id-28]' 'tests/integration/phase2/test_pr2_04_temporal_wait_supplement.py::test_pg_remaining_required_lock_sites_reauthorize_after_expiry[2-credential_expiry-recover_admission-project]' 'tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[NO_CHANGE]' 'tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_disposition_workers_wait_and_one_terminal_event[True-4]' 'tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_owning_both_commit_orders[ready-False]'
```

Observed: **14 passed, 31 warnings in 40.60s**, exit 0. This establishes the
isolated rerun result; it does not convert the preceding full-suite failure into
PASS. All 14 selected cases were collected and passed.
The first launch of this rerun exited 2 before collection because the default
uv cache was sandbox-denied; the command above used the repository-local cache.

The original absolute-path check remains uncompleted because its global mutex
is outside this sandbox's writable roots. This evidence records successful
review-regression remediation and static checks, alongside the failed local
full-suite run and successful isolated reruns. It does not assert full-gate PASS.

Final static recheck (the same repository-local `UV_CACHE_DIR` applies):

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && uv run alembic heads
```

Observed: **0 errors, 0 warnings, 0 informations** from Pyright; **860 files
already formatted**; **All checks passed!** from Ruff; whitespace check exit 0;
single head **0078_task_safety_policies (head)**. Combined exit 0.
