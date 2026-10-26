# PR3-02-S2 intent review B3 evidence — lane351

Review: `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_intent_review_B3.md`, read in full.
Target: existing branch `s2-intent-fix3`, base/HEAD `33e2a65896b9646f0e373c7d96c8f42439282484` (`s2-freeze`), plus the uncommitted test/evidence diff. Local date: 2026-10-25; the captured UTC timestamps fall on 2026-10-26.

This file replaces the earlier evidence narrative. All previous B2/B/RR/PG run outputs and completion claims have been removed; none receives current credit. Every run below was executed in lane351 after the final test edits and formatting. Only this evidence document was assembled afterward. DIFF was repeated with the evidence included.

Only three test files and this evidence file change. L2/L3, the two CHECK-drift cases, and the 16 effective privilege cases already existed at the base; they were retained, collected and mutation-tested, not recreated or credited as new implementation. The named-layer assertions, READ COMMITTED isolation case, and three byte/replay cases are new; L2 now reports the missing post-wait observations explicitly. No runtime implementation, frozen pack, migration, dependency, branch, commit or push is changed.

## B3 closure checklist

The exact node IDs and removed/restored results below are the evidence for checking these items. Collection proves existence only; execution and mutation results provide the behavioral evidence. Items 2 and 7 are command/evidence obligations, so they have no production guard to mutate and receive no invented mutation PASS.

- [x] **1. Frozen L2/L3 names:** COLLECT found all four nodes below; UNIT-ARCH executed them. M-L2 removes the post-SHARE fresh check: 1 failure/exit 1, restored 1 pass/exit 0. M-L3 removes read-only mode from `begin_formal_read`: 3 failures/exit 1, restored 3 passes/exit 0.
- [x] **2. Complete frozen S7 regression commands:** S7-REG3, S7-REG2 and S7-PREVIEW execute the literal frozen regression commands; all exit 0. The other S7 commands are also rerun below, with the existing S2 filename mapping made explicit. Mutation result: not applicable to running commands; no substituted migration-only selection or seven-command completeness claim.
- [x] **3. Receipt CHECK drift refusal:** both `test_upgrade_refuses_receipt_check_drift` nodes alter one baseline CHECK at 0080 to `CHECK (true)`, require the exact refusal, and compare the unchanged drifted catalog/revision and absence of intent tables. M-DRIFT removes the comparison/refusal: 2 failures/exit 1, restored 2 passes/exit 0. The refusal is the migration's Python `RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")`, not a SQLSTATE or public ErrorCode.
- [x] **4. Every migration REVOKE:** the PUBLIC and explicit-role paths each have eight normal-role direct-write nodes, listed below. Default grants are installed before migration and proven effective on a probe table; SELECT is granted independently. Every operation must raise SQLSTATE 42501. M-REVOKE-PUBLIC and M-REVOKE-ROLE each remove only their own REVOKE in a copy: 8 failures/exit 1 each, restored 8 passes/exit 0 each.
- [x] **5. Named guards:** all 13 `test_named_insertion_and_receipt_guards` cases assert SQLSTATE, tag, exact diagnostic message, and the actual `PL/pgSQL function ... at RAISE` context. SHARE-held/no-command-advisory and non-READ-COMMITTED cases are explicit. M-SHARE, M-CAS and M-ISOLATION each produce 1 failure/exit 1 and restored 1 pass/exit 0. In M-CAS the surviving receipt root raises the same tag and message, but the function-name assertion fails.
- [x] **6. Replay before byte failure:** both saved-receipt cases return original results with `replayed=True` without calling the broken byte reader; a new command proves that reader fails. The interleaving case commits an exact receipt after the outer preflight snapshot and then returns mismatched bytes, proving saved replay wins over a captured preflight error. M-REPLAY-PREFLIGHT: 2 failures/exit 1, restored 2 passes/exit 0. M-REPLAY-WRITE: 1 failure/exit 1, restored 1 pass/exit 0. Effect counts remain unchanged on replay or contain only the single winning three-row create.
- [x] **7. Fresh supporting runs:** all commands below ran after the final test changes, including the full frozen regressions, historical H-U/PG-R, PG-N catalog probe, scope AUDIT and `-s` concurrency/replay evidence. Old run output is deleted. Mutation references are only the current removed/restored runs below; no older result is carried forward.

## Exact nodes for checklist items

| Item | Node ID | Normal evidence | Mutation removed → restored |
| --- | --- | --- | --- |
| 1 / L2 | `tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait` | UNIT-ARCH, exit 0 | M-L2, exit 1 → 0 |
| 1 / L3 | `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]` | UNIT-ARCH, exit 0 | M-L3, exit 1 → 0 |
| 1 / L3 | `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]` | UNIT-ARCH, exit 0 | M-L3, exit 1 → 0 |
| 1 / L3 | `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]` | UNIT-ARCH, exit 0 | M-L3, exit 1 → 0 |
| 3 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]` | INTENT, exit 0 | M-DRIFT, exit 1 → 0 |
| 3 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]` | INTENT, exit 0 | M-DRIFT, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-PUBLIC, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_instances]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 4 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_events]` | INTENT, exit 0 | M-REVOKE-ROLE, exit 1 → 0 |
| 5 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]` | INTENT, exit 0 | M-SHARE, exit 1 → 0 |
| 5 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]` | INTENT, exit 0 | M-CAS, exit 1 → 0 |
| 5 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]` | INTENT, exit 0 | M-ISOLATION, exit 1 → 0 |
| 6 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]` | INTENT, exit 0 | M-REPLAY-PREFLIGHT, exit 1 → 0 |
| 6 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]` | INTENT, exit 0 | M-REPLAY-PREFLIGHT, exit 1 → 0 |
| 6 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed` | INTENT, exit 0 | M-REPLAY-WRITE, exit 1 → 0 |

The SHARE-held/no-advisory node is `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[advisory-pr302s2_preheld]` (INTENT, exit 0). COLLECT-NODES lists every expanded parameter ID; it is not counted as executed coverage by itself.

## Frozen-ID to actual-node mapping

The frozen `test_pr3_02_s2_schema.py` nodes live in `test_pr3_02_s2_intent_guards.py`; all other S2 integration filenames retain their existing `_intent_` infix. No aliases, duplicate tests or frozen-pack edits were added. Schema/guards/migration therefore run as two actual files in S7-SCHEMA; execution and races/replay use the corresponding actual filenames. All three existing regression commands retain the exact frozen glob/file lists.

| Frozen ID | Actual nodes (integration/repository parameters in COLLECT-NODES) | Run (exit 0) |
| --- | --- | --- |
| U1 | `tests/unit/phase3/test_agent_execution_contracts.py::test_closed_intent_command_and_literal_vectors`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity` | UNIT-ARCH / INTENT |
| U2 | `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_binding_and_harness_pins` | UNIT-ARCH |
| U3 | `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_query_and_receipt_shapes` | UNIT-ARCH |
| L1 | `tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys` | UNIT-ARCH |
| L2 | `tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait` | UNIT-ARCH |
| L3 | `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot` | UNIT-ARCH |
| M1 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head`; `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift` | INTENT |
| M2 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history` | INTENT |
| M3 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change` | INTENT |
| G1 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_exact_intent_schema_and_scoped_foreign_keys`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral` | INTENT |
| G2 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history`; `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary`; `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history`; `tests/integration/phase3/test_pr3_02_s1_schema.py::test_unreceipted_or_late_writes_deny`; `tests/integration/phase3/test_pr3_02_s1_schema.py::test_db_receipt_time_overrides_input_and_incomplete_root_denied` | INTENT / S7-REG3 |
| G3 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity` | INTENT |
| E1 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary` | INTENT |
| E2 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate` | INTENT |
| E3 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects` | INTENT |
| R1 | `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait` | INTENT |
| R2 | `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_same_command_revision_and_existing_writer_races`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_task_writer_coexistence`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_gateway_writer_coexistence`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_phase2_writer_coexistence` | INTENT |
| R3 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit`; `tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry`; `tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability` | UNIT-ARCH / INTENT |
| R4 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure`; `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt` | INTENT |
| R5 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_queries_are_coherent_bounded_snapshots`; `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot` | UNIT-ARCH / INTENT |
| A1 | `tests/architecture/test_pr3_02_s2_boundaries.py::test_intent_only_application_boundary` | UNIT-ARCH |

This mapping identifies test allocation, not a claim that every theoretical branch is reachable. Under the option-A numeric refreeze, SQL numeric rejection is not required. The SQL NULL 22023 diagnostic is exercised by G3; the serializer's unsupported-type ELSE is unreachable for valid PostgreSQL jsonb, whose possible types are all handled. That branch is not credited as tested. Source-link revocation and all running/promotion/provider work remain deferred by the frozen pack. The existing PR3-05 preview denial is covered by S7-PREVIEW/PG-R, not promoted to producer verification.

L2/L3 execute the real service/UoW/repository with deterministic SQL/port doubles; their observations prove call ordering and forbidden I/O/session operations, not PostgreSQL isolation by themselves. INTENT and S7-RACES supply the real PG18.6 wait/snapshot observations. The `-s` output includes all four wait sites (first_share, second_key, task_row, version_row), expiry/acquisition/authorization times and persisted counts. No deadlock-freedom claim is made.

## Environment and fresh command results

