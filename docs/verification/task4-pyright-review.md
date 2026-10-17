# Task 4: Pyright review remediation

## Scope and check

Pyright is clean: 94 initial errors, 0 final errors. All initial diagnostics were
in tests. The 95 grandfathered fixture entries have been removed. Production
code, migrations, architecture, dependencies, and Pyright configuration are unchanged.

The follow-up code change exposes the existing `m3` fixture in
`tests/integration/phase2/conftest.py`; fixture implementation and scope are unchanged.
This fixes the collection-order problem described below.

All commands ran from the repository (or the isolated baseline checkout) with:

```sh
export UV_CACHE_DIR=/private/tmp/researchbase-uv-cache
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

The requested command chain passed, exit 0:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -p no:cacheprovider tests/unit tests/architecture
```

Results: 0 Pyright errors/warnings; 438 Python files formatted; Ruff check passed;
**1809 tests passed**, 2 warnings, 31.13 seconds (1752 unit + 57 architecture).

## P1: actual clean-HEAD failure comparison

The baseline is a detached, clean checkout of
`dd3982e30f6c483edf0a674fa2caed15132c6e35`, in
`tmp/task4-verification/clean-head`. Its tracked tree is exactly HEAD, its
`git status --porcelain` output is empty, and it has no branches. No commit,
push, stash, or original-repository metadata mutation was made.

The sandbox disallowed `.git/worktrees` writes, so the isolated checkout has
its own Git metadata with read-only object alternates pointing at the main
repository's object store. This retains Git history needed by migration tests.
It has its own uv environment built from the unchanged HEAD dependency lock.

The same complete 63-node list below was run on clean HEAD and the modified
checkout, with the same database environment, without explicit fixture plugins:

```sh
uv run pytest -q --tb=short <all 63 node IDs below> --junitxml <output-path>
```

Exact argv/cwd manifests: `tmp/task4-verification/review-head-63-command.json`
and `tmp/task4-verification/review-current-63-command.json`.

| Checkout | Tests | Failed | Setup errors |
| --- | ---: | ---: | ---: |
| Clean HEAD | 63 | 63 | 0 |
| Modified checkout | 63 | 63 | 0 |

The failed-node sets extracted from both JUnit XML files are identical to each
other and to the original reported 63-node list. Both set differences are empty.
Machine-readable comparison: `tmp/task4-verification/review-63-comparison.json`.
Raw logs/XML files use the `review-head-63` and `review-current-63` prefixes.

Seven of these failures are in previously modified integration files: one in
`test_pr2_03_review_guards.py`, one in `test_pr2_04_authority_coverage.py`,
three in `test_pr2_04_outcome_reapplication_acceptance.py`, one in
`test_pr2_04_retrieval_observation_repair.py`, and one in
`test_pr2_04_structural_guard_repair.py`. These seven fail on clean HEAD too.
The HG1 review and bound-subject files are not among the 63 failures.

## P1: HG1 fixture before/after verification

The original HEAD file invokes the wrapped generator directly. The modified
file uses pytest fixture dependency resolution. Both existing fixtures have
function scope and no parametrization; the underlying generator and its engine
cleanup are unchanged. The HG1 fixture runs its test-only database/CAS setup
and teardown under both implementations.

Run in each checkout:

```sh
uv run pytest tests/integration/phase2/test_hg1_review_integration.py -q --junitxml <output-path>
```

**Clean HEAD: 1 passed. Modified checkout: 1 passed.** Neither run uses `-p`.
This file is not among the 63 failures. Exact commands and output are in
`tmp/task4-verification/review-hg1-commands.json` and the `review-hg1-*` logs/XML.

## P1: shared-fixture collection defect and standard invocation

The 88 prior setup errors were `fixture 'm3' not found`. They were a real
collection-order defect also present on HEAD, not passing test outcomes.
The earlier consolidated count after `-p` reruns did not establish that the
standard suite invocation worked.

The shared fixture is defined in `test_m3_evidence.py`. When that module is
collected as a normal test module first, its fixtures have module visibility.
Later `pytest_plugins` requests import the same already-scanned module object.
The installed pytest `FixtureManager.parsefactories` tracks scanned objects in
`_holderobjseen`; it returns immediately on a repeated object, before creating
fixture definitions with plugin-wide visibility. Thus the original definitions
retain module visibility. Dependent suites calling `request.getfixturevalue("m3")`
then fail at setup. This cache behavior was verified in the installed
`.venv/lib/python3.12/site-packages/_pytest/fixtures.py` and reproduced below.

The fix re-exports `m3` from the Phase 2 `conftest.py`, making its visibility
explicit for every Phase 2 suite regardless of collection/plugin order.
No command-line plugin override is needed and the fixture body is unchanged.

A minimal normal-CLI reproduction, run on clean HEAD and the modified checkout:

