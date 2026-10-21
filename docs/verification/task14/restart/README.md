# Task 14 historical local-mode sharded verification

**Scope correction:** The 5,169-pass total below belongs only to the historical
`HG1_RUN_LOCAL=1` sharded run. It is not the result of the reviewer's exact serial
command with HG1 flags unset. That reviewer run printed `5168 passed, 1 skipped,
2940 warnings in 4957.65s`; the skip is not a pass. See the
[round 3 verification](../round3/README.md) for the default-environment rerun and
skip diagnosis.

The approved contract is [PR2-16 Basic Approval](../../../proposals/PR2-16_Basic_Approval_Contract.md).
This run continues the earlier working tree. Earlier task14 verification files are
historical evidence; the `*-final` files here will hold the final restart results.

Implemented scope: internal scientific approval request, independent HUMAN
approval decision, bounded grant, and exact-ID reads through the existing
Application/UoW/repository boundary. Migration 0045 follows 0044. Error mappings
are added; no API routes or CLI commands are required. Task 13's protected
snapshot/read policy is reused without changing RevisionAction history.

Restart corrections: approved contract renamed; future credential binding denied
by SQL; rationale NFC/nonblank enforced by SQL; newer selected target prevents a
late decision on an older pending request. Six new PostgreSQL cases cover these
boundary gaps. Read-only sub-agent review found no remaining P0/P1 in the fixes;
the primary agent owns all writes and verification.

## Exact commands and current results

All final commands exited **0**. Exact commands (including JUnit output paths)
and printed results are recorded in [checks.json](checks.json). Each log is
retained alongside its JUnit report. Pyright also prints an available-version
update notice after its zero-diagnostic summary.

| Check | Actual printed result |
| --- | --- |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `482 files already formatted` |
| `uv run pytest -o addopts='' -q tests/unit` | `1841 passed, 4 warnings in 37.44s` |
| `uv run pytest -o addopts='' -q tests/architecture` | `60 passed, 1 warning in 2.27s` |
| `uv run pytest -o addopts='' -q -ra tests/integration/phase2/test_approval.py` | `69 passed, 210 warnings in 50.40s` |

All three final pytest selections above have **0 failures, 0 errors, 0 skips**,
confirmed by their JUnit reports. These are separate runs; their counts are not
added to the full-suite count.