Every command below inherited these exports, including mutation subprocesses. The mutation copies use the lane's existing interpreter/environment and override PYTHONPATH to the copied source. Fixtures create/drop only randomly named disposable databases on the selected local cluster; the ambient lane database is not substituted for a disposable migration fixture.

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export DATABASE_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane351"
export RB_TEST_ADMIN_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres"
export PGOPTIONS="-c jit=off"
```

Each command is recorded separately. Counts overlap across combined, frozen-stage and focused commands and must not be added as distinct tests. Existing Alembic path_separator warnings and the Pyright update notice are preserved in raw output.

| Run | Observed result | Exit code |
| --- | --- | --- |
| DIFF | Empty stdout/stderr | 0 |
| LINT | All checks passed! | 0 |
| FORMAT | 948 files already formatted | 0 |
| TYPE | 0 errors, 0 warnings, 0 informations | 0 |
| HEAD | 0081_agent_execution_intents (head) | 0 |
| UNIT-ARCH | 1423 passed, 50 warnings in 35.98s | 0 |
| INTENT | 91 passed, 151 warnings in 82.58s (0:01:22) | 0 |
| COLLECT | 4 tests collected in 0.26s | 0 |
| COLLECT-NODES | 101 tests collected in 0.05s | 0 |
| S7-UNIT | 1050 passed in 8.97s | 0 |
| S7-ARCH | 373 passed, 50 warnings in 28.54s | 0 |
| S7-SCHEMA | 45 passed, 66 warnings in 33.67s | 0 |
| S7-EXEC | 19 passed, 38 warnings in 25.12s | 0 |
| S7-RACES | 23 passed, 47 warnings in 29.93s | 0 |
| S7-REG3 | 561 passed, 548 warnings in 509.18s (0:08:29) | 0 |
| S7-REG2 | 155 passed, 360 warnings in 170.95s (0:02:50) | 0 |
| S7-PREVIEW | 2 passed, 2 warnings in 1.78s | 0 |
| H-U | 18 passed, 5 warnings in 13.70s | 0 |
| PG-R | 45 passed, 98 warnings in 47.09s | 0 |
| PG-N | See raw output | 0 |
| AUDIT | See raw output | 0 |
| FOCUS | 35 passed, 50 warnings in 24.13s | 0 |

### DIFF

```sh
git diff --check HEAD
```

Raw stdout/stderr: empty (zero bytes).

Exit code: **0**.

### LINT

```sh
uv run ruff check .
```

```text
All checks passed!
```

Exit code: **0**.

### FORMAT

```sh
uv run ruff format --check .
```

```text
948 files already formatted
```

Exit code: **0**.

### TYPE

```sh
uv run pyright
```

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: **0**.

### HEAD

```sh
uv run alembic heads
```

```text
0081_agent_execution_intents (head)
```

Exit code: **0**.

### UNIT-ARCH

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/phase3 tests/architecture tests/unit/architecture
```

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 35%]
........................................................................ [ 40%]
........................................................................ [ 45%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 60%]
........................................................................ [ 65%]
........................................................................ [ 70%]
........................................................................ [ 75%]
........................................................................ [ 80%]
........................................................................ [ 86%]
........................................................................ [ 91%]
........................................................................ [ 96%]
.......................................................                  [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1423 passed, 50 warnings in 35.98s
```

Exit code: **0**.

### INTENT

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase3/test_pr3_02_s2_intent_*.py
```

```text
........................................................................ [ 79%]
...................                                                      [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 50 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 16 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 24 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
91 passed, 151 warnings in 82.58s (0:01:22)
```

Exit code: **0**.

### COLLECT

```sh
uv run pytest -o addopts='' --collect-only -q tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot
```

```text
tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]

4 tests collected in 0.26s
```

Exit code: **0**.

### COLLECT-NODES

```sh
uv run pytest -o addopts='' --collect-only -q tests/unit/phase3/test_agent_execution_repository.py tests/integration/phase3/test_pr3_02_s2_intent_*.py
```

```text
tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]
tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys
tests/unit/phase3/test_agent_execution_repository.py::test_intent_diagnostics_are_translated_by_exact_state_and_tag
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[40001-3]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[40P01-3]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[55P03-1]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[57014-1]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[task_row]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[version_row]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_same_command_revision_and_existing_writer_races
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait[membership]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait[credential]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_task_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_phase2_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_gateway_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[40001]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[40P01]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[55P03]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[57014]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary[human_researcher]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary[agent]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[stale-CONCURRENT_MODIFICATION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unsealed-INVALID_STATE_TRANSITION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unavailable-INVALID_STATE_TRANSITION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[viewer-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[other_agent-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[untrusted-AUTHENTICATION_REQUIRED]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[pins-FROZEN_REFERENCE_REQUIRED]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[bytes-PROVENANCE_CLOSURE_VIOLATION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[scope-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unfrozen-VERSION_NOT_FROZEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_command_receipts]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[constraints]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[credentials]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_selected_step_and_typed_inputs_preserve_both_owners
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[advisory-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[missing_receipt-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[actor-pr302s2_scope]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[state-pr302s2_state]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[binding-pr302s2_binding]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[not_frozen-pr302s2_not_frozen]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[hash-pr302s2_provenance]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[event-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[partial-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[request_hash-pr302s2_provenance]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history[agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history[agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_unresolved_input_material_diagnostic
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_exact_intent_schema_and_scoped_foreign_keys
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change[False]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change[True]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[expected_task_revision]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[harness_artifact_version_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[agent_version_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[research_task_step_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[execution_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[research_task_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_queries_are_coherent_bounded_snapshots

101 tests collected in 0.05s
```

Exit code: **0**.

### S7-UNIT

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 1050 items

tests/unit/phase3/test_agent_execution_contracts.py .............        [  1%]
tests/unit/phase3/test_agent_execution_repository.py ..........          [  2%]
tests/unit/phase3/test_agent_identity_contracts.py .                     [  2%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  4%]
........................................                                 [  8%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [ 10%]
........................................................................ [ 17%]
....                                                                     [ 18%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_canonical_context.py .......................      [ 22%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 24%]
........................................................................ [ 31%]
........................................................................ [ 38%]
...................................................................      [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 46%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 57%]
tests/unit/phase3/test_capability_routing.py ........................... [ 60%]
........................................................                 [ 65%]
tests/unit/phase3/test_context_contracts.py ...............              [ 67%]
tests/unit/phase3/test_gateway_input_validation.py ..................... [ 69%]
.........                                                                [ 70%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 71%]
tests/unit/phase3/test_promotion_context.py ..                           [ 71%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 73%]
....................................................                     [ 78%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 81%]
........................................................................ [ 88%]
.                                                                        [ 88%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 90%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 91%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_memory.py ..                                 [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 94%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 99%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 1050 passed in 8.97s =============================
```

Exit code: **0**.

### S7-ARCH

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 373 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  2%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  5%]
tests/architecture/test_b07_revision_decisions.py ...                    [  6%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 12%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 13%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 15%]
tests/architecture/test_b17_boundaries.py ...                            [ 16%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 17%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 17%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 18%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 19%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 20%]
tests/architecture/test_b25_boundaries.py ...                            [ 20%]
tests/architecture/test_b26_boundaries.py ...                            [ 21%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 22%]
tests/architecture/test_b32_boundaries.py ................               [ 26%]
tests/architecture/test_basic_approval.py ...                            [ 27%]
tests/architecture/test_import_boundaries.py .............               [ 31%]
tests/architecture/test_m1_boundaries.py ...                             [ 31%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 38%]
tests/architecture/test_pr12_boundaries.py ....                          [ 39%]
tests/architecture/test_pr13_boundaries.py ..                            [ 40%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 41%]
tests/architecture/test_pr14_boundaries.py ..                            [ 41%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 42%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 43%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 45%]
tests/architecture/test_pr18_boundaries.py .......                       [ 47%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 48%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 53%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 58%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 60%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 67%]
................................                                         [ 76%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 77%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 77%]
tests/architecture/test_pr3_02_s2_boundaries.py ..                       [ 78%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
tests/architecture/test_pr3_05_readonly_boundaries.py .....              [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 373 passed, 50 warnings in 28.54s =======================
```

Exit code: **0**.

### S7-SCHEMA

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_intent_guards.py tests/integration/phase3/test_pr3_02_s2_intent_migration.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 45 items

tests/integration/phase3/test_pr3_02_s2_intent_guards.py ............... [ 33%]
........................                                                 [ 86%]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py ......       [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 50 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 16 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 45 passed, 66 warnings in 33.67s =======================
```

Exit code: **0**.

### S7-EXEC

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_intent_execution.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 19 items

tests/integration/phase3/test_pr3_02_s2_intent_execution.py ............ [ 63%]
.......                                                                  [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 19 passed, 38 warnings in 25.12s =======================
```

Exit code: **0**.

### S7-RACES

```sh
uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py tests/integration/phase3/test_pr3_02_s2_intent_replay.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 23 items

tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 13.292, "error_code": null, "level": "INFO", "project_id": "40ddcd09-6127-413e-bd90-1925a59328c0", "request_id": "0bbd0303-d681-480a-bbcf-7e245ad24a74", "result": "success", "rollback": false, "target_id": "40ddcd09-6127-413e-bd90-1925a59328c0", "timestamp": "2026-10-26T01:21:38.555246+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.556413+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.096, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.556462+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.136, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.556488+00:00"}
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 7.492, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0bbd0303-d681-480a-bbcf-7e245ad24a74", "result": "success", "rollback": false, "target_id": "01a175cc-7efa-7ae9-b604-21f9ecc68c4a", "timestamp": "2026-10-26T01:21:38.564024+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.564739+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.677, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.564781+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.712, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-7eff-71c3-a6c3-438143369a4d", "timestamp": "2026-10-26T01:21:38.564806+00:00"}
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.331, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0bbd0303-d681-480a-bbcf-7e245ad24a74", "result": "success", "rollback": false, "target_id": "01a175cc-7eff-71c3-a6c3-438143369a4d", "timestamp": "2026-10-26T01:21:38.568175+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.568711+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.496, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.568744+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.524, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-7eff-71c3-a6c3-438143369a4d", "timestamp": "2026-10-26T01:21:38.568764+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.889, "error_code": null, "level": "INFO", "project_id": "40ddcd09-6127-413e-bd90-1925a59328c0", "request_id": "3501ba6a-92d3-4244-8a08-1680b084a78d", "result": "success", "rollback": false, "target_id": "40ddcd09-6127-413e-bd90-1925a59328c0", "timestamp": "2026-10-26T01:21:38.717381+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.718029+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.594, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.718059+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.622, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.718079+00:00"}
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.997, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3501ba6a-92d3-4244-8a08-1680b084a78d", "result": "success", "rollback": false, "target_id": "01a175cc-7f9c-716b-8150-aadf893387dd", "timestamp": "2026-10-26T01:21:38.723103+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.723598+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.723635+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.497, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-7fa0-741f-ab2d-63cab84620a8", "timestamp": "2026-10-26T01:21:38.723651+00:00"}
INFO  [researchbase.commands] {"actor_id": "f97e5e78-4293-4d9c-a4cb-c92dc0b3299d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.668, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3501ba6a-92d3-4244-8a08-1680b084a78d", "result": "success", "rollback": false, "target_id": "01a175cc-7fa0-741f-ab2d-63cab84620a8", "timestamp": "2026-10-26T01:21:38.726344+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.726766+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.404, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:38.726795+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.428, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-7fa0-741f-ab2d-63cab84620a8", "timestamp": "2026-10-26T01:21:38.726814+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:38.740703+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:39.441366+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_7f092c1ac2834affbbae05aece8f6027
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_7f092c1ac2834affbbae05aece8f6027
wait evidence first_share {'xact_start': datetime.datetime(2026, 10, 25, 21, 21, 38, 741115, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 21, 21, 38, 741146, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 21, 21, 38, 749276, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_membership_events, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions, strategy_candidate_captures, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE', 'expiry_at': datetime.datetime(2026, 10, 25, 21, 21, 39, 429833, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 21, 21, 38, 749276, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 21, 21, 39, 439367, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 1, 21, 39, 441217, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_7f092c1ac2834affbbae05aece8f6027
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.131, "error_code": null, "level": "INFO", "project_id": "a2079275-50a9-4327-a6b3-d3653cf8d4cf", "request_id": "f24d316d-9cea-40b4-bb46-2f0e6625ac7f", "result": "success", "rollback": false, "target_id": "a2079275-50a9-4327-a6b3-d3653cf8d4cf", "timestamp": "2026-10-26T01:21:40.377543+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.378235+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.656, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.378267+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.682, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.378285+00:00"}
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.269, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f24d316d-9cea-40b4-bb46-2f0e6625ac7f", "result": "success", "rollback": false, "target_id": "01a175cc-8618-79e3-a083-caa9156e6d2b", "timestamp": "2026-10-26T01:21:40.383580+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.384050+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.384077+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.47, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-861c-7a82-bf03-2b268eb291ca", "timestamp": "2026-10-26T01:21:40.384092+00:00"}
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.455, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f24d316d-9cea-40b4-bb46-2f0e6625ac7f", "result": "success", "rollback": false, "target_id": "01a175cc-861c-7a82-bf03-2b268eb291ca", "timestamp": "2026-10-26T01:21:40.386575+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.387031+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.437, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.387056+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.458, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-861c-7a82-bf03-2b268eb291ca", "timestamp": "2026-10-26T01:21:40.387072+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.804, "error_code": null, "level": "INFO", "project_id": "a2079275-50a9-4327-a6b3-d3653cf8d4cf", "request_id": "44fc5a9a-c858-4e70-8000-d040c26980dc", "result": "success", "rollback": false, "target_id": "a2079275-50a9-4327-a6b3-d3653cf8d4cf", "timestamp": "2026-10-26T01:21:40.525935+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.527703+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.735, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.527736+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.758, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.527752+00:00"}
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.365, "error_code": null, "level": "INFO", "project_id": null, "request_id": "44fc5a9a-c858-4e70-8000-d040c26980dc", "result": "success", "rollback": false, "target_id": "01a175cc-86ad-7bbd-81cb-70857900c7d7", "timestamp": "2026-10-26T01:21:40.532143+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.532518+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.364, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.532555+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.394, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-86b1-7423-b8e2-37ab6d667b16", "timestamp": "2026-10-26T01:21:40.532579+00:00"}
INFO  [researchbase.commands] {"actor_id": "8dd87b2a-ad7f-4a0c-94f5-6136f20c88e6", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.238, "error_code": null, "level": "INFO", "project_id": null, "request_id": "44fc5a9a-c858-4e70-8000-d040c26980dc", "result": "success", "rollback": false, "target_id": "01a175cc-86b1-7423-b8e2-37ab6d667b16", "timestamp": "2026-10-26T01:21:40.534843+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.535209+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.355, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:40.535233+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.375, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-86b1-7423-b8e2-37ab6d667b16", "timestamp": "2026-10-26T01:21:40.535249+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:40.548651+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:41.251285+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_9f0ae963af644149873591b96bcca5b6
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_9f0ae963af644149873591b96bcca5b6
wait evidence second_key {'xact_start': datetime.datetime(2026, 10, 25, 21, 21, 40, 549027, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 21, 21, 40, 554222, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 21, 21, 40, 555538, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT pg_advisory_xact_lock(hashtextextended($1,0))', 'expiry_at': datetime.datetime(2026, 10, 25, 21, 21, 41, 238194, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 21, 21, 40, 555538, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 21, 21, 41, 248609, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 1, 21, 41, 250866, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_9f0ae963af644149873591b96bcca5b6
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.196, "error_code": null, "level": "INFO", "project_id": "9a66f697-b894-4e4b-90cd-277d92444dff", "request_id": "aef83b45-051c-410c-a3d5-70a5f38927f6", "result": "success", "rollback": false, "target_id": "9a66f697-b894-4e4b-90cd-277d92444dff", "timestamp": "2026-10-26T01:21:42.253639+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.254293+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.602, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.254333+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.63, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.254352+00:00"}
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.683, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aef83b45-051c-410c-a3d5-70a5f38927f6", "result": "success", "rollback": false, "target_id": "01a175cc-8d6c-7841-9301-34fb1c95dbf4", "timestamp": "2026-10-26T01:21:42.260063+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.260684+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.594, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.260714+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.617, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-8d70-72d4-8d22-a36047b966cb", "timestamp": "2026-10-26T01:21:42.260730+00:00"}
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.391, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aef83b45-051c-410c-a3d5-70a5f38927f6", "result": "success", "rollback": false, "target_id": "01a175cc-8d70-72d4-8d22-a36047b966cb", "timestamp": "2026-10-26T01:21:42.263146+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.263556+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.39, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.263580+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-8d70-72d4-8d22-a36047b966cb", "timestamp": "2026-10-26T01:21:42.263598+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.674, "error_code": null, "level": "INFO", "project_id": "9a66f697-b894-4e4b-90cd-277d92444dff", "request_id": "3bea4fe8-32d0-4c3f-906c-c34ad589b3a9", "result": "success", "rollback": false, "target_id": "9a66f697-b894-4e4b-90cd-277d92444dff", "timestamp": "2026-10-26T01:21:42.402995+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.403646+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.543, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.403677+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.566, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.403694+00:00"}
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.345, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3bea4fe8-32d0-4c3f-906c-c34ad589b3a9", "result": "success", "rollback": false, "target_id": "01a175cc-8e02-7142-b87c-bd3a5e76e924", "timestamp": "2026-10-26T01:21:42.408062+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.408469+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.39, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.408501+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.428, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-8e05-760e-958d-d6f379437027", "timestamp": "2026-10-26T01:21:42.408534+00:00"}
INFO  [researchbase.commands] {"actor_id": "2ba0cd9a-f0bf-4621-94c0-30c31119e01e", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.329, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3bea4fe8-32d0-4c3f-906c-c34ad589b3a9", "result": "success", "rollback": false, "target_id": "01a175cc-8e05-760e-958d-d6f379437027", "timestamp": "2026-10-26T01:21:42.410890+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.411218+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.316, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:42.411243+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.339, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-8e05-760e-958d-d6f379437027", "timestamp": "2026-10-26T01:21:42.411260+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:42.422961+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:43.119913+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_5b87dc803a9c4d338845c8e899357133
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_5b87dc803a9c4d338845c8e899357133
wait evidence task_row {'xact_start': datetime.datetime(2026, 10, 25, 21, 21, 42, 423319, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 21, 21, 42, 430066, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 21, 21, 42, 444322, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT id FROM research_tasks WHERE id=$1 FOR UPDATE', 'expiry_at': datetime.datetime(2026, 10, 25, 21, 21, 43, 113706, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 21, 21, 42, 444322, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 21, 21, 43, 117715, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 1, 21, 43, 119701, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_5b87dc803a9c4d338845c8e899357133
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.071, "error_code": null, "level": "INFO", "project_id": "ed1236b8-21e1-43a1-bd6e-10b513d9ae8a", "request_id": "78c321ab-93b3-49fe-82bc-0e3e1dc578ac", "result": "success", "rollback": false, "target_id": "ed1236b8-21e1-43a1-bd6e-10b513d9ae8a", "timestamp": "2026-10-26T01:21:44.192874+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.193596+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.684, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.193631+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.711, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.193650+00:00"}
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.85, "error_code": null, "level": "INFO", "project_id": null, "request_id": "78c321ab-93b3-49fe-82bc-0e3e1dc578ac", "result": "success", "rollback": false, "target_id": "01a175cc-9500-7c0e-ae31-fa502e553f6d", "timestamp": "2026-10-26T01:21:44.198528+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.199023+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.199055+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.506, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9503-7ae4-a5c6-33db6ae6633c", "timestamp": "2026-10-26T01:21:44.199082+00:00"}
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.352, "error_code": null, "level": "INFO", "project_id": null, "request_id": "78c321ab-93b3-49fe-82bc-0e3e1dc578ac", "result": "success", "rollback": false, "target_id": "01a175cc-9503-7ae4-a5c6-33db6ae6633c", "timestamp": "2026-10-26T01:21:44.201463+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.201811+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.332, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.201838+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9503-7ae4-a5c6-33db6ae6633c", "timestamp": "2026-10-26T01:21:44.201854+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.91, "error_code": null, "level": "INFO", "project_id": "ed1236b8-21e1-43a1-bd6e-10b513d9ae8a", "request_id": "e70438c3-291d-4a45-a130-81c4c17ec874", "result": "success", "rollback": false, "target_id": "ed1236b8-21e1-43a1-bd6e-10b513d9ae8a", "timestamp": "2026-10-26T01:21:44.397037+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.397806+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.726, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.397834+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.775, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.397877+00:00"}
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.566, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e70438c3-291d-4a45-a130-81c4c17ec874", "result": "success", "rollback": false, "target_id": "01a175cc-95cc-79c5-b3ce-a127f5a5fc51", "timestamp": "2026-10-26T01:21:44.403489+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.404219+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.701, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.404254+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.75, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-95cf-7ccb-b359-0352761669bd", "timestamp": "2026-10-26T01:21:44.404295+00:00"}
INFO  [researchbase.commands] {"actor_id": "7434e7a8-c2f4-41b6-9e75-5fe7bfa30da9", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.773, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e70438c3-291d-4a45-a130-81c4c17ec874", "result": "success", "rollback": false, "target_id": "01a175cc-95cf-7ccb-b359-0352761669bd", "timestamp": "2026-10-26T01:21:44.407116+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.407478+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.347, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:44.407509+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.371, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-95cf-7ccb-b359-0352761669bd", "timestamp": "2026-10-26T01:21:44.407528+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:44.420832+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:45.116962+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_1fa877a4d1c243d1b671462a4c405555
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_1fa877a4d1c243d1b671462a4c405555
wait evidence version_row {'xact_start': datetime.datetime(2026, 10, 25, 21, 21, 44, 421217, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 21, 21, 44, 429862, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 21, 21, 44, 430229, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT id FROM agent_versions WHERE id=$1 FOR UPDATE', 'expiry_at': datetime.datetime(2026, 10, 25, 21, 21, 45, 110642, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 21, 21, 44, 430229, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 21, 21, 45, 114916, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 1, 21, 45, 116711, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_1fa877a4d1c243d1b671462a4c405555
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.523, "error_code": null, "level": "INFO", "project_id": "d0622e6f-a95a-4dc0-ad53-a563d0733868", "request_id": "cdc965c9-0568-4821-80d2-7b99b8369fe2", "result": "success", "rollback": false, "target_id": "d0622e6f-a95a-4dc0-ad53-a563d0733868", "timestamp": "2026-10-26T01:21:46.116004+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.116748+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.694, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.116790+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.73, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.116814+00:00"}
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.816, "error_code": null, "level": "INFO", "project_id": null, "request_id": "cdc965c9-0568-4821-80d2-7b99b8369fe2", "result": "success", "rollback": false, "target_id": "01a175cc-9c83-77e4-a568-f9929446f6c0", "timestamp": "2026-10-26T01:21:46.122665+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.123214+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.523, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.123261+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.554, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9c87-785b-b822-14ec7ba3a24c", "timestamp": "2026-10-26T01:21:46.123283+00:00"}
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.977, "error_code": null, "level": "INFO", "project_id": null, "request_id": "cdc965c9-0568-4821-80d2-7b99b8369fe2", "result": "success", "rollback": false, "target_id": "01a175cc-9c87-785b-b822-14ec7ba3a24c", "timestamp": "2026-10-26T01:21:46.126302+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.126716+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.388, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.126738+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.409, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9c87-785b-b822-14ec7ba3a24c", "timestamp": "2026-10-26T01:21:46.126753+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.689, "error_code": null, "level": "INFO", "project_id": "d0622e6f-a95a-4dc0-ad53-a563d0733868", "request_id": "3a463281-d28a-47af-8a8b-62cda53bafee", "result": "success", "rollback": false, "target_id": "d0622e6f-a95a-4dc0-ad53-a563d0733868", "timestamp": "2026-10-26T01:21:46.269998+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.270529+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.491, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.270558+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.514, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.270575+00:00"}
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.93, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3a463281-d28a-47af-8a8b-62cda53bafee", "result": "success", "rollback": false, "target_id": "01a175cc-9d1d-7aea-a216-87b4d40fd345", "timestamp": "2026-10-26T01:21:46.274528+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.274876+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.341, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.274912+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.365, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9d20-7a10-8b0d-e3a0c2482113", "timestamp": "2026-10-26T01:21:46.274930+00:00"}
INFO  [researchbase.commands] {"actor_id": "f93b5d19-9150-4b0d-82ea-bb33169aa009", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.165, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3a463281-d28a-47af-8a8b-62cda53bafee", "result": "success", "rollback": false, "target_id": "01a175cc-9d20-7a10-8b0d-e3a0c2482113", "timestamp": "2026-10-26T01:21:46.277121+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.277488+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.357, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:46.277517+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.379, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-9d20-7a10-8b0d-e3a0c2482113", "timestamp": "2026-10-26T01:21:46.277533+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.283281+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.288550+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:46.363277+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_f8723a44cfb446578cca1ce18f5ca34a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_f8723a44cfb446578cca1ce18f5ca34a
.DISPOSABLE_DROPPED: researchbase_pr212_test_f8723a44cfb446578cca1ce18f5ca34a
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.572, "error_code": null, "level": "INFO", "project_id": "ab321e7e-04cc-439d-9c24-12fdab1f4e8d", "request_id": "7a7b488e-0c36-44e6-9f4b-29e834d0ac57", "result": "success", "rollback": false, "target_id": "ab321e7e-04cc-439d-9c24-12fdab1f4e8d", "timestamp": "2026-10-26T01:21:47.599819+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.600702+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.828, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.600745+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.86, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.600770+00:00"}
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.441, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7a7b488e-0c36-44e6-9f4b-29e834d0ac57", "result": "success", "rollback": false, "target_id": "01a175cc-a24e-70e9-b490-c81d82eeb953", "timestamp": "2026-10-26T01:21:47.606245+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.606856+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.576, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.606883+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.601, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a252-72fe-94d2-d16cc35b9c76", "timestamp": "2026-10-26T01:21:47.606901+00:00"}
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 14.722, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7a7b488e-0c36-44e6-9f4b-29e834d0ac57", "result": "success", "rollback": false, "target_id": "01a175cc-a252-72fe-94d2-d16cc35b9c76", "timestamp": "2026-10-26T01:21:47.621648+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.622334+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.649, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.622359+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.672, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a252-72fe-94d2-d16cc35b9c76", "timestamp": "2026-10-26T01:21:47.622374+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.801, "error_code": null, "level": "INFO", "project_id": "ab321e7e-04cc-439d-9c24-12fdab1f4e8d", "request_id": "c0b9710b-6388-42d3-a43e-8d2fa3b710f9", "result": "success", "rollback": false, "target_id": "ab321e7e-04cc-439d-9c24-12fdab1f4e8d", "timestamp": "2026-10-26T01:21:47.769119+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.769748+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.596, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.769785+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.622, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.769803+00:00"}
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.746, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c0b9710b-6388-42d3-a43e-8d2fa3b710f9", "result": "success", "rollback": false, "target_id": "01a175cc-a2f8-729b-836b-87669b81ef86", "timestamp": "2026-10-26T01:21:47.774575+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.775048+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.456, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.775082+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.478, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a2fb-7945-a9f8-eee9d702dce7", "timestamp": "2026-10-26T01:21:47.775098+00:00"}
INFO  [researchbase.commands] {"actor_id": "0cd373e4-572b-4ce2-a5c0-f62e1f16f5fe", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.55, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c0b9710b-6388-42d3-a43e-8d2fa3b710f9", "result": "success", "rollback": false, "target_id": "01a175cc-a2fb-7945-a9f8-eee9d702dce7", "timestamp": "2026-10-26T01:21:47.777671+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.778119+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.429, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:47.778144+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.452, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a2fb-7945-a9f8-eee9d702dce7", "timestamp": "2026-10-26T01:21:47.778162+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.799037+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:47.815220+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_aaec23b4c8e34ebf871cf070e84ae2b0
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_aaec23b4c8e34ebf871cf070e84ae2b0
.DISPOSABLE_DROPPED: researchbase_pr212_test_aaec23b4c8e34ebf871cf070e84ae2b0
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.476, "error_code": null, "level": "INFO", "project_id": "d0b89fc1-290f-499f-815f-4bb784dec0fd", "request_id": "3b80bfd3-cb21-4bb3-84fb-ef2a6a9bdc1e", "result": "success", "rollback": false, "target_id": "d0b89fc1-290f-499f-815f-4bb784dec0fd", "timestamp": "2026-10-26T01:21:48.765939+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.767325+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.324, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.767377+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.364, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.767404+00:00"}
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.642, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3b80bfd3-cb21-4bb3-84fb-ef2a6a9bdc1e", "result": "success", "rollback": false, "target_id": "01a175cc-a6dc-77a6-aca9-a7eae20171a4", "timestamp": "2026-10-26T01:21:48.774087+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.774706+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.583, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.774750+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.617, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a6e2-7245-acb4-1f56e995062d", "timestamp": "2026-10-26T01:21:48.774775+00:00"}
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3b80bfd3-cb21-4bb3-84fb-ef2a6a9bdc1e", "result": "success", "rollback": false, "target_id": "01a175cc-a6e2-7245-acb4-1f56e995062d", "timestamp": "2026-10-26T01:21:48.778301+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.779116+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.772, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.779158+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.8, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a6e2-7245-acb4-1f56e995062d", "timestamp": "2026-10-26T01:21:48.779176+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.044, "error_code": null, "level": "INFO", "project_id": "d0b89fc1-290f-499f-815f-4bb784dec0fd", "request_id": "080e1ab2-05a3-452b-939c-c05d04485d02", "result": "success", "rollback": false, "target_id": "d0b89fc1-290f-499f-815f-4bb784dec0fd", "timestamp": "2026-10-26T01:21:48.932331+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.933121+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.762, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.933164+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.794, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.933190+00:00"}
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.054, "error_code": null, "level": "INFO", "project_id": null, "request_id": "080e1ab2-05a3-452b-939c-c05d04485d02", "result": "success", "rollback": false, "target_id": "01a175cc-a783-7b04-a209-6e19f498f556", "timestamp": "2026-10-26T01:21:48.939273+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.939829+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.518, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.939857+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.54, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a787-7c99-bebb-c8fc268875d5", "timestamp": "2026-10-26T01:21:48.939872+00:00"}
INFO  [researchbase.commands] {"actor_id": "36a89dd8-838f-41ac-88da-f03f665758b4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.685, "error_code": null, "level": "INFO", "project_id": null, "request_id": "080e1ab2-05a3-452b-939c-c05d04485d02", "result": "success", "rollback": false, "target_id": "01a175cc-a787-7c99-bebb-c8fc268875d5", "timestamp": "2026-10-26T01:21:48.942581+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.943139+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.563, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:48.943184+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.587, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-a787-7c99-bebb-c8fc268875d5", "timestamp": "2026-10-26T01:21:48.943202+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.962232+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:48.978463+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_dd0b1651a5d242df8b7234ec9f4d0268
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_dd0b1651a5d242df8b7234ec9f4d0268
.DISPOSABLE_DROPPED: researchbase_pr212_test_dd0b1651a5d242df8b7234ec9f4d0268
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.968, "error_code": null, "level": "INFO", "project_id": "b8debd77-d9f7-4ddb-9004-f7b62d4f9c90", "request_id": "afa04832-b1f5-4d94-bbbf-bcc47f069aea", "result": "success", "rollback": false, "target_id": "b8debd77-d9f7-4ddb-9004-f7b62d4f9c90", "timestamp": "2026-10-26T01:21:49.881105+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:49.881693+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.549, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:49.881727+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.577, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:49.881748+00:00"}
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.862, "error_code": null, "level": "INFO", "project_id": null, "request_id": "afa04832-b1f5-4d94-bbbf-bcc47f069aea", "result": "success", "rollback": false, "target_id": "01a175cc-ab38-76d5-a1b1-cd85e5e5fd57", "timestamp": "2026-10-26T01:21:49.886635+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:49.887101+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.421, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:49.887132+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.444, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ab3b-76c5-904b-baceafa55827", "timestamp": "2026-10-26T01:21:49.887147+00:00"}
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.724, "error_code": null, "level": "INFO", "project_id": null, "request_id": "afa04832-b1f5-4d94-bbbf-bcc47f069aea", "result": "success", "rollback": false, "target_id": "01a175cc-ab3b-76c5-904b-baceafa55827", "timestamp": "2026-10-26T01:21:49.889897+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:49.890356+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.429, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:49.890387+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.453, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ab3b-76c5-904b-baceafa55827", "timestamp": "2026-10-26T01:21:49.890403+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.611, "error_code": null, "level": "INFO", "project_id": "b8debd77-d9f7-4ddb-9004-f7b62d4f9c90", "request_id": "d44b9085-13c1-4675-8991-8343fd7aaef4", "result": "success", "rollback": false, "target_id": "b8debd77-d9f7-4ddb-9004-f7b62d4f9c90", "timestamp": "2026-10-26T01:21:50.014332+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:50.014949+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.579, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:50.014978+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.604, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:50.014996+00:00"}
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.101, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d44b9085-13c1-4675-8991-8343fd7aaef4", "result": "success", "rollback": false, "target_id": "01a175cc-abbd-776b-a3aa-f80f7a889d65", "timestamp": "2026-10-26T01:21:50.019121+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:50.019481+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.349, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:50.019512+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.394, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-abc0-7d91-96bb-67b046639627", "timestamp": "2026-10-26T01:21:50.019552+00:00"}
INFO  [researchbase.commands] {"actor_id": "ca15ef0a-5aaf-411c-93c1-59cc06eabeb9", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.642, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d44b9085-13c1-4675-8991-8343fd7aaef4", "result": "success", "rollback": false, "target_id": "01a175cc-abc0-7d91-96bb-67b046639627", "timestamp": "2026-10-26T01:21:50.022222+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:50.022559+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.333, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:50.022592+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.353, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-abc0-7d91-96bb-67b046639627", "timestamp": "2026-10-26T01:21:50.022607+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:50.035332+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "INVALID_STATE_TRANSITION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:50.056801+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_dcb541b6bf0848cb996d806ea5b880d3
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_dcb541b6bf0848cb996d806ea5b880d3
.DISPOSABLE_DROPPED: researchbase_pr212_test_dcb541b6bf0848cb996d806ea5b880d3
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.718, "error_code": null, "level": "INFO", "project_id": "4ace293a-491d-437e-87a6-c30a8ee0a33a", "request_id": "3baaa9ca-3afd-41e1-bf91-b2b7311083c5", "result": "success", "rollback": false, "target_id": "4ace293a-491d-437e-87a6-c30a8ee0a33a", "timestamp": "2026-10-26T01:21:51.013632+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.015172+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.497, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.015221+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.528, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.015243+00:00"}
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.065, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3baaa9ca-3afd-41e1-bf91-b2b7311083c5", "result": "success", "rollback": false, "target_id": "01a175cc-afa4-7ec9-86fe-17812f8d46e8", "timestamp": "2026-10-26T01:21:51.021337+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.021953+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.591, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.021998+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.631, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-afa9-79e2-b414-556db6054ffe", "timestamp": "2026-10-26T01:21:51.022030+00:00"}
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.228, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3baaa9ca-3afd-41e1-bf91-b2b7311083c5", "result": "success", "rollback": false, "target_id": "01a175cc-afa9-79e2-b414-556db6054ffe", "timestamp": "2026-10-26T01:21:51.025291+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.026009+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.691, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.026038+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.715, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-afa9-79e2-b414-556db6054ffe", "timestamp": "2026-10-26T01:21:51.026056+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.806, "error_code": null, "level": "INFO", "project_id": "4ace293a-491d-437e-87a6-c30a8ee0a33a", "request_id": "7a69802d-cd2e-4a11-801f-6fb3e7bc6e53", "result": "success", "rollback": false, "target_id": "4ace293a-491d-437e-87a6-c30a8ee0a33a", "timestamp": "2026-10-26T01:21:51.172655+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.173412+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.72, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.173441+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.744, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.173459+00:00"}
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.318, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7a69802d-cd2e-4a11-801f-6fb3e7bc6e53", "result": "success", "rollback": false, "target_id": "01a175cc-b043-7959-9293-accea503d927", "timestamp": "2026-10-26T01:21:51.177800+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.178305+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.178330+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.509, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b047-79f3-99c5-4d5ea131c432", "timestamp": "2026-10-26T01:21:51.178345+00:00"}
INFO  [researchbase.commands] {"actor_id": "b15f7dff-5cab-48c4-a30f-380385642dd3", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.537, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7a69802d-cd2e-4a11-801f-6fb3e7bc6e53", "result": "success", "rollback": false, "target_id": "01a175cc-b047-79f3-99c5-4d5ea131c432", "timestamp": "2026-10-26T01:21:51.180905+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.181390+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.479, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:51.181421+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.503, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b047-79f3-99c5-4d5ea131c432", "timestamp": "2026-10-26T01:21:51.181441+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.203411+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "INVALID_STATE_TRANSITION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:51.221792+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_454ac946332b4060a4469602a6df32c0
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_454ac946332b4060a4469602a6df32c0
.DISPOSABLE_DROPPED: researchbase_pr212_test_454ac946332b4060a4469602a6df32c0
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.344, "error_code": null, "level": "INFO", "project_id": "3cbefe0e-36d2-449b-8b60-0e9c402538a9", "request_id": "519edf15-f2f8-4431-a7fb-71a0f49d990d", "result": "success", "rollback": false, "target_id": "3cbefe0e-36d2-449b-8b60-0e9c402538a9", "timestamp": "2026-10-26T01:21:52.267675+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.268436+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.701, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.268471+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.733, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.268490+00:00"}
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.549, "error_code": null, "level": "INFO", "project_id": null, "request_id": "519edf15-f2f8-4431-a7fb-71a0f49d990d", "result": "success", "rollback": false, "target_id": "01a175cc-b48a-7cf5-9e6e-3d7762cfa355", "timestamp": "2026-10-26T01:21:52.274065+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.274559+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.452, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.274590+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.479, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b48e-7a84-b892-054a07d17118", "timestamp": "2026-10-26T01:21:52.274608+00:00"}
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.783, "error_code": null, "level": "INFO", "project_id": null, "request_id": "519edf15-f2f8-4431-a7fb-71a0f49d990d", "result": "success", "rollback": false, "target_id": "01a175cc-b48e-7a84-b892-054a07d17118", "timestamp": "2026-10-26T01:21:52.277418+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.277887+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.46, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.277929+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.497, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b48e-7a84-b892-054a07d17118", "timestamp": "2026-10-26T01:21:52.277959+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.033, "error_code": null, "level": "INFO", "project_id": "3cbefe0e-36d2-449b-8b60-0e9c402538a9", "request_id": "b1c97208-a921-4d3a-b2ff-2802c2ca978b", "result": "success", "rollback": false, "target_id": "3cbefe0e-36d2-449b-8b60-0e9c402538a9", "timestamp": "2026-10-26T01:21:52.434820+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.436298+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.369, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.436344+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.417, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.436370+00:00"}
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.709, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b1c97208-a921-4d3a-b2ff-2802c2ca978b", "result": "success", "rollback": false, "target_id": "01a175cc-b531-7d66-85cd-91a71dffa08e", "timestamp": "2026-10-26T01:21:52.443117+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.443587+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.423, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.443617+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.451, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b536-7310-b26e-33a00328d7bb", "timestamp": "2026-10-26T01:21:52.443637+00:00"}
INFO  [researchbase.commands] {"actor_id": "8458243e-a3c1-49be-adef-216065d931db", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.653, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b1c97208-a921-4d3a-b2ff-2802c2ca978b", "result": "success", "rollback": false, "target_id": "01a175cc-b536-7310-b26e-33a00328d7bb", "timestamp": "2026-10-26T01:21:52.446318+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.446676+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.328, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:52.446703+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.352, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b536-7310-b26e-33a00328d7bb", "timestamp": "2026-10-26T01:21:52.446721+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:52.459937+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_382948d3ec9e435291e6d1c6be8a1195
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_382948d3ec9e435291e6d1c6be8a1195
.DISPOSABLE_DROPPED: researchbase_pr212_test_382948d3ec9e435291e6d1c6be8a1195
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.897, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "7d736351-f96d-4a5d-85f5-abdcda3d5880", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.380316+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.380871+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.511, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.380899+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.536, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.380917+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.276, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7d736351-f96d-4a5d-85f5-abdcda3d5880", "result": "success", "rollback": false, "target_id": "01a175cc-b8e3-70a4-bf19-9726783935a1", "timestamp": "2026-10-26T01:21:53.385216+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.385618+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.404, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.385665+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.435, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b8e6-7016-855d-a50448b19d1b", "timestamp": "2026-10-26T01:21:53.385691+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.339, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7d736351-f96d-4a5d-85f5-abdcda3d5880", "result": "success", "rollback": false, "target_id": "01a175cc-b8e6-7016-855d-a50448b19d1b", "timestamp": "2026-10-26T01:21:53.388058+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.388407+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.338, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.388435+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.36, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b8e6-7016-855d-a50448b19d1b", "timestamp": "2026-10-26T01:21:53.388451+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.102, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "b3102193-b311-4be0-99d7-caf837c431cb", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.539375+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.539845+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.451, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.539897+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.491, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.539931+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.104, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b3102193-b311-4be0-99d7-caf837c431cb", "result": "success", "rollback": false, "target_id": "01a175cc-b982-78ce-9c4e-5d5e0432d7cf", "timestamp": "2026-10-26T01:21:53.544081+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.544508+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.409, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.544540+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.434, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b985-7c55-96d8-65903ed9a0bf", "timestamp": "2026-10-26T01:21:53.544559+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.165, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b3102193-b311-4be0-99d7-caf837c431cb", "result": "success", "rollback": false, "target_id": "01a175cc-b985-7c55-96d8-65903ed9a0bf", "timestamp": "2026-10-26T01:21:53.546750+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.547208+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.431, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.547245+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.478, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b985-7c55-96d8-65903ed9a0bf", "timestamp": "2026-10-26T01:21:53.547285+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.656, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "86860ceb-1123-40ca-9270-4ffeba3b6414", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.549205+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.549641+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.407, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.549671+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.43, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.549688+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.744, "error_code": null, "level": "INFO", "project_id": null, "request_id": "86860ceb-1123-40ca-9270-4ffeba3b6414", "result": "success", "rollback": false, "target_id": "01a175cc-b98c-7e7a-811b-50f39bc1193f", "timestamp": "2026-10-26T01:21:53.552458+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.553065+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.575, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.553102+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.606, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b98f-7cbc-bd88-c7ff24e9b733", "timestamp": "2026-10-26T01:21:53.553125+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.181, "error_code": null, "level": "INFO", "project_id": null, "request_id": "86860ceb-1123-40ca-9270-4ffeba3b6414", "result": "success", "rollback": false, "target_id": "01a175cc-b98f-7cbc-bd88-c7ff24e9b733", "timestamp": "2026-10-26T01:21:53.555339+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.555807+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.447, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.555836+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.473, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b98f-7cbc-bd88-c7ff24e9b733", "timestamp": "2026-10-26T01:21:53.555854+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.879, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "26868882-2d20-4dc0-9b29-5bfab595bf31", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.556966+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.557375+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.383, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.557408+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.402, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.557423+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.526, "error_code": null, "level": "INFO", "project_id": null, "request_id": "26868882-2d20-4dc0-9b29-5bfab595bf31", "result": "success", "rollback": false, "target_id": "01a175cc-b994-7e7e-95d0-71de5a2745e5", "timestamp": "2026-10-26T01:21:53.559970+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.560539+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.565, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.560580+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.595, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b996-795f-ac4c-46a1f6fe51d2", "timestamp": "2026-10-26T01:21:53.560605+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.388, "error_code": null, "level": "INFO", "project_id": null, "request_id": "26868882-2d20-4dc0-9b29-5bfab595bf31", "result": "success", "rollback": false, "target_id": "01a175cc-b996-795f-ac4c-46a1f6fe51d2", "timestamp": "2026-10-26T01:21:53.563028+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.563590+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.545, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.563615+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.571, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b996-795f-ac4c-46a1f6fe51d2", "timestamp": "2026-10-26T01:21:53.563636+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.986, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "c1f680c6-258a-48c1-b741-38cb94c5e1d9", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.574056+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.574482+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.395, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.574513+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.418, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.574530+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.58, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c1f680c6-258a-48c1-b741-38cb94c5e1d9", "result": "success", "rollback": false, "target_id": "01a175cc-b9a5-7af4-a84f-db8945e9da76", "timestamp": "2026-10-26T01:21:53.577137+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.577589+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.433, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.577616+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.456, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b9a7-75a8-8ce7-7b6c57ec6954", "timestamp": "2026-10-26T01:21:53.577633+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.206, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c1f680c6-258a-48c1-b741-38cb94c5e1d9", "result": "success", "rollback": false, "target_id": "01a175cc-b9a7-75a8-8ce7-7b6c57ec6954", "timestamp": "2026-10-26T01:21:53.579864+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.580378+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.49, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.580417+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.522, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b9a7-75a8-8ce7-7b6c57ec6954", "timestamp": "2026-10-26T01:21:53.580442+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.981, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "9b07fe97-25d9-4f79-acf2-265c589793a2", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.581484+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.581876+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.378, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.581911+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.411, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.581939+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.82, "error_code": null, "level": "INFO", "project_id": null, "request_id": "9b07fe97-25d9-4f79-acf2-265c589793a2", "result": "success", "rollback": false, "target_id": "01a175cc-b9ad-7b6a-b1a9-5cfe85dd8847", "timestamp": "2026-10-26T01:21:53.584784+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.585213+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.41, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.585264+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b9af-7e8f-afc3-9153834c6ba6", "timestamp": "2026-10-26T01:21:53.585295+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.195, "error_code": null, "level": "INFO", "project_id": null, "request_id": "9b07fe97-25d9-4f79-acf2-265c589793a2", "result": "success", "rollback": false, "target_id": "01a175cc-b9af-7e8f-afc3-9153834c6ba6", "timestamp": "2026-10-26T01:21:53.587527+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.588055+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.512, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.588092+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.556, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-b9af-7e8f-afc3-9153834c6ba6", "timestamp": "2026-10-26T01:21:53.588130+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.589850+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.262, "error_code": null, "level": "INFO", "project_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "request_id": "1607eb67-16da-4c84-8989-32f705f7d899", "result": "success", "rollback": false, "target_id": "e6d479fe-233f-43e8-ada7-320d0d4aa843", "timestamp": "2026-10-26T01:21:53.675456+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.676246+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.746, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.676281+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.774, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.676301+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.997, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1607eb67-16da-4c84-8989-32f705f7d899", "result": "success", "rollback": false, "target_id": "01a175cc-ba0a-75f5-b0d0-9affeb5af35a", "timestamp": "2026-10-26T01:21:53.681328+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.681789+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.441, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.681827+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.467, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ba0e-739a-ada9-1ae5f822abdc", "timestamp": "2026-10-26T01:21:53.681846+00:00"}
INFO  [researchbase.commands] {"actor_id": "28518123-b75f-4d13-a10e-a9b2cf3ddd72", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.881, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1607eb67-16da-4c84-8989-32f705f7d899", "result": "success", "rollback": false, "target_id": "01a175cc-ba0e-739a-ada9-1ae5f822abdc", "timestamp": "2026-10-26T01:21:53.684756+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.685297+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.519, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:53.685341+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.552, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ba0e-739a-ada9-1ae5f822abdc", "timestamp": "2026-10-26T01:21:53.685367+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.688667+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:53.730768+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_a163626956e04e6e97122b76a695bd5d
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_a163626956e04e6e97122b76a695bd5d
.DISPOSABLE_DROPPED: researchbase_pr212_test_a163626956e04e6e97122b76a695bd5d

tests/integration/phase3/test_pr3_02_s2_intent_replay.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.573, "error_code": null, "level": "INFO", "project_id": "304d26db-f9c9-42e3-9b6e-a52641d8349c", "request_id": "326b3574-9167-4c02-b615-303aa80f579f", "result": "success", "rollback": false, "target_id": "304d26db-f9c9-42e3-9b6e-a52641d8349c", "timestamp": "2026-10-26T01:21:55.001113+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.002048+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.881, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.002091+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.917, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.002117+00:00"}
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.436, "error_code": null, "level": "INFO", "project_id": null, "request_id": "326b3574-9167-4c02-b615-303aa80f579f", "result": "success", "rollback": false, "target_id": "01a175cc-bf38-7f69-9125-1fdcb583a7b6", "timestamp": "2026-10-26T01:21:55.007590+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.008277+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.659, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.008320+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.692, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-bf3c-76de-84ee-ce64324817d3", "timestamp": "2026-10-26T01:21:55.008345+00:00"}
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.935, "error_code": null, "level": "INFO", "project_id": null, "request_id": "326b3574-9167-4c02-b615-303aa80f579f", "result": "success", "rollback": false, "target_id": "01a175cc-bf3c-76de-84ee-ce64324817d3", "timestamp": "2026-10-26T01:21:55.011315+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.011806+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.473, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.011844+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.505, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-bf3c-76de-84ee-ce64324817d3", "timestamp": "2026-10-26T01:21:55.011868+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.191, "error_code": null, "level": "INFO", "project_id": "304d26db-f9c9-42e3-9b6e-a52641d8349c", "request_id": "00eeb735-e56a-4349-9f24-a5f86b177dec", "result": "success", "rollback": false, "target_id": "304d26db-f9c9-42e3-9b6e-a52641d8349c", "timestamp": "2026-10-26T01:21:55.165979+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.166859+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.815, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.166897+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.85, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.166921+00:00"}
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.829, "error_code": null, "level": "INFO", "project_id": null, "request_id": "00eeb735-e56a-4349-9f24-a5f86b177dec", "result": "success", "rollback": false, "target_id": "01a175cc-bfdd-7395-b427-d84613953aa3", "timestamp": "2026-10-26T01:21:55.172782+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.173303+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.173345+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.527, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-bfe1-7baf-995f-ebc8f2366c88", "timestamp": "2026-10-26T01:21:55.173375+00:00"}
INFO  [researchbase.commands] {"actor_id": "d2261e6b-0ef4-487d-ab03-d44522f53b19", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.788, "error_code": null, "level": "INFO", "project_id": null, "request_id": "00eeb735-e56a-4349-9f24-a5f86b177dec", "result": "success", "rollback": false, "target_id": "01a175cc-bfe1-7baf-995f-ebc8f2366c88", "timestamp": "2026-10-26T01:21:55.176204+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.176866+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.634, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:55.176892+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.658, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-bfe1-7baf-995f-ebc8f2366c88", "timestamp": "2026-10-26T01:21:55.176910+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.182253+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.258281+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.265039+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.265750+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.268064+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FROZEN_REFERENCE_REQUIRED", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:55.274554+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_dc0e221f3992413380981a160924d083
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_dc0e221f3992413380981a160924d083
.DISPOSABLE_DROPPED: researchbase_pr212_test_dc0e221f3992413380981a160924d083
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.571, "error_code": null, "level": "INFO", "project_id": "20288aeb-b088-4de7-a6aa-2d7e654062b4", "request_id": "168c44dd-2677-4ea2-9fb2-abbd7c9a549b", "result": "success", "rollback": false, "target_id": "20288aeb-b088-4de7-a6aa-2d7e654062b4", "timestamp": "2026-10-26T01:21:56.126199+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.126869+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.636, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.126909+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.671, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.126935+00:00"}
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.797, "error_code": null, "level": "INFO", "project_id": null, "request_id": "168c44dd-2677-4ea2-9fb2-abbd7c9a549b", "result": "success", "rollback": false, "target_id": "01a175cc-c39d-766b-9839-1082199c3be6", "timestamp": "2026-10-26T01:21:56.131773+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.132189+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.403, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.132226+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.434, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c3a0-701f-8dfd-932c725a4ae4", "timestamp": "2026-10-26T01:21:56.132251+00:00"}
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.392, "error_code": null, "level": "INFO", "project_id": null, "request_id": "168c44dd-2677-4ea2-9fb2-abbd7c9a549b", "result": "success", "rollback": false, "target_id": "01a175cc-c3a0-701f-8dfd-932c725a4ae4", "timestamp": "2026-10-26T01:21:56.134670+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.135006+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.332, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.135040+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.357, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c3a0-701f-8dfd-932c725a4ae4", "timestamp": "2026-10-26T01:21:56.135061+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.296, "error_code": null, "level": "INFO", "project_id": "20288aeb-b088-4de7-a6aa-2d7e654062b4", "request_id": "336759a0-6472-4ad0-8a09-3fb03cdd6887", "result": "success", "rollback": false, "target_id": "20288aeb-b088-4de7-a6aa-2d7e654062b4", "timestamp": "2026-10-26T01:21:56.282253+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.282977+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.684, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.283012+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.71, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.283031+00:00"}
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.605, "error_code": null, "level": "INFO", "project_id": null, "request_id": "336759a0-6472-4ad0-8a09-3fb03cdd6887", "result": "success", "rollback": false, "target_id": "01a175cc-c439-7e0e-b5a2-18991022906c", "timestamp": "2026-10-26T01:21:56.288663+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.290099+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.415, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.290129+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.438, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c43d-7957-951d-ce118286f165", "timestamp": "2026-10-26T01:21:56.290147+00:00"}
INFO  [researchbase.commands] {"actor_id": "13e6c54e-433a-4204-9933-76ef3f86764c", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.736, "error_code": null, "level": "INFO", "project_id": null, "request_id": "336759a0-6472-4ad0-8a09-3fb03cdd6887", "result": "success", "rollback": false, "target_id": "01a175cc-c43d-7957-951d-ce118286f165", "timestamp": "2026-10-26T01:21:56.293909+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.294405+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.461, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:56.294432+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.487, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c43d-7957-951d-ce118286f165", "timestamp": "2026-10-26T01:21:56.294451+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.301105+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.333407+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.340109+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.340956+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.343479+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "PROVENANCE_CLOSURE_VIOLATION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:56.351019+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_1ea517d3ac414501aa72796613b0eb5e
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_1ea517d3ac414501aa72796613b0eb5e
.DISPOSABLE_DROPPED: researchbase_pr212_test_1ea517d3ac414501aa72796613b0eb5e
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.923, "error_code": null, "level": "INFO", "project_id": "7998e021-b4b1-43b2-85cc-c917d3c8d1b4", "request_id": "78e1cdf8-52da-4605-b2e2-7df22a505328", "result": "success", "rollback": false, "target_id": "7998e021-b4b1-43b2-85cc-c917d3c8d1b4", "timestamp": "2026-10-26T01:21:57.601725+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.660091+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 58.38, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.660179+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 58.425, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.660215+00:00"}
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.86, "error_code": null, "level": "INFO", "project_id": null, "request_id": "78e1cdf8-52da-4605-b2e2-7df22a505328", "result": "success", "rollback": false, "target_id": "01a175cc-c960-7473-bb07-f0743e9822e0", "timestamp": "2026-10-26T01:21:57.666119+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.666554+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.406, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.666584+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.432, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c99e-779c-822b-ddb82f2110e2", "timestamp": "2026-10-26T01:21:57.666603+00:00"}
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.655, "error_code": null, "level": "INFO", "project_id": null, "request_id": "78e1cdf8-52da-4605-b2e2-7df22a505328", "result": "success", "rollback": false, "target_id": "01a175cc-c99e-779c-822b-ddb82f2110e2", "timestamp": "2026-10-26T01:21:57.669283+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.669753+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.463, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.669792+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.495, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-c99e-779c-822b-ddb82f2110e2", "timestamp": "2026-10-26T01:21:57.669818+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.204, "error_code": null, "level": "INFO", "project_id": "7998e021-b4b1-43b2-85cc-c917d3c8d1b4", "request_id": "7ffd8eb0-edb7-4de4-9ab6-41331b238d65", "result": "success", "rollback": false, "target_id": "7998e021-b4b1-43b2-85cc-c917d3c8d1b4", "timestamp": "2026-10-26T01:21:57.816259+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.816938+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.61, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.816971+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.643, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.816991+00:00"}
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.637, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7ffd8eb0-edb7-4de4-9ab6-41331b238d65", "result": "success", "rollback": false, "target_id": "01a175cc-ca37-74ec-9f24-16a379cb8231", "timestamp": "2026-10-26T01:21:57.821656+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.822076+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.385, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.822103+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.408, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ca3b-7a1a-9d7e-dbf02f3dc0f5", "timestamp": "2026-10-26T01:21:57.822119+00:00"}
INFO  [researchbase.commands] {"actor_id": "206271aa-7c04-4bed-924e-ea11ca6cd720", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.345, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7ffd8eb0-edb7-4de4-9ab6-41331b238d65", "result": "success", "rollback": false, "target_id": "01a175cc-ca3b-7a1a-9d7e-dbf02f3dc0f5", "timestamp": "2026-10-26T01:21:57.824490+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.824886+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.378, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:57.824908+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.397, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ca3b-7a1a-9d7e-dbf02f3dc0f5", "timestamp": "2026-10-26T01:21:57.824922+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.836082+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.839585+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:57.925073+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_ae5ae64a12b34603a0675b10f72b2a1a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_ae5ae64a12b34603a0675b10f72b2a1a
.DISPOSABLE_DROPPED: researchbase_pr212_test_ae5ae64a12b34603a0675b10f72b2a1a
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.365, "error_code": null, "level": "INFO", "project_id": "e01e07a2-6fc1-4f01-a9cf-332fc5c91eaa", "request_id": "4d398ef5-eb57-4003-9ad1-05b68e22359a", "result": "success", "rollback": false, "target_id": "e01e07a2-6fc1-4f01-a9cf-332fc5c91eaa", "timestamp": "2026-10-26T01:21:58.748028+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.748699+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.628, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.748729+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.653, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.748748+00:00"}
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.812, "error_code": null, "level": "INFO", "project_id": null, "request_id": "4d398ef5-eb57-4003-9ad1-05b68e22359a", "result": "success", "rollback": false, "target_id": "01a175cc-cddb-70c4-90e1-e3bfccdeccec", "timestamp": "2026-10-26T01:21:58.754585+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.755068+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.444, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.755096+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.468, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-cdde-7ca2-b5f9-0d25348415e2", "timestamp": "2026-10-26T01:21:58.755113+00:00"}
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.602, "error_code": null, "level": "INFO", "project_id": null, "request_id": "4d398ef5-eb57-4003-9ad1-05b68e22359a", "result": "success", "rollback": false, "target_id": "01a175cc-cdde-7ca2-b5f9-0d25348415e2", "timestamp": "2026-10-26T01:21:58.757741+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.758198+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.435, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.758225+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.457, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-cdde-7ca2-b5f9-0d25348415e2", "timestamp": "2026-10-26T01:21:58.758242+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.981, "error_code": null, "level": "INFO", "project_id": "e01e07a2-6fc1-4f01-a9cf-332fc5c91eaa", "request_id": "aa0e81e8-0f2c-4439-8fdc-27701bd341d9", "result": "success", "rollback": false, "target_id": "e01e07a2-6fc1-4f01-a9cf-332fc5c91eaa", "timestamp": "2026-10-26T01:21:58.903287+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.904047+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.741, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.904121+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.781, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.904152+00:00"}
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.954, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aa0e81e8-0f2c-4439-8fdc-27701bd341d9", "result": "success", "rollback": false, "target_id": "01a175cc-ce76-70b9-b7a6-a2fe8e39cb61", "timestamp": "2026-10-26T01:21:58.909147+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.909579+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.408, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.909612+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.434, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ce7a-7277-8444-a3ff075d6d2f", "timestamp": "2026-10-26T01:21:58.909631+00:00"}
INFO  [researchbase.commands] {"actor_id": "505e24b8-d802-4453-835b-2ada5a88d365", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.905, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aa0e81e8-0f2c-4439-8fdc-27701bd341d9", "result": "success", "rollback": false, "target_id": "01a175cc-ce7a-7277-8444-a3ff075d6d2f", "timestamp": "2026-10-26T01:21:58.915563+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.916124+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.535, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:58.916157+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.561, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ce7a-7277-8444-a3ff075d6d2f", "timestamp": "2026-10-26T01:21:58.916176+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.922807+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.991792+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.992521+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:58.996329+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_9879b72493b94fefabd73dbbf37c042a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_9879b72493b94fefabd73dbbf37c042a
.DISPOSABLE_DROPPED: researchbase_pr212_test_9879b72493b94fefabd73dbbf37c042a
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.465, "error_code": null, "level": "INFO", "project_id": "3215ea67-2201-48ab-a19a-26a717daebf9", "request_id": "f662df13-d0e9-4ece-8596-ae5c2ce23d5c", "result": "success", "rollback": false, "target_id": "3215ea67-2201-48ab-a19a-26a717daebf9", "timestamp": "2026-10-26T01:21:59.793082+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:59.793710+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.59, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.793749+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.618, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.793769+00:00"}
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.166, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f662df13-d0e9-4ece-8596-ae5c2ce23d5c", "result": "success", "rollback": false, "target_id": "01a175cc-d1f0-7ff7-aadc-1f662b197d48", "timestamp": "2026-10-26T01:21:59.798962+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:59.799526+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.54, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.799563+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.576, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d1f3-7585-8505-e331d0375479", "timestamp": "2026-10-26T01:21:59.799592+00:00"}
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.315, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f662df13-d0e9-4ece-8596-ae5c2ce23d5c", "result": "success", "rollback": false, "target_id": "01a175cc-d1f3-7585-8505-e331d0375479", "timestamp": "2026-10-26T01:21:59.802936+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:59.803384+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.422, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.803413+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.446, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d1f3-7585-8505-e331d0375479", "timestamp": "2026-10-26T01:21:59.803431+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.062, "error_code": null, "level": "INFO", "project_id": "3215ea67-2201-48ab-a19a-26a717daebf9", "request_id": "b3e9db39-b878-4670-a2b8-1d70665c0577", "result": "success", "rollback": false, "target_id": "3215ea67-2201-48ab-a19a-26a717daebf9", "timestamp": "2026-10-26T01:21:59.998775+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:21:59.999594+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.752, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.999639+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.785, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:21:59.999664+00:00"}
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.516, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b3e9db39-b878-4670-a2b8-1d70665c0577", "result": "success", "rollback": false, "target_id": "01a175cc-d2bd-7a48-af2f-ff52a80ef9f6", "timestamp": "2026-10-26T01:22:00.006216+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.006903+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.635, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.006945+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.673, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d2c2-7534-8987-104c3738dd93", "timestamp": "2026-10-26T01:22:00.006970+00:00"}
INFO  [researchbase.commands] {"actor_id": "9d3d50a8-42ab-42fe-b0aa-38f5b1b5ff75", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.065, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b3e9db39-b878-4670-a2b8-1d70665c0577", "result": "success", "rollback": false, "target_id": "01a175cc-d2c2-7534-8987-104c3738dd93", "timestamp": "2026-10-26T01:22:00.010064+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.010712+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.612, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.010738+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.635, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d2c2-7534-8987-104c3738dd93", "timestamp": "2026-10-26T01:22:00.010755+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.016363+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.102157+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.110416+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.111490+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.112414+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.121155+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.123592+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.124484+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.127529+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.128264+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.129021+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.129791+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_5199d24683e74734b47b45f7ee3deefb
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_5199d24683e74734b47b45f7ee3deefb
.DISPOSABLE_DROPPED: researchbase_pr212_test_5199d24683e74734b47b45f7ee3deefb
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.398, "error_code": null, "level": "INFO", "project_id": "0199ca5b-c7e2-4c5e-9f52-276095d66410", "request_id": "3cd12465-4957-4461-9004-bbd0ba3ac10f", "result": "success", "rollback": false, "target_id": "0199ca5b-c7e2-4c5e-9f52-276095d66410", "timestamp": "2026-10-26T01:22:00.980519+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.981426+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.848, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.981472+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.886, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.981498+00:00"}
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.136, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3cd12465-4957-4461-9004-bbd0ba3ac10f", "result": "success", "rollback": false, "target_id": "01a175cc-d693-798b-9470-b40a33d5a913", "timestamp": "2026-10-26T01:22:00.987671+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.988360+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.662, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.988408+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.704, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d697-766d-988c-dbb942eed494", "timestamp": "2026-10-26T01:22:00.988441+00:00"}
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.361, "error_code": null, "level": "INFO", "project_id": null, "request_id": "3cd12465-4957-4461-9004-bbd0ba3ac10f", "result": "success", "rollback": false, "target_id": "01a175cc-d697-766d-988c-dbb942eed494", "timestamp": "2026-10-26T01:22:00.991841+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:00.992443+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.548, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:00.992474+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.577, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d697-766d-988c-dbb942eed494", "timestamp": "2026-10-26T01:22:00.992491+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.455, "error_code": null, "level": "INFO", "project_id": "0199ca5b-c7e2-4c5e-9f52-276095d66410", "request_id": "c4829935-2f03-41d8-ab6b-719dd27a0523", "result": "success", "rollback": false, "target_id": "0199ca5b-c7e2-4c5e-9f52-276095d66410", "timestamp": "2026-10-26T01:22:01.154149+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.154926+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.72, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:01.154960+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.746, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:01.154979+00:00"}
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.372, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c4829935-2f03-41d8-ab6b-719dd27a0523", "result": "success", "rollback": false, "target_id": "01a175cc-d741-7c08-8e31-30a1ecc235ee", "timestamp": "2026-10-26T01:22:01.161382+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.161913+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.485, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:01.161941+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.509, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d746-7889-944a-7d2bff128470", "timestamp": "2026-10-26T01:22:01.161958+00:00"}
INFO  [researchbase.commands] {"actor_id": "3af20336-310f-4313-b54a-cc3d9c208430", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.164, "error_code": null, "level": "INFO", "project_id": null, "request_id": "c4829935-2f03-41d8-ab6b-719dd27a0523", "result": "success", "rollback": false, "target_id": "01a175cc-d746-7889-944a-7d2bff128470", "timestamp": "2026-10-26T01:22:01.165148+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.165595+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.419, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:01.165620+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.441, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-d746-7889-944a-7d2bff128470", "timestamp": "2026-10-26T01:22:01.165635+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.171341+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.297201+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.305650+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.306571+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.307370+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.314904+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.316837+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.317571+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.319897+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.320598+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.321650+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:01.322133+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_c9ddb62e1b3044db8cf739d6bb325679
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_c9ddb62e1b3044db8cf739d6bb325679
.DISPOSABLE_DROPPED: researchbase_pr212_test_c9ddb62e1b3044db8cf739d6bb325679
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.978, "error_code": null, "level": "INFO", "project_id": "daaf7287-140c-4cba-a585-693cf5a3f174", "request_id": "6658f545-eef9-4439-ba74-611b8b03fad9", "result": "success", "rollback": false, "target_id": "daaf7287-140c-4cba-a585-693cf5a3f174", "timestamp": "2026-10-26T01:22:02.262566+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.263289+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.668, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.263320+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.697, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.263339+00:00"}
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.786, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6658f545-eef9-4439-ba74-611b8b03fad9", "result": "success", "rollback": false, "target_id": "01a175cc-db95-733d-b197-664b6097ac05", "timestamp": "2026-10-26T01:22:02.269150+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.269728+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.549, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.269753+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.573, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-db99-72f0-a076-8bb8ec5defae", "timestamp": "2026-10-26T01:22:02.269771+00:00"}
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.823, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6658f545-eef9-4439-ba74-611b8b03fad9", "result": "success", "rollback": false, "target_id": "01a175cc-db99-72f0-a076-8bb8ec5defae", "timestamp": "2026-10-26T01:22:02.272619+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.272988+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.348, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.273016+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.373, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-db99-72f0-a076-8bb8ec5defae", "timestamp": "2026-10-26T01:22:02.273035+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.803, "error_code": null, "level": "INFO", "project_id": "daaf7287-140c-4cba-a585-693cf5a3f174", "request_id": "6f071f71-741e-4d23-ba1d-7a3c811e6b61", "result": "success", "rollback": false, "target_id": "daaf7287-140c-4cba-a585-693cf5a3f174", "timestamp": "2026-10-26T01:22:02.467514+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.468153+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.605, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.468184+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.645, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.468220+00:00"}
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.078, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6f071f71-741e-4d23-ba1d-7a3c811e6b61", "result": "success", "rollback": false, "target_id": "01a175cc-dc62-789f-8a94-a90840621dd9", "timestamp": "2026-10-26T01:22:02.473351+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.473875+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.492, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.473903+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.516, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-dc66-7264-a27d-d43b9c567d9e", "timestamp": "2026-10-26T01:22:02.473920+00:00"}
INFO  [researchbase.commands] {"actor_id": "5455e09a-e9a9-48df-a2b5-0c7d6f89e797", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.421, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6f071f71-741e-4d23-ba1d-7a3c811e6b61", "result": "success", "rollback": false, "target_id": "01a175cc-dc66-7264-a27d-d43b9c567d9e", "timestamp": "2026-10-26T01:22:02.476367+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.476819+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.422, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:02.476850+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.448, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-dc66-7264-a27d-d43b9c567d9e", "timestamp": "2026-10-26T01:22:02.476869+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.482183+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.604610+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.612926+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.613697+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.614542+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.620856+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.623012+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.623908+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.625763+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.626358+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.627083+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:02.627608+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_5d743d42f01642bbac8bc2a683622f6f
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_5d743d42f01642bbac8bc2a683622f6f
.DISPOSABLE_DROPPED: researchbase_pr212_test_5d743d42f01642bbac8bc2a683622f6f
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.366, "error_code": null, "level": "INFO", "project_id": "4658ed5d-5d57-417b-859f-dc9c00f4333a", "request_id": "dde25f0d-1dc8-4779-ad6d-9102667992d7", "result": "success", "rollback": false, "target_id": "4658ed5d-5d57-417b-859f-dc9c00f4333a", "timestamp": "2026-10-26T01:22:03.526044+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.526693+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.599, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.526722+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.624, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.526740+00:00"}
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.147, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dde25f0d-1dc8-4779-ad6d-9102667992d7", "result": "success", "rollback": false, "target_id": "01a175cc-e085-7fa3-8bc9-415313b74d70", "timestamp": "2026-10-26T01:22:03.531915+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.532498+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.555, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.532544+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.589, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e088-76d9-907e-409262555feb", "timestamp": "2026-10-26T01:22:03.532569+00:00"}
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.796, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dde25f0d-1dc8-4779-ad6d-9102667992d7", "result": "success", "rollback": false, "target_id": "01a175cc-e088-76d9-907e-409262555feb", "timestamp": "2026-10-26T01:22:03.535397+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.535817+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.397, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.535842+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.419, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e088-76d9-907e-409262555feb", "timestamp": "2026-10-26T01:22:03.535858+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.026, "error_code": null, "level": "INFO", "project_id": "4658ed5d-5d57-417b-859f-dc9c00f4333a", "request_id": "ada7015d-d574-48e5-8f94-ee65b5ef5bbf", "result": "success", "rollback": false, "target_id": "4658ed5d-5d57-417b-859f-dc9c00f4333a", "timestamp": "2026-10-26T01:22:03.678896+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.679842+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.917, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.679887+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.957, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.679920+00:00"}
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.123, "error_code": null, "level": "INFO", "project_id": null, "request_id": "ada7015d-d574-48e5-8f94-ee65b5ef5bbf", "result": "success", "rollback": false, "target_id": "01a175cc-e11e-7964-8eff-9f198cac0eab", "timestamp": "2026-10-26T01:22:03.686078+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.686791+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.674, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.686825+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.7, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e122-7bd7-a863-f1edd46fb311", "timestamp": "2026-10-26T01:22:03.686843+00:00"}
INFO  [researchbase.commands] {"actor_id": "05c0a074-2d8e-4878-a897-f8047970edf5", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.199, "error_code": null, "level": "INFO", "project_id": null, "request_id": "ada7015d-d574-48e5-8f94-ee65b5ef5bbf", "result": "success", "rollback": false, "target_id": "01a175cc-e122-7bd7-a863-f1edd46fb311", "timestamp": "2026-10-26T01:22:03.690069+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.690643+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.539, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:03.690678+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.569, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e122-7bd7-a863-f1edd46fb311", "timestamp": "2026-10-26T01:22:03.690700+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.697330+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.762330+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.771121+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.772026+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.772930+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.781419+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.784527+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.785378+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.787947+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.788560+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.789235+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:03.789779+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_9cdd9b9a11044ed69b93d097b04bedab
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_9cdd9b9a11044ed69b93d097b04bedab
.DISPOSABLE_DROPPED: researchbase_pr212_test_9cdd9b9a11044ed69b93d097b04bedab
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.939, "error_code": null, "level": "INFO", "project_id": "29e14a1f-b783-42c7-99df-c5e6702d3c24", "request_id": "b4b83117-1438-4a5b-a37e-120a67bf0fdf", "result": "success", "rollback": false, "target_id": "29e14a1f-b783-42c7-99df-c5e6702d3c24", "timestamp": "2026-10-26T01:22:04.517176+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.517720+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.502, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.517748+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.527, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.517766+00:00"}
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.599, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b4b83117-1438-4a5b-a37e-120a67bf0fdf", "result": "success", "rollback": false, "target_id": "01a175cc-e464-731d-b363-ec3e4dbc6af7", "timestamp": "2026-10-26T01:22:04.522389+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.522776+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.372, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.522809+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.396, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e467-7dc1-ac5c-b2ef60d4c6df", "timestamp": "2026-10-26T01:22:04.522827+00:00"}
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.393, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b4b83117-1438-4a5b-a37e-120a67bf0fdf", "result": "success", "rollback": false, "target_id": "01a175cc-e467-7dc1-ac5c-b2ef60d4c6df", "timestamp": "2026-10-26T01:22:04.525246+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.525590+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.326, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.525613+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.346, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e467-7dc1-ac5c-b2ef60d4c6df", "timestamp": "2026-10-26T01:22:04.525629+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.896, "error_code": null, "level": "INFO", "project_id": "29e14a1f-b783-42c7-99df-c5e6702d3c24", "request_id": "23d99548-ba52-4d67-86db-5928fca4a577", "result": "success", "rollback": false, "target_id": "29e14a1f-b783-42c7-99df-c5e6702d3c24", "timestamp": "2026-10-26T01:22:04.658067+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.658692+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.582, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.658723+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.606, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.658741+00:00"}
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.343, "error_code": null, "level": "INFO", "project_id": null, "request_id": "23d99548-ba52-4d67-86db-5928fca4a577", "result": "success", "rollback": false, "target_id": "01a175cc-e4f1-7806-9a3f-b29e1765d10f", "timestamp": "2026-10-26T01:22:04.664108+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.717490+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 53.35, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.717543+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 53.38, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e4f4-7cd7-a494-4525a79fc2b5", "timestamp": "2026-10-26T01:22:04.717564+00:00"}
INFO  [researchbase.commands] {"actor_id": "0a359814-2c65-4e1b-a226-1a4cf418a0a0", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.431, "error_code": null, "level": "INFO", "project_id": null, "request_id": "23d99548-ba52-4d67-86db-5928fca4a577", "result": "success", "rollback": false, "target_id": "01a175cc-e4f4-7cd7-a494-4525a79fc2b5", "timestamp": "2026-10-26T01:22:04.721026+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.721441+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.384, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:04.721468+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e4f4-7cd7-a494-4525a79fc2b5", "timestamp": "2026-10-26T01:22:04.721490+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.726314+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.785618+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.793510+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.794267+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.794993+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.801555+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.803952+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.804677+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.806610+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.807154+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.807837+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:04.808357+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_1a22efde54254aad8e93464e93136e06
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_1a22efde54254aad8e93464e93136e06
.DISPOSABLE_DROPPED: researchbase_pr212_test_1a22efde54254aad8e93464e93136e06
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.986, "error_code": null, "level": "INFO", "project_id": "4cabc05d-be9d-4950-8802-2096859375f0", "request_id": "ed473ed0-3568-4964-9b8e-06ea01df2c72", "result": "success", "rollback": false, "target_id": "4cabc05d-be9d-4950-8802-2096859375f0", "timestamp": "2026-10-26T01:22:05.538667+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.539212+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.499, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.539240+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.525, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.539258+00:00"}
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.116, "error_code": null, "level": "INFO", "project_id": null, "request_id": "ed473ed0-3568-4964-9b8e-06ea01df2c72", "result": "success", "rollback": false, "target_id": "01a175cc-e861-7dcc-ad56-15bb3488a4bc", "timestamp": "2026-10-26T01:22:05.544396+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.544815+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.418, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.544860+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e865-7276-af08-475968d933f3", "timestamp": "2026-10-26T01:22:05.544886+00:00"}
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.608, "error_code": null, "level": "INFO", "project_id": null, "request_id": "ed473ed0-3568-4964-9b8e-06ea01df2c72", "result": "success", "rollback": false, "target_id": "01a175cc-e865-7276-af08-475968d933f3", "timestamp": "2026-10-26T01:22:05.547530+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.547915+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.378, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.547949+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.414, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e865-7276-af08-475968d933f3", "timestamp": "2026-10-26T01:22:05.547980+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.781, "error_code": null, "level": "INFO", "project_id": "4cabc05d-be9d-4950-8802-2096859375f0", "request_id": "f10e82c9-7d0a-40ef-a359-ebbdc6bcad93", "result": "success", "rollback": false, "target_id": "4cabc05d-be9d-4950-8802-2096859375f0", "timestamp": "2026-10-26T01:22:05.680601+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.681161+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.532, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.681200+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.555, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.681217+00:00"}
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.972, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f10e82c9-7d0a-40ef-a359-ebbdc6bcad93", "result": "success", "rollback": false, "target_id": "01a175cc-e8ef-7885-88ae-193e90f64c74", "timestamp": "2026-10-26T01:22:05.686212+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.686644+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.391, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.686670+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e8f3-7902-98df-49abe46f44df", "timestamp": "2026-10-26T01:22:05.686686+00:00"}
INFO  [researchbase.commands] {"actor_id": "900eea6c-a4d1-4d2c-beea-2ba22adb50a0", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.41, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f10e82c9-7d0a-40ef-a359-ebbdc6bcad93", "result": "success", "rollback": false, "target_id": "01a175cc-e8f3-7902-98df-49abe46f44df", "timestamp": "2026-10-26T01:22:05.689122+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.689528+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.406, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:05.689567+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.437, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-e8f3-7902-98df-49abe46f44df", "timestamp": "2026-10-26T01:22:05.689593+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.695263+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.741848+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.749495+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.750268+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.751084+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.757233+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.759226+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.760056+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.762202+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.762786+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.763379+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:05.763924+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_cb7f84843cee4f4084aa4f69340de76b
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_cb7f84843cee4f4084aa4f69340de76b
.DISPOSABLE_DROPPED: researchbase_pr212_test_cb7f84843cee4f4084aa4f69340de76b
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.464, "error_code": null, "level": "INFO", "project_id": "f64e9c22-f6eb-4eab-ba35-0906d288574f", "request_id": "b630a383-8bd4-4024-8130-ed30089f0d4f", "result": "success", "rollback": false, "target_id": "f64e9c22-f6eb-4eab-ba35-0906d288574f", "timestamp": "2026-10-26T01:22:06.426455+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.427141+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.634, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.427182+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.685, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.427222+00:00"}
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.593, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b630a383-8bd4-4024-8130-ed30089f0d4f", "result": "success", "rollback": false, "target_id": "01a175cc-ebd9-7608-8967-5e8f6e9e0608", "timestamp": "2026-10-26T01:22:06.431856+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.432246+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.365, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.432273+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.39, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ebdd-7cb6-b28a-feadf6983468", "timestamp": "2026-10-26T01:22:06.432292+00:00"}
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.656, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b630a383-8bd4-4024-8130-ed30089f0d4f", "result": "success", "rollback": false, "target_id": "01a175cc-ebdd-7cb6-b28a-feadf6983468", "timestamp": "2026-10-26T01:22:06.434980+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.435431+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.42, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.435455+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.444, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ebdd-7cb6-b28a-feadf6983468", "timestamp": "2026-10-26T01:22:06.435472+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.905, "error_code": null, "level": "INFO", "project_id": "f64e9c22-f6eb-4eab-ba35-0906d288574f", "request_id": "b8d6837a-313b-400a-9823-bef1bb73d54a", "result": "success", "rollback": false, "target_id": "f64e9c22-f6eb-4eab-ba35-0906d288574f", "timestamp": "2026-10-26T01:22:06.569614+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.570251+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.593, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.570277+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.614, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.570291+00:00"}
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.395, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b8d6837a-313b-400a-9823-bef1bb73d54a", "result": "success", "rollback": false, "target_id": "01a175cc-ec68-7895-9f91-351d0664fc63", "timestamp": "2026-10-26T01:22:06.575710+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.576221+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.576248+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.499, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ec6c-7a6b-81d4-d8ab31f0646f", "timestamp": "2026-10-26T01:22:06.576265+00:00"}
INFO  [researchbase.commands] {"actor_id": "80372418-eb6a-4594-97f6-ddd419691bf4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.339, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b8d6837a-313b-400a-9823-bef1bb73d54a", "result": "success", "rollback": false, "target_id": "01a175cc-ec6c-7a6b-81d4-d8ab31f0646f", "timestamp": "2026-10-26T01:22:06.578648+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.578982+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.345, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:06.579030+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.376, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ec6c-7a6b-81d4-d8ab31f0646f", "timestamp": "2026-10-26T01:22:06.579055+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.584429+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.618958+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:06.619867+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_2fe8a1e520314521a2be067a92964c22
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_2fe8a1e520314521a2be067a92964c22
.DISPOSABLE_DROPPED: researchbase_pr212_test_2fe8a1e520314521a2be067a92964c22
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.132, "error_code": null, "level": "INFO", "project_id": "ec16eca9-bf41-4fe7-bcbb-394fef23efdf", "request_id": "663d1579-f16f-4792-9489-a8afc6eadb17", "result": "success", "rollback": false, "target_id": "ec16eca9-bf41-4fe7-bcbb-394fef23efdf", "timestamp": "2026-10-26T01:22:07.354562+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.355285+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.696, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.355339+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.73, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.355365+00:00"}
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.642, "error_code": null, "level": "INFO", "project_id": null, "request_id": "663d1579-f16f-4792-9489-a8afc6eadb17", "result": "success", "rollback": false, "target_id": "01a175cc-ef79-782c-bb94-81e7fba55211", "timestamp": "2026-10-26T01:22:07.360043+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.360520+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.455, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.360554+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.481, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ef7d-7e1f-8c36-3141be4b4b92", "timestamp": "2026-10-26T01:22:07.360573+00:00"}
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.639, "error_code": null, "level": "INFO", "project_id": null, "request_id": "663d1579-f16f-4792-9489-a8afc6eadb17", "result": "success", "rollback": false, "target_id": "01a175cc-ef7d-7e1f-8c36-3141be4b4b92", "timestamp": "2026-10-26T01:22:07.363241+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.363617+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.363643+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.377, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-ef7d-7e1f-8c36-3141be4b4b92", "timestamp": "2026-10-26T01:22:07.363661+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.707, "error_code": null, "level": "INFO", "project_id": "ec16eca9-bf41-4fe7-bcbb-394fef23efdf", "request_id": "11460e32-6755-4d35-9250-4b80bedb4cd7", "result": "success", "rollback": false, "target_id": "ec16eca9-bf41-4fe7-bcbb-394fef23efdf", "timestamp": "2026-10-26T01:22:07.498963+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.499591+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.585, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.499618+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.609, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.499635+00:00"}
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.034, "error_code": null, "level": "INFO", "project_id": null, "request_id": "11460e32-6755-4d35-9250-4b80bedb4cd7", "result": "success", "rollback": false, "target_id": "01a175cc-f00a-7db1-955b-2059638a454b", "timestamp": "2026-10-26T01:22:07.503695+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.504174+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.459, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.504203+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.49, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-f00d-71fd-b587-030ca75a3d8f", "timestamp": "2026-10-26T01:22:07.504228+00:00"}
INFO  [researchbase.commands] {"actor_id": "1aee649b-b2b5-4040-9fee-6626b12775c1", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.076, "error_code": null, "level": "INFO", "project_id": null, "request_id": "11460e32-6755-4d35-9250-4b80bedb4cd7", "result": "success", "rollback": false, "target_id": "01a175cc-f00d-71fd-b587-030ca75a3d8f", "timestamp": "2026-10-26T01:22:07.507328+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.507912+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.562, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T01:22:07.507937+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.583, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a175cc-f00d-71fd-b587-030ca75a3d8f", "timestamp": "2026-10-26T01:22:07.507952+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.514135+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.559328+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.590627+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T01:22:07.591749+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_0ebba7328adf4c398d9901623b5b774f
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_0ebba7328adf4c398d9901623b5b774f
.DISPOSABLE_DROPPED: researchbase_pr212_test_0ebba7328adf4c398d9901623b5b774f


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 24 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 23 passed, 47 warnings in 29.93s =======================
```

Exit code: **0**.

### S7-REG3

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_02_s1_*.py tests/integration/phase3/test_pr3_03_*.py tests/integration/phase3/test_pr3_04_*.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 561 items

tests/integration/phase3/test_pr3_01_application.py .......              [  1%]
tests/integration/phase3/test_pr3_01_concurrency.py ................     [  4%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [  4%]
tests/integration/phase3/test_pr3_01_replay.py ...............           [  7%]
tests/integration/phase3/test_pr3_01_schema.py ......................... [ 11%]
........................................................................ [ 24%]
..................................                                       [ 30%]
tests/integration/phase3/test_pr3_02_s1_application.py ..............    [ 33%]
tests/integration/phase3/test_pr3_02_s1_b02_agent.py .                   [ 33%]
tests/integration/phase3/test_pr3_02_s1_concurrency.py .......           [ 34%]
tests/integration/phase3/test_pr3_02_s1_identity.py ...................  [ 37%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [ 38%]
tests/integration/phase3/test_pr3_02_s1_replay.py ..........             [ 40%]
tests/integration/phase3/test_pr3_02_s1_schema.py .....................  [ 44%]
tests/integration/phase3/test_pr3_03_application.py .................... [ 47%]
...........................................                              [ 55%]
tests/integration/phase3/test_pr3_03_concurrency.py .................... [ 58%]
...                                                                      [ 59%]
tests/integration/phase3/test_pr3_03_guards.py ......................... [ 63%]
.....................                                                    [ 67%]
tests/integration/phase3/test_pr3_03_input_versions.py ....              [ 68%]
tests/integration/phase3/test_pr3_03_migration.py ...                    [ 68%]
tests/integration/phase3/test_pr3_03_replay.py ......................... [ 73%]
................................................                         [ 81%]
tests/integration/phase3/test_pr3_03_schema.py ......................... [ 86%]
.....                                                                    [ 87%]
tests/integration/phase3/test_pr3_04_accounting.py ...........           [ 89%]
tests/integration/phase3/test_pr3_04_application.py .................... [ 92%]
..                                                                       [ 93%]
tests/integration/phase3/test_pr3_04_concurrency.py .......              [ 94%]
tests/integration/phase3/test_pr3_04_fake_consumer.py ..                 [ 94%]
tests/integration/phase3/test_pr3_04_guards.py ..................        [ 97%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 98%]
tests/integration/phase3/test_pr3_04_queries.py ..                       [ 98%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 99%]
tests/integration/phase3/test_pr3_04_schema.py ....                      [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_01_application.py: 2 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_b02_agent.py: 1 warning
tests/integration/phase3/test_pr3_02_s1_concurrency.py: 7 warnings
tests/integration/phase3/test_pr3_02_s1_identity.py: 19 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
tests/integration/phase3/test_pr3_02_s1_schema.py: 21 warnings
tests/integration/phase3/test_pr3_03_application.py: 126 warnings
tests/integration/phase3/test_pr3_03_concurrency.py: 46 warnings
tests/integration/phase3/test_pr3_03_guards.py: 92 warnings
tests/integration/phase3/test_pr3_03_migration.py: 8 warnings
tests/integration/phase3/test_pr3_03_replay.py: 146 warnings
tests/integration/phase3/test_pr3_03_schema.py: 28 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 561 passed, 548 warnings in 509.18s (0:08:29) =================
```

Exit code: **0**.

### S7-REG2

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 155 items

tests/integration/phase2/test_b02_identity_boundary.py ........          [  5%]
tests/integration/phase2/test_b02_strategy_admission.py .............    [ 13%]
tests/integration/phase2/test_b02_strategy_capture.py .........          [ 19%]
tests/integration/phase2/test_b02_strategy_concurrency.py .............. [ 28%]
.................                                                        [ 39%]
tests/integration/phase2/test_b02_strategy_replay.py ................    [ 49%]
tests/integration/phase2/test_b02_strategy_schema.py ................... [ 61%]
......                                                                   [ 65%]
tests/integration/phase2/test_b03_discussion_hypothesis.py ............. [ 74%]
...................                                                      [ 86%]
tests/integration/phase2/test_b03_discussion_hypothesis_guards.py ...... [ 90%]
...............                                                          [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_b02_identity_boundary.py: 8 warnings
tests/integration/phase2/test_b02_strategy_admission.py: 26 warnings
tests/integration/phase2/test_b02_strategy_capture.py: 18 warnings
tests/integration/phase2/test_b02_strategy_concurrency.py: 62 warnings
tests/integration/phase2/test_b02_strategy_replay.py: 31 warnings
tests/integration/phase2/test_b02_strategy_schema.py: 53 warnings
tests/integration/phase2/test_b03_discussion_hypothesis.py: 98 warnings
tests/integration/phase2/test_b03_discussion_hypothesis_guards.py: 64 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 155 passed, 360 warnings in 170.95s (0:02:50) =================
```

Exit code: **0**.

### S7-PREVIEW

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_promotion_validation.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 2 items

tests/integration/phase3/test_pr3_05_promotion_validation.py ..          [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_05_promotion_validation.py::test_candidate_basis_revision_gates_and_missing_s2[RESEARCH_QUESTION_VERSION]
tests/integration/phase3/test_pr3_05_promotion_validation.py::test_candidate_basis_revision_gates_and_missing_s2[RESEARCH_QUESTION_VERSION]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 2 passed, 2 warnings in 1.78s =========================
```

Exit code: **0**.

### H-U

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/test_task12_migration_history.py tests/unit/test_batch_c_migration_history.py tests/unit/test_ci_migration_head.py tests/unit/phase2/test_pr2_04_static_acceptance.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py
```

```text
..................                                                       [100%]
=============================== warnings summary ===============================
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
18 passed, 5 warnings in 13.70s
```

Exit code: **0**.

### PG-R

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase2/test_pr2_03_review_guards.py::test_remediation_child_upgrade_empty_downgrade_and_unique_head tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta tests/integration/phase2/test_pr2_04_migration_coverage.py::test_historical_migration_bytes_match_frozen_accepted_tree tests/integration/phase2/test_pr2_15_decision_schema.py::test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables tests/integration/phase2/test_pr2_17_authorship_schema.py::test_install_upgrade_exact_catalog_and_one_head tests/integration/phase2/test_revision_action.py::test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog tests/integration/phase3/test_pr3_00_bootstrap.py::test_single_head_and_exact_parent tests/integration/phase3/test_pr3_01_migration.py::test_clean_and_populated_upgrade_and_downgrade_refusal tests/integration/phase3/test_pr3_02_s1_migration.py::test_empty_upgrade_and_refusal tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal tests/integration/phase3/test_pr3_04_migration.py::test_forward_upgrade_and_refusal tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_replay.py tests/integration/phase3/test_pr3_05_promotion_validation.py
```

```text
.............................................                            [100%]
=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 5 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 3 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 9 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 4 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 12 warnings
tests/integration/phase2/test_revision_action.py: 6 warnings
tests/integration/phase3/test_pr3_00_bootstrap.py: 1 warning
tests/integration/phase3/test_pr3_01_migration.py: 10 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 4 warnings
tests/integration/phase3/test_pr3_03_migration.py: 3 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase2/test_pr2_20_migrations.py: 6 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
tests/integration/phase3/test_pr3_05_promotion_validation.py: 2 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
45 passed, 98 warnings in 47.09s
```

Exit code: **0**.

### PG-N

```sh
uv run python - <<'PY'
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from sqlalchemy import create_engine,text
with disposable_database("researchbase_pr212_test_") as url:
    upgrade(url)
    engine=create_engine(url)
    with engine.connect() as conn:
        for row in conn.execute(text("SELECT c.relname,k.conname,k.contype FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relname IN ('agent_execution_instances','agent_execution_events') ORDER BY 1,2")):
            print(tuple(row))
    engine.dispose()
PY
```

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_538330025319403b81e07a70662e251b
('agent_execution_events', 'agent_execution_events_actor_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_execution_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_new_status_not_null', 'n')
('agent_execution_events', 'agent_execution_events_occurred_at_not_null', 'n')
('agent_execution_events', 'agent_execution_events_reason_not_null', 'n')
('agent_execution_events', 'agent_execution_events_receipt_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_sequence_not_null', 'n')
('agent_execution_events', 'pr302s2_event_actor_fk', 'f')
('agent_execution_events', 'pr302s2_event_execution_fk', 'f')
('agent_execution_events', 'pr302s2_event_execution_uq', 'u')
('agent_execution_events', 'pr302s2_event_id_ck', 'c')
('agent_execution_events', 'pr302s2_event_initial_ck', 'c')
('agent_execution_events', 'pr302s2_event_pk', 'p')
('agent_execution_events', 'pr302s2_event_reason_ck', 'c')
('agent_execution_events', 'pr302s2_event_receipt_fk', 'f')
('agent_execution_events', 'pr302s2_event_receipt_uq', 'u')
('agent_execution_events', 'pr302s2_event_time_ck', 'c')
('agent_execution_instances', 'agent_execution_instances_actor_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_agent_version_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_created_at_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_artifact_version_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_content_hash_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_hash_scheme_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_input_ref_hash_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_input_ref_hash_scheme_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_project_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_research_task_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_revision_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_status_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_task_revision_at_creation_not_null', 'n')
('agent_execution_instances', 'pr302s2_exec_actor_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_harness_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_hashes_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_id_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_pk', 'p')
('agent_execution_instances', 'pr302s2_exec_project_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_revision_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_schemes_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_status_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_step_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_task_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_task_revision_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_time_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_version_fk', 'f')
DISPOSABLE_DROPPED: researchbase_pr212_test_538330025319403b81e07a70662e251b
```

Exit code: **0**.

### AUDIT

```sh
uv run python tmp/b3_scope_audit.py
```

```text
Protected bytes unchanged: 83 accepted migrations; dependencies, freeze, public errors, closed task gate, gateway, safety and producer-preview paths.
Exact intent delta: 2 tables; 2 nullable receipt links; 9 allowed functions; no deferred identifiers.
Untracked deliverables checked for trailing whitespace and final newline: 0 files.
Migration SHA-256: 142c7a9061785a971d7043667041cf5368be24e38069c59900640d13c2259e52
```

Exit code: **0**.

### FOCUS

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/phase3/test_agent_execution_repository.py tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards tests/integration/phase3/test_pr3_02_s2_intent_replay.py
```

```text
...................................                                      [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 26 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 24 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
35 passed, 50 warnings in 24.13s
```

Exit code: **0**.

## Mutation results: removed guard and restored control

All ten mutations ran against disposable repository copies under `tmp/`, with fresh disposable PostgreSQL databases where needed. Only one mutation is applied per copy. The original checkout's source/migration bytes are asserted unchanged; the copied file is restored in `finally` and the directory removed. `--show-capture=no` suppresses captured setup logs at pytest's output layer; the raw emitted output below is unedited. All restored controls use the identical command and copied test source.

The first harness attempt lacked the acceptance-matrix directory and produced pytest INTERNALERROR/exit 3 for both L2 runs; a second setup attempt named a nonexistent config directory. These setup failures are not mutation witnesses. The corrected harness copies the required execution/docs resources. All credited runs below were rerun after that correction. An earlier successful mutation batch with captured setup logs was replaced by the final shorter-output batch; no older batch receives separate credit.

| Mutation | Guard removed | Removed result (exit 1) | Restored result (exit 0) |
| --- | --- | --- | --- |
| M-L2 | `src/researchbase/persistence/agent_execution_repository.py` | 1 failed in 0.65s | 1 passed in 0.63s |
| M-L3 | `src/researchbase/persistence/uow.py` | 3 failed in 0.90s | 3 passed in 0.82s |
| M-DRIFT | `migrations/versions/0081_agent_execution_intents.py` | 2 failed, 4 warnings in 2.79s | 2 passed, 4 warnings in 2.39s |
| M-REVOKE-PUBLIC | `migrations/versions/0081_agent_execution_intents.py` | 8 failed, 8 deselected, 2 warnings in 0.78s | 8 passed, 8 deselected, 2 warnings in 0.78s |
| M-REVOKE-ROLE | `migrations/versions/0081_agent_execution_intents.py` | 8 failed, 8 deselected, 2 warnings in 0.79s | 8 passed, 8 deselected, 2 warnings in 0.80s |
| M-SHARE | `migrations/versions/0081_agent_execution_intents.py` | 1 failed, 2 warnings in 0.92s | 1 passed, 2 warnings in 0.95s |
| M-CAS | `migrations/versions/0081_agent_execution_intents.py` | 1 failed, 2 warnings in 1.37s | 1 passed, 2 warnings in 1.40s |
| M-ISOLATION | `migrations/versions/0081_agent_execution_intents.py` | 1 failed, 2 warnings in 1.36s | 1 passed, 2 warnings in 1.28s |
| M-REPLAY-PREFLIGHT | `src/researchbase/agent_runtime/application/agent_executions.py` | 2 failed, 4 warnings in 3.40s | 2 passed, 4 warnings in 2.74s |
| M-REPLAY-WRITE | `src/researchbase/agent_runtime/application/agent_executions.py` | 1 failed, 2 warnings in 1.52s | 1 passed, 2 warnings in 1.33s |

### M-L2

Copy-only edit in `src/researchbase/persistence/agent_execution_repository.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
        self._session.execute(text(INTENT_SHARE_SQL))
        after_wait()
```

After:

```text
        self._session.execute(text(INTENT_SHARE_SQL))
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg/tests/unit/phase3/test_agent_execution_repository.py:235: AssertionError: [('wait', 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis...egy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE'), ('sql', 'SELECT rb_phase2_lock_project(:id)')]
=========================== short test summary info ============================
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
1 failed in 0.65s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zq7hbkdg`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
```

```text
.                                                                        [100%]
1 passed in 0.63s
```

Exit code: **0**.

### M-L3

Copy-only edit in `src/researchbase/persistence/uow.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
"postgresql_readonly": True,
```

After:

```text
"postgresql_readonly": False,
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot
```

```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
______________ test_formal_read_has_one_readonly_snapshot[replay] ______________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
_______________ test_formal_read_has_one_readonly_snapshot[get] ________________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
_______________ test_formal_read_has_one_readonly_snapshot[list] _______________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
=========================== short test summary info ============================
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]
3 failed in 0.90s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-zcyxgzbi`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot
```

```text
...                                                                      [100%]
3 passed in 0.82s
```

Exit code: **0**.

### M-DRIFT

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
    if actual != BASELINE_CHECKS:
        raise RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")
```

After:

```text
    # Mutation: no baseline CHECK comparison.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift
```

```text
FF                                                                       [100%]
=================================== FAILURES ===================================
_ test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check] _
tests/integration/phase3/test_pr3_02_s2_intent_migration.py:47: in test_upgrade_refuses_receipt_check_drift
    with pytest.raises(
E   Failed: DID NOT RAISE <class 'RuntimeError'>
____ test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check] ____
tests/integration/phase3/test_pr3_02_s2_intent_migration.py:47: in test_upgrade_refuses_receipt_check_drift
    with pytest.raises(
E   Failed: DID NOT RAISE <class 'RuntimeError'>
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
2 failed, 4 warnings in 2.79s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-qih2i1uo`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift
```

```text
..                                                                       [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 4 warnings in 2.39s
```

Exit code: **0**.

### M-REVOKE-PUBLIC

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM PUBLIC;
```

After:

```text
-- Mutation: PUBLIC revoke removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k PUBLIC
```

```text
FFFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '0A000' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '0A000' == '42501'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_events]
8 failed, 8 deselected, 2 warnings in 0.78s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-no7z0cuc`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k PUBLIC
```

```text
........                                                                 [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 8 deselected, 2 warnings in 0.78s
```

Exit code: **0**.

### M-REVOKE-ROLE

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
        op.execute(
            f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM {quoted}"
        )
```

After:

```text
        pass  # Mutation: explicit-role revoke removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k normal_role-
```

```text
FFFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:83: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '0A000' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:90: AssertionError: assert '0A000' == '42501'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_events]
8 failed, 8 deselected, 2 warnings in 0.79s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-2l5obkw8`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k normal_role-
```

```text
........                                                                 [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 8 deselected, 2 warnings in 0.80s
```

Exit code: **0**.

### M-SHARE

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND granted
 AND relation=to_regclass('public.'||relation_name) AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
 RAISE EXCEPTION 'intent SHARE protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
```

After:

```text
 PERFORM 1; -- Mutation: SHARE guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:210: AssertionError: assert 'intent comma...ection absent' == 'intent SHARE...ection absent'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
1 failed, 2 warnings in 0.92s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-oeixmhdq`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 0.95s
```

Exit code: **0**.

### M-CAS

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
 IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;
```

After:

```text
 -- Mutation: insertion CAS guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
___________ test_named_insertion_and_receipt_guards[cas-pr302s2_cas] ___________
tests/integration/phase3/test_pr3_02_s2_intent_guards.py:211: in test_named_insertion_and_receipt_guards
    assert re.search(
E   AssertionError: PL/pgSQL function pr302_receipt_complete() line 52 at RAISE
E   assert None
E    +  where None = <function search at 0x10a552ca0>('^PL/pgSQL function pr302s2_execution_guard\\(\\) line \\d+ at RAISE$', ('PL/pgSQL function pr302_receipt_complete() line 52 at RAISE'), re.MULTILINE)
E    +    where <function search at 0x10a552ca0> = re.search
E    +    and   'PL/pgSQL function pr302_receipt_complete() line 52 at RAISE' = <psycopg.errors.Diagnostic object at 0x1101b0050>.context
E    +    and   re.MULTILINE = re.MULTILINE
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
1 failed, 2 warnings in 1.37s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-gxu66dxe`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.40s
```

Exit code: **0**.

### M-ISOLATION

Copy-only edit in `migrations/versions/0081_agent_execution_intents.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
 IF current_setting('transaction_isolation')<>'read committed' THEN
 RAISE EXCEPTION 'intent isolation' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
```

After:

```text
 -- Mutation: isolation guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
______ test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld] ______
tests/integration/phase3/test_pr3_02_s2_intent_guards.py:156: in test_named_insertion_and_receipt_guards
    with pytest.raises(DBAPIError) as exc, Session(env.owning_engine) as session, session.begin():
         ^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
1 failed, 2 warnings in 1.36s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-lm8sf5_d`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.28s
```

Exit code: **0**.

### M-REPLAY-PREFLIGHT

Copy-only edit in `src/researchbase/agent_runtime/application/agent_executions.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
            saved = repo.receipt(command)
            if saved:
                return None
```

After:

```text
            # Mutation: do not short-circuit saved receipt before bytes.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure
```

```text
FF                                                                       [100%]
=================================== FAILURES ===================================
________ test_saved_replay_precedes_retained_byte_failure[unavailable] _________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:33: in test_saved_replay_precedes_retained_byte_failure
    broken_open.assert_not_called()
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:910: in assert_not_called
    raise AssertionError(msg)
E   AssertionError: Expected 'mock' to not have been called. Called 1 times.
E   Calls: [call('sha256:28bf151822a35cc3d78e0c14d45fbba5c5f87017e5e9f92ded57821b7544f363')].
__________ test_saved_replay_precedes_retained_byte_failure[mismatch] __________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:33: in test_saved_replay_precedes_retained_byte_failure
    broken_open.assert_not_called()
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:910: in assert_not_called
    raise AssertionError(msg)
E   AssertionError: Expected 'mock' to not have been called. Called 1 times.
E   Calls: [call('sha256:28bf151822a35cc3d78e0c14d45fbba5c5f87017e5e9f92ded57821b7544f363')].
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
2 failed, 4 warnings in 3.40s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-0oytlzef`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure
```

```text
..                                                                       [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 4 warnings in 2.74s
```

Exit code: **0**.

### M-REPLAY-WRITE

Copy-only edit in `src/researchbase/agent_runtime/application/agent_executions.py` (first matching occurrence; L3 is scoped to `begin_formal_read`):

Before:

```text
            saved = self._saved(repo, command)
            if saved is not None:
                return saved
            if preflight_error is not None:
                raise preflight_error
```

After:

```text
            if preflight_error is not None:
                raise preflight_error
            saved = self._saved(repo, command)
            if saved is not None:
                return saved
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
_______ test_receipt_committed_during_failed_byte_preflight_is_replayed ________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:66: in test_receipt_committed_during_failed_byte_preflight_is_replayed
    result = env.intents.execute(env.intent)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:197: in execute
    return self._once(command, ids, preflight, preflight_error)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:218: in _once
    raise preflight_error
src/researchbase/agent_runtime/application/agent_executions.py:191: in execute
    preflight = self._preflight(command)
                ^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:129: in _preflight
    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained bytes mismatch")
src/researchbase/agent_runtime/application/agent_versions.py:26: in fail
    raise ResearchBaseError(code, message)
E   researchbase.foundation.errors.ResearchBaseError: retained bytes mismatch
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
1 failed, 2 warnings in 1.52s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/tmp/b3-mutation-93ieip44`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane351/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.33s
```

Exit code: **0**.

## Reproduction sources

The ignored helper scripts are reproduced here so the evidence does not depend on retaining temporary files. Invoke `python3 tmp/b3_mutations.py` after recreating it and applying the environment above. It asserts every pair is `[1, 0]`.

### tmp/b3_mutations.py

```python
"""Review B3 mutation witnesses; only disposable copies under this lane are edited."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile

root = Path.cwd()
logs = root / 'tmp/b3-evidence'
migration = 'migrations/versions/0081_agent_execution_intents.py'
repository = 'src/researchbase/persistence/agent_execution_repository.py'
service = 'src/researchbase/agent_runtime/application/agent_executions.py'
uow = 'src/researchbase/persistence/uow.py'
unit = 'tests/unit/phase3/test_agent_execution_repository.py::'
guards = 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::'
replay = 'tests/integration/phase3/test_pr3_02_s2_intent_replay.py::'
share_check = """ IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND granted
 AND relation=to_regclass('public.'||relation_name) AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
 RAISE EXCEPTION 'intent SHARE protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;"""
cas_check = " IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;"
saved_before_error = """            saved = self._saved(repo, command)
            if saved is not None:
                return saved
            if preflight_error is not None:
                raise preflight_error"""
cases = {
    'L2': (repository,
           '        self._session.execute(text(INTENT_SHARE_SQL))\n        after_wait()',
           '        self._session.execute(text(INTENT_SHARE_SQL))',
           [unit + 'test_fresh_checks_after_each_wait']),
    'L3': (uow, '"postgresql_readonly": True,', '"postgresql_readonly": False,',
           [unit + 'test_formal_read_has_one_readonly_snapshot']),
    'DRIFT': (migration,
              '    if actual != BASELINE_CHECKS:\n        raise RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")',
              '    # Mutation: no baseline CHECK comparison.',
              ['tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift']),
    'REVOKE-PUBLIC': (migration,
                      'REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM PUBLIC;',
                      '-- Mutation: PUBLIC revoke removed.',
                      [guards + 'test_normal_role_cannot_write_intent_tables', '-k', 'PUBLIC']),
    'REVOKE-ROLE': (migration,
                    '        op.execute(\n            f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM {quoted}"\n        )',
                    '        pass  # Mutation: explicit-role revoke removed.',
                    [guards + 'test_normal_role_cannot_write_intent_tables', '-k', 'normal_role-']),
    'SHARE': (migration, share_check, ' PERFORM 1; -- Mutation: SHARE guard removed.',
              [guards + 'test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]']),
    # Only the first CAS check is removed; the receipt-root CAS remains installed.
    'CAS': (migration, cas_check, ' -- Mutation: insertion CAS guard removed.',
            [guards + 'test_named_insertion_and_receipt_guards[cas-pr302s2_cas]']),
    'ISOLATION': (migration,
                  " IF current_setting('transaction_isolation')<>'read committed' THEN\n RAISE EXCEPTION 'intent isolation' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;",
                  ' -- Mutation: isolation guard removed.',
                  [guards + 'test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]']),
    'REPLAY-PREFLIGHT': (service,
                        '            saved = repo.receipt(command)\n            if saved:\n                return None',
                        '            # Mutation: do not short-circuit saved receipt before bytes.',
                        [replay + 'test_saved_replay_precedes_retained_byte_failure']),
    'REPLAY-WRITE': (service, saved_before_error,
                    '            if preflight_error is not None:\n                raise preflight_error\n'
                    '            saved = self._saved(repo, command)\n'
                    '            if saved is not None:\n                return saved',
                    [replay + 'test_receipt_committed_during_failed_byte_preflight_is_replayed']),
}

selected = sys.argv[1:] or list(cases)
for name in selected:
    path, old, new, nodes = cases[name]
    with tempfile.TemporaryDirectory(prefix='b3-mutation-', dir=root / 'tmp') as directory:
        copy = Path(directory)
        for folder in ('src', 'tests', 'migrations', 'scripts', 'execution', 'docs'):
            shutil.copytree(root / folder, copy / folder,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for filename in ('alembic.ini', 'pyproject.toml', 'uv.lock', 'README.md'):
            shutil.copyfile(root / filename, copy / filename)
        original = (copy / path).read_text()
        assert old in original, name
        # L3 is scoped to begin_formal_read, not another UoW method.
        if name == 'L3':
            prefix, body = original.split('    def begin_formal_read(self)', 1)
            mutated = prefix + '    def begin_formal_read(self)' + body.replace(old, new, 1)
        else:
            mutated = original.replace(old, new, 1)
        env = os.environ | {
            'PYTHONPATH': str(copy / 'src') + os.pathsep + str(copy),
            'PYTHONPYCACHEPREFIX': str(copy / 'bytecode'),
        }
        argv = [str(root / '.venv/bin/python'), '-m', 'pytest', '-o', 'addopts=',
                '-q', '-rfE', '--tb=line' if name in {'L2', 'SHARE', 'REVOKE-PUBLIC', 'REVOKE-ROLE'} else '--tb=short', '--show-capture=no', *nodes]
        exits = []
        try:
            for state, content in [('removed', mutated), ('restored', original)]:
                (copy / path).write_text(content)
                shutil.rmtree(copy / 'bytecode', ignore_errors=True)
                label = f'M-{name}-{state}'
                with (logs / f'{label}.out').open('w') as output:
                    result = subprocess.run(argv, cwd=copy, env=env, stdout=output,
                                            stderr=subprocess.STDOUT)
                exits.append(result.returncode)
                (logs / f'{label}.json').write_text(json.dumps({
                    'command': shlex.join(argv), 'cwd': str(copy), 'exit_code': result.returncode,
                    'path': path, 'old': old, 'new': new,
                }))
                print(label, 'exit', result.returncode, flush=True)
        finally:
            (copy / path).write_text(original)
        assert (root / path).read_text() == original, 'original checkout changed'
        assert exits == [1, 0], (name, exits)
```

### tmp/b3_scope_audit.py

```python
import ast
import hashlib
import re
import subprocess
from pathlib import Path

accepted = subprocess.check_output(['git', 'ls-files', 'migrations/versions/*.py'], text=True).splitlines()
protected = accepted + [
    'pyproject.toml', 'uv.lock', 'docs/phase3/PR3-02-S2-contract-freeze.md',
    'src/researchbase/foundation/errors.py',
    'src/researchbase/agent_runtime/domain/research_task.py',
    'src/researchbase/agent_runtime/application/research_task.py',
    'src/researchbase/agent_runtime/application/capability_gateway.py',
    'src/researchbase/persistence/capability_gateway_repository.py',
    'src/researchbase/agent_runtime/application/task_safety.py',
    'src/researchbase/persistence/task_safety_repository.py',
    'src/researchbase/agent_runtime/application/promotion_context.py',
]
for name in protected:
    original = subprocess.check_output(['git', 'show', f'HEAD:{name}'])
    assert Path(name).read_bytes() == original, name
path = Path('migrations/versions/0081_agent_execution_intents.py')
module = ast.parse(path.read_text())
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
ddl = constants['DDL']
assert re.findall(r'CREATE TABLE (\w+)', ddl) == ['agent_execution_instances', 'agent_execution_events']
assert re.findall(r'ADD COLUMN (\w+)', ddl) == ['result_execution_id', 'result_execution_event_id']
functions = set(re.findall(r'CREATE(?: OR REPLACE)? FUNCTION (\w+)', constants['FUNCTIONS']))
assert functions == {'pr302s2_cjson', 'pr302s2_value_digest', 'pr302s2_input_material', 'pr302s2_preheld', 'pr302s2_execution_guard', 'pr302s2_event_guard', 'pr302s2_immutable', 'pr302_receipt_guard', 'pr302_receipt_complete'}
for forbidden in ('agent_promotion_records', 'agent_promotion_outputs', 'producing_execution_id', 'result_promotion_id', 'AGENT_EXECUTION_FAKE', 'S2ConsumerContext', 'S2CaptureContext', 's2_admission', 'AGENT_POLICY'):
    assert forbidden not in ddl + constants['FUNCTIONS'], forbidden
new_files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
for name in new_files:
    data = Path(name).read_text()
    assert data.endswith('\n') and all(line == line.rstrip() for line in data.splitlines()), name
print(f'Protected bytes unchanged: {len(accepted)} accepted migrations; dependencies, freeze, public errors, closed task gate, gateway, safety and producer-preview paths.')
print('Exact intent delta: 2 tables; 2 nullable receipt links; 9 allowed functions; no deferred identifiers.')
print(f'Untracked deliverables checked for trailing whitespace and final newline: {len(new_files)} files.')
print('Migration SHA-256:', hashlib.sha256(path.read_bytes()).hexdigest())
```

## Completion boundary

All listed normal verification commands exited 0; all ten removed-guard mutations exited 1 for the expected assertion failure, and all ten restored controls exited 0. No unrun command is recorded as PASS. Full suite: **NOT RUN by this agent**. External-loop output and independent review/owner acceptance: **NOT AVAILABLE in this task**; no full-suite or acceptance-gate success is asserted.
