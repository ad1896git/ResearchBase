# Task 14 review round 3 verification

The earlier summary conflated two different environments. The reviewer-provided
serial check printed `5168 passed, 1 skipped, 2940 warnings in 4957.65s`.
The historical `HG1_RUN_LOCAL=1` sharded run printed 5,169 reconciled passes and
zero skips. Its explicit local-mode opt-in runs the inherited optional runner
test on disposable deployments. The reviewer command leaves both HG1 flags unset
and skips that test. These results are separate; a skip is not a pass.

The exact reviewer command was rerun to completion, without either HG1 flag:

```bash
uv run pyright && uv run ruff format --check . && uv run ruff check . && DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Only the uv cache is redirected into the repository. `PYTEST_ADDOPTS` is unset.
The command exited **0**. Its verbatim final line is:

```text
5168 passed, 1 skipped, 2940 warnings in 4967.06s (1:22:47)
```

This serial run has **one skipped test**. It is not the 5,169-pass local-mode
sharded run. The serial output reports 5,168 passes plus one skip. The historical
sharded run reports 5,169 passes; its explicit local mode exercises the optional
runner test. The diagnosed skip accounts for the one-pass difference.

The command's Pyright/Ruff prefix printed `0 errors, 0 warnings, 0 informations`,
`482 files already formatted`, and `All checks passed!`. Raw current output is
retained in `check.log`; the exit code is in `check-exit.txt`.

The targeted skip diagnosis used the same pytest options with `-rs` and the exact
node ID appended. Its verbatim output is retained in `skip.log`:

```text
SKIPPED [1] tests/integration/phase2/test_hg1_runner_live.py:111: set HG1_RUN_LIVE=1 for the authorized read-only M2 check
1 skipped in 0.02s
```

Skipped node:
`tests/integration/phase2/test_hg1_runner_live.py::test_four_durable_deployments_authenticate_and_clean_up`.
It is pre-existing, not caused by Approval: the entire test file is byte-identical
to HEAD, as recorded in `skip-origin.json`. The skip condition has not been changed.

No implementation, accepted test, migration, or test-selection behavior is
changed in this round. Corrections are to reporting scope and review evidence.

The first separate unit run exposed trailing whitespace in newly included
historical evidence artifacts: `1 failed, 1840 passed, 4 warnings in 34.74s`.
The existing static gate was unchanged. Nine historical text/XML/diff artifacts
were cleaned after their exact original bytes were preserved in `raw/*.gz`;
`whitespace-cleanup.json` records hashes and verifies lossless decompression.
These readable historical copies are whitespace-cleaned previews; compressed
originals retain verbatim historical output. `git diff --check` against both HEAD
and the frozen static baseline now exits 0.

The literal requested `uv run pytest tests/unit -q` and
`uv run pytest tests/architecture -q` both exit 0 after cleanup. Because the
repository's pytest configuration already includes `-q`, their doubled quiet
mode suppresses numeric result lines. Separately repeating with `-o addopts=''`
produced these verbatim summaries:

```text
1841 passed, 4 warnings in 38.70s
60 passed, 1 warning in 2.25s
```

Separate Pyright output:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`
```

Separate `uv run ruff format --check . && uv run ruff check .` output:

```text
482 files already formatted
All checks passed!
```

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


The complete literal `git diff HEAD --stat` output is retained in `diff-stat.txt`
and pasted in the final review summary. New round-three evidence files are
untracked and therefore are not included by that Git command. No source code,
accepted test, or migration was modified in this round.