All commands use `UV_CACHE_DIR=tmp/task14-verification/uv-cache`. The Approval
selection uses `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase`
and `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres`.
The exact full-suite invocation was:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres HG1_RUN_LOCAL=1 UV_CACHE_DIR=tmp/task14-verification/uv-cache uv run python docs/verification/task14/restart/run_full.py
```

This runner migrated a fresh disposable database on **PostgreSQL 18.6**, then
collected and partitioned the entire suite. Shared Phase 1 tests ran serially in
partition 0; Phase 2 tests used their disposable database fixtures in partitions
1–4. `HG1_RUN_LOCAL=1` explicitly selects the inherited optional runner test's
disposable local deployment mode; this is not the default environment that skips
that test, and it does not access durable live deployments.

The per-partition commands, environment, collection, partition identities, raw
logs, exit codes and JUnit reports are retained in [full/](full/). The printed
pytest summaries are:

| Partition | Actual printed summary |
| --- | --- |
| 0 | `2854 passed, 9 warnings in 139.64s (0:02:19)` |
| 1 | `579 passed, 762 warnings in 1253.19s (0:20:53)` |
| 2 | `579 passed, 752 warnings in 1327.67s (0:22:07)` |
| 3 | `579 passed, 745 warnings in 1250.53s (0:20:50)` |
| 4 | `578 passed, 747 warnings in 1274.85s (0:21:14)` |

The runner printed the reconciled full-suite totals: **5169 passed, 0 failures,
0 errors, 0 skipped**. All five partitions exited **0**. The
[summary](full/summary.json) verifies **5169 collected = 5169 unique results**,
with no missing, extra or duplicate identities. The
[cleanup record](full/cleanup.json) confirms the temporary database was dropped
and its absence checked.

Final audits: [46 accepted migration files](accepted-migrations.json) remain
byte-identical to HEAD; `alembic heads` prints
`0045_pr2_16_basic_approval (head)`; [source hashes](source-hashes.json) were
compared again after the full run with **0 changes**. The
[accepted test inventory](accepted-tests.json) records no removed functions or
reduced assertion counts. A final documentation check verifies the approved
status/title, renamed file, 24 local links and no trailing whitespace;
`git diff --check HEAD` exits 0.

## Why each accepted test was modified (16 functions plus 2 helper consumers)

No accepted test or assertion was removed. All pre-existing migration files must
remain byte-identical to HEAD; the new migration is the sole schema addition.

| Existing accepted test file | Function | Reason |
| --- | --- | --- |
| `tests/architecture/test_import_boundaries.py` | `test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration` | Add authorized 0045 to the exact migration lineage. |
| `tests/e2e/test_phase1_failure_recovery.py` | `test_every_stable_researchbase_error_has_explicit_http_and_cli_mapping` | Extend exhaustive HTTP/CLI mapping coverage for seven Approval codes. |
| `tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py` | `test_pr2_03_fresh_install_adds_exact_four_tables_and_unique_head` | Advance the expected global head to 0045; keep the exact migration-specific table delta. |
| `tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py` | `test_pr2_03_populated_downgrade_refuses_before_dropping_tables` | Advance the unchanged head expected after downgrade refusal. |
| `tests/integration/phase2/test_pr2_03_review_guards.py` | `test_remediation_child_upgrade_empty_downgrade_and_unique_head` | Advance the expected global head to 0045. |
| `tests/integration/phase2/test_pr2_04_execution_migration.py` | `test_pr2_04_upgrade_adds_exact_tables_and_unique_head` | Advance the expected global head; keep the exact migration-specific checks. |
| `tests/integration/phase2/test_pr2_04_migration_coverage.py` | `test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta` | Advance the expected global head; retain exact migration-specific checks. |
| `tests/integration/phase2/test_pr2_04_migration_coverage.py` | `test_historical_migration_bytes_match_frozen_accepted_tree` | Advance the expected global head; retain frozen byte-integrity checks. |
| `tests/integration/phase2/test_pr2_15_decision_schema.py` | `test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables` | Advance the expected global head; retain exact 0042 schema checks. |
| `tests/integration/phase2/test_revision_action.py` | `test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog` | Pin the exact RevisionAction table-delta test to 0044, and separately advance the global head. |
| `tests/test_architecture.py` | `test_phase1_has_no_unauthorized_later_business_schema_migration` | Permit approved 0045 references to existing scientific_conclusions/literature_evidence tables. |
| `tests/unit/foundation/test_errors.py` | `test_normative_error_codes_are_stable` | Add seven approved stable Approval error codes. |
| `tests/unit/phase2/test_pr2_04_r8a_host_topology.py` | `test_r8a_actual_migration_graph_and_frozen_bytes` | Advance the head and immediate parent; preserve frozen byte-integrity checks. |
| `tests/unit/test_pr15_http.py` | `test_all_researchbase_error_codes_have_frozen_status_mapping` | Extend exhaustive HTTP 409 mapping expectations for seven Approval errors. |
| `tests/unit/test_pr16_cli_errors.py` | `test_all_stable_error_codes_have_cli_exit_mapping` | Extend exhaustive CLI exit-code 4 expectations for seven Approval errors. |
| `tests/unit/test_task12_migration_history.py` | `test_task12_preserves_every_historical_migration_byte_and_exact_child` | Allow the additive 0045 descendant and advance the head; retain historical byte checks. |

The `_catalog` helper in `tests/integration/phase2/test_pr2_04_migration_coverage.py`
now sorts inspector table names. This preserves exact catalog membership while
eliminating ordering-only differences. Its two additional accepted test consumers
are `test_empty_downgrade_removes_exact_tables_and_reupgrade_restores_catalog` and
`test_each_populated_table_independently_refuses_downgrade_before_any_ddl`.

`tests/fixtures/phase2_static_baseline.json` and CI also advance the expected head.
The new Approval test files are not previously accepted tests. Within the new
Approval tests, the other-target rejection case rejects the newer selected
request before testing that the earlier pending request cannot bypass rejection.
This preserves symmetric gate validation for REJECT.

## Superseded and interrupted evidence

The initial restart full invocation was interrupted while the source was being
corrected. Its printed summary was **19 failed, 142 passed, 1 skipped, 310 warnings,
73 errors** followed by KeyboardInterrupt (exit 2). The errors include the
intermediate migration SQL string escaping error, corrected before the final
run. Its `full.log`/`full.xml` are retained, not relabeled as passes. The subsequent
full run uses the final migration source in a fresh disposable PostgreSQL 18
database. The database is dropped in the runner's `finally` block.

The initial separate restart unit/architecture checks printed **1841 passed,
4 warnings** and **72 passed, 1 warning** respectively; the latter included
`tests/test_architecture.py` as well as `tests/architecture`. Final separate
architecture results use only `tests/architecture`; the full suite includes both.

A subsequent serial full invocation was stopped to switch to parallel partitions.
The wrapper exited **130**, without a completed pytest summary; its
`full-final.log`, `full-final.xml`, `full-runner.log` and `full-cleanup.json` are
interrupted-run evidence only. The disposable database was dropped and absence
checked. No completed pass count is claimed for this attempt.