```sh
uv run pytest   tests/integration/phase2/test_m3_evidence.py::test_pg_manual_evidence_replay_and_restart   tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_freeze_and_unreviewed_positive_support_fail_closed   -o addopts='' -q --tb=short --junitxml <output-path>
```

**Clean HEAD: 1 passed, 1 setup error. Modified checkout: 2 passed, 0 errors.**
Exact commands are in `tmp/task4-verification/review-fixture-order-commands.json`;
the corresponding `review-fixture-order-*` logs/XML contain the missing-fixture
traceback before the fix and successful execution after it.

The exact standard suite command, with no `-p` flags or selection overrides:

```sh
uv run pytest tests/integration/phase2
```

**Completed: 2121 passed, 63 failed, 1 skipped, 0 setup errors**, 2528 warnings,
4671.23 seconds (1:17:51). Exit 1 is due to the same 63 failures reproduced on
clean HEAD. The standard suite's failed-node set is also identical to that clean
baseline; both set differences are empty. No explicit fixture-plugin flags or
selection overrides were used. All previously errored dependent fixtures resolve
and their test bodies execute successfully in this ordinary invocation.

Machine-readable result: `tmp/task4-verification/review-standard-comparison.json`.
The **870** temporal-phase/temporal-wait cases passed as part of this standard run.
Log: `tmp/task4-verification/review-standard-phase2.log`.

The event-fixture dictionary annotation was also corrected to include its actual
datetime values, without changing its data or runtime logic. The dedicated
PostgreSQL check passed:

```sh
uv run pytest tests/integration/phase2/test_pr2_04_remaining_schema_acceptance.py -o addopts='' -q
```

**15 passed**, 15 warnings, 6.05 seconds. Log:
`tmp/task4-verification/review-event-annotation.log`.

## P2: cross-project case and bound-subject coverage

```sh
uv run pytest   'tests/integration/phase2/test_pr2_03_review_guards.py::test_question_reference_validation_matrix[cross_project]'   tests/integration/phase2/test_hg1_bound_subject.py   -o addopts='' -q --junitxml=tmp/task4-verification/review-cross-project-and-bound.xml
```

**2 passed**, 3 warnings, 0.66 seconds. In particular, the cross-project case
passes against PostgreSQL after the incorrect service-call arguments are fixed.
No production API/contract changed.

## P2: complete diff and suppression audit

The complete untruncated diff is saved as `tmp/task4-verification/review/full.diff`.
The requested audit command was run and saved as `review/diff-audit.log`:

```sh
git diff HEAD | grep -nE 'pyright: ignore|type: ignore|Any|cast\('
```

The added Python lines contain exactly two rule-specific suppressions, both
with a one-line justification immediately before the deliberately invalid call:

```python
# Deliberately pass a raw string to verify the runtime typed-locator boundary.
EvidenceCandidate(uuid4(), "internal-index:opaque-42", "excerpt")  # pyright: ignore[reportArgumentType]

# Deliberately pass an unverified identity to exercise the runtime rejection.
SimpleNamespace(actor_id=UUID(TARGET)),  # pyright: ignore[reportArgumentType]
```

Locations: `tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py` and
`tests/unit/test_hg1_review_ops.py`. There are no added blanket suppressions,
broad dynamic-type annotations, or casts. Other audit matches are textual references in diagnostics/documentation or
unchanged import context.

## Complete list of the 63 failing node IDs

```text
tests/integration/phase2/test_m0_provider_cancellation.py::test_migration_empty_roundtrip_and_populated_downgrade
tests/integration/phase2/test_m2_metadata.py::test_empty_m2_migration_roundtrip
tests/integration/phase2/test_m3_evidence.py::test_pg_m3_alembic_env_preserves_percent_escaped_socket_url
tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait
tests/integration/phase2/test_pr2_03_effective_authority.py::test_authority_loss_during_observed_project_lock_wait[run-1]
tests/integration/phase2/test_pr2_03_effective_authority.py::test_authority_loss_during_observed_project_lock_wait[run-2]
tests/integration/phase2/test_pr2_03_effective_authority.py::test_authority_loss_during_observed_project_lock_wait[run-3]
tests/integration/phase2/test_pr2_03_effective_authority.py::test_authority_loss_during_observed_project_lock_wait[run-4]
tests/integration/phase2/test_pr2_03_effective_authority.py::test_authority_loss_during_observed_project_lock_wait[run-5]
tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py::test_pr2_03_fresh_install_adds_exact_four_tables_and_unique_head
tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py::test_pr2_03_populated_downgrade_refuses_before_dropping_tables
tests/integration/phase2/test_pr2_03_review_guards.py::test_remediation_child_upgrade_empty_downgrade_and_unique_head
tests/integration/phase2/test_pr2_04_authority_coverage.py::test_pg_equal_created_at_cursor_uses_uuid_tiebreak_without_duplicates_or_omissions
tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_historical_migration_bytes_match_frozen_accepted_tree
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta[fresh]
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta[phase1_0018]
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta[populated_0023a]
tests/integration/phase2/test_pr2_04_outcome_certainty_matrix_acceptance.py::test_pg_complete_outcome_reason_certainty_matrix[NOT_SENT-CANCELLED]
tests/integration/phase2/test_pr2_04_outcome_certainty_matrix_acceptance.py::test_pg_complete_outcome_reason_certainty_matrix[RESPONSE_RECEIVED-CANCELLED]
tests/integration/phase2/test_pr2_04_outcome_reapplication_acceptance.py::test_pg_all_outcome_exact_reapplication_and_changed_tuple[request_id-cancelled]
tests/integration/phase2/test_pr2_04_outcome_reapplication_acceptance.py::test_pg_all_outcome_exact_reapplication_and_changed_tuple[retry_after-cancelled]
tests/integration/phase2/test_pr2_04_outcome_reapplication_acceptance.py::test_pg_all_outcome_exact_reapplication_and_changed_tuple[warnings-cancelled]
tests/integration/phase2/test_pr2_04_parent_restrict_acceptance.py::test_pg_referenced_parent_delete_cannot_remove_provenance[actors]
tests/integration/phase2/test_pr2_04_parent_restrict_acceptance.py::test_pg_referenced_parent_delete_cannot_remove_provenance[literature_search_executions]
tests/integration/phase2/test_pr2_04_parent_restrict_acceptance.py::test_pg_referenced_parent_delete_cannot_remove_provenance[projects]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_admission_rejects_invalid_exact_plan_without_effects[abandoned]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_admission_rejects_invalid_exact_plan_without_effects[draft]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_admission_rejects_invalid_exact_plan_without_effects[foreign]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_admission_rejects_invalid_exact_plan_without_effects[missing]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_admission_rejects_invalid_exact_plan_without_effects[superseded]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_plan_supersession_never_substitutes_current_version[before_first_start]
tests/integration/phase2/test_pr2_04_plan_binding_coverage.py::test_pg_plan_supersession_never_substitutes_current_version[during_provider]
tests/integration/phase2/test_pr2_04_provider_budget_completion.py::test_pg_lowered_provider_cap_preserves_mixed_failure_history[1]
tests/integration/phase2/test_pr2_04_provider_budget_completion.py::test_pg_lowered_provider_cap_preserves_mixed_failure_history[2]
tests/integration/phase2/test_pr2_04_provider_budget_completion.py::test_pg_lowered_provider_cap_preserves_mixed_failure_history[3]
tests/integration/phase2/test_pr2_04_r8a_reservation_guards.py::test_r8a_populated_upgrade_downgrade_preserves_rows
tests/integration/phase2/test_pr2_04_r8a_reservation_guards.py::test_r8a_valid_reservations_keep_exact_deadline[one_second]
tests/integration/phase2/test_pr2_04_retrieval_observation_repair.py::test_pg_sealed_retrieval_observations_are_immutable[attempt-P17D1]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_atomic_outcome_rejects_invalid_complete_response_set[mixed_retrieval_times]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_atomic_outcome_rejects_invalid_complete_response_set[rank_gap_at_seal]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[literature_search_executions.created_by-6]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[literature_search_executions.requested_by-5]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[literature_search_provider_attempts.created_by-14]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[search_query_records.created_by-17]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_required_column_null_is_rejected[literature_search_executions.created_by]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_required_column_null_is_rejected[literature_search_executions.executed_by]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_required_column_null_is_rejected[literature_search_executions.requested_by]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_every_fk_has_unconditional_leading_btree_index[literature_search_execution_command_receipts]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_every_fk_has_unconditional_leading_btree_index[literature_search_execution_events]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_every_fk_has_unconditional_leading_btree_index[literature_search_executions]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_every_fk_has_unconditional_leading_btree_index[literature_search_provider_attempts]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_every_fk_has_unconditional_leading_btree_index[search_query_records]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_live_column_pk_nullability_and_fk_restrict_inventory[literature_search_execution_command_receipts]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_live_column_pk_nullability_and_fk_restrict_inventory[literature_search_provider_attempts]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_live_column_pk_nullability_and_fk_restrict_inventory[search_query_records]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_query_same_parent_and_atomic_observation_guards[input_mismatch]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_query_same_parent_and_atomic_observation_guards[ordinal_gap]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_reservation_uniqueness_contiguity_and_input_bounds[invalid_input_index]
tests/integration/phase2/test_pr2_04_schema_coverage.py::test_reservation_uniqueness_contiguity_and_input_bounds[number_gap]
tests/integration/phase2/test_pr2_04_structural_guard_repair.py::test_exact_scoped_query_key_supports_concrete_fk
tests/integration/phase2/test_pr2_04_success_coordinates_acceptance.py::test_pg_success_full_coordinates_and_admission[one-hit]
tests/integration/phase2/test_pr2_04_success_coordinates_acceptance.py::test_pg_success_full_coordinates_and_admission[zero-hit]
```
