# PR3-00 implementation evidence

Owner authorization: 2026-10-20, PR3-00 only, ADR-0021. Accepted Phase 2 baseline:
commit `286cd9a`, parent `0075_m1_reconsideration`. New sole head:
`0076_agent_runtime_bootstrap`. See [contract freeze](PR3-00-contract-freeze.md).
ADR-0022 records PR3-01 decisions; that implementation remains unauthorized.

Implementation: 16 zero-byte package markers, one empty forward-only migration,
recursive import-boundary tests with malicious nested fixtures, real PostgreSQL
bootstrap tests, value-only head/parent expectations and historical Phase 2
round-trip upper bounds, README and this scoped evidence. No production behavior,
dependency, table, column, trigger, API/CLI command, task model or worker is added.

Verification environment: macOS, Python 3.12.15, pytest 8.4.2, PostgreSQL
`server_version_num=180006` (18.6); existing explicit `RB_TEST_ADMIN_URL` local
admin selector. PostgreSQL suites use disposable databases; test file artifacts
are under `tmp_path`. No retained database was migrated.

All commands below ran in the repository. The uv cache override avoids writes to
the restricted shared cache. PostgreSQL 18 tools were selected through PATH:

```sh
export UV_CACHE_DIR=/private/tmp/researchbase-lane85-uv
export PATH=/opt/homebrew/opt/postgresql@18/bin:$PATH
```

Final static commands and observed results:

```sh
uv run ruff check .
# All checks passed! (exit 0)
uv run ruff format --check .
# 817 files already formatted (exit 0)
uv run pyright
# 0 errors, 0 warnings, 0 informations (exit 0)
uv run alembic heads
# 0076_agent_runtime_bootstrap (head) (exit 0)
git diff --check
# no output (exit 0)
```

Pyright also printed its available-version notice; no dependency was changed.

Combined architecture, selected unit and bootstrap verification (exact targets):

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture tests/test_architecture.py tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py tests/integration/phase3/test_pr3_00_bootstrap.py
```

Observed: **362 passed, 0 failed, 0 skipped, 68 warnings in 31.87s**, exit 0.
The warnings are the inherited Alembic `path_separator` deprecation.
The new architecture module contributes 59 tests; the new PostgreSQL module
contributes six tests.

The additional bootstrap observation run captured inventory hashes:

```sh
uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_00_bootstrap.py > /private/tmp/researchbase-pr300-bootstrap-output.txt 2>&1
```

Observed: **6 passed, 0 failed, 0 skipped, 14 warnings in 5.82s**, exit 0.
Proof: clean install and idempotent re-upgrade; single head with exact parent;
empty and populated 0075 → 0076 upgrades; refused downgrades to 0075 and base.
The populated upgrade and both refusal cases contain 17 rows, including frozen
ResearchQuestion and LiteratureSearchPlan versions and their concrete input
relation. Complete row JSON comparisons preserve hashes, identity and reference
edges; Application readbacks also remain equal.

All compared catalogs have 131 application tables (excluding `alembic_version`).
Normalized full `pg_dump --schema-only --no-owner --no-privileges` text is identical
before/after; this covers columns, FKs/checks, indexes, triggers, functions, views,
sequences and other schema DDL. Only PostgreSQL 18's randomized psql restrict
keys are removed. Schema SHA-256 for clean, parent, bootstrap and refused states:
`9543d9b43f82bc3501f3a7436e085482ec9b988d140580a69aa9bc04b0645a22`.
The revision changes from 0075 to 0076 only on successful upgrade. Refusal leaves
0076 installed. Catalog delta: zero; row delta excluding revision value: zero.
The populated upgrade's full row JSON SHA-256 is
`dce94999fb217ebb63b3443631c2c002b00d98ee84a040cd58000b553f8b48e2`
on both sides. UUID/time-dependent fixture row hashes naturally differ between
independent databases; equality is checked within each transition.

Focused Phase 2 PostgreSQL regression selectors follow. They cover changed
migration expectations/round trips and all failures observed in the earlier
broader diagnostic run. Existing test control flow, assertions and historical
migration bytes are retained; round trips stop at the accepted Phase 2 head so
they continue testing their owning revisions without crossing PR3-00's guard.

```sh
cat > /private/tmp/researchbase-pr300-final-pg-selectors.txt <<'EOF'
tests/integration/phase2/test_approval.py::test_empty_downgrade_upgrade_and_catalog
tests/integration/phase2/test_b01_resolution_schema.py::test_nullable_legacy_hash_survives_downgrade_and_reupgrade
tests/integration/phase2/test_b02_strategy_schema.py::test_empty_and_populated_downgrade_and_preserved_existing_rows
tests/integration/phase2/test_b03_discussion_hypothesis.py::test_empty_upgrade_to_head
tests/integration/phase2/test_b03_discussion_hypothesis.py::test_prior_head_upgrade_keeps_receipts_and_empty_downgrade
tests/integration/phase2/test_b04_manuscript_migration.py::test_populated_draft_downgrade_and_frozen_refusal
tests/integration/phase2/test_b04_manuscript_migration.py::test_upgrade_catalog_and_empty_downgrade
tests/integration/phase2/test_b05_review_migration.py::test_populated_history_prevents_downgrade
tests/integration/phase2/test_b05_review_migration.py::test_preflight_rejects_incompatible_history_and_populated_downgrade
tests/integration/phase2/test_b05_review_migration.py::test_upgrade_actual_head_catalog_and_empty_downgrade
tests/integration/phase2/test_b06_revision_action.py::test_forward_migration_retains_shipped_history_and_preserved_catalog
tests/integration/phase2/test_b06_revision_action.py::test_global_artifact_metric_inputs_keep_phase1_owner_semantics
tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade
tests/integration/phase2/test_b07_schema.py::test_revision_history_refuses_downgrade_and_late_append
tests/integration/phase2/test_b07_schema.py::test_upgrade_preflights_retained_release_without_reapplying_late_blockers
tests/integration/phase2/test_b08_schema.py::test_populated_b07_upgrade_open_downgrade_and_terminal_refusal
tests/integration/phase2/test_b08_schema.py::test_upgrade_preflight_refuses_corrupt_legacy_root_without_partial_ddl
tests/integration/phase2/test_b09_approval_schema.py::test_b09_catalog_and_empty_roundtrip
tests/integration/phase2/test_b09_approval_schema.py::test_populated_forward_preserves_literal_history_and_downgrade_refuses
tests/integration/phase2/test_b10_reconsideration_schema.py::test_empty_roundtrip_and_populated_downgrade_refusal
tests/integration/phase2/test_b11_readiness_schema.py::test_catalog_and_empty_downgrade
tests/integration/phase2/test_b11_readiness_schema.py::test_downgrade_restores_live_0053_function_definitions
tests/integration/phase2/test_b11_readiness_schema.py::test_populated_release_upgrade_and_permissible_downgrade_preserve_history
tests/integration/phase2/test_b13_grant_schema.py::test_empty_slice_roundtrip_preserves_populated_predecessor
tests/integration/phase2/test_b13_grant_schema.py::test_stale_hardening_downgrade_restores_exact_0067_body
tests/integration/phase2/test_b14_ready_schema.py::test_forward_empty_catalog_and_exact_downgrade
tests/integration/phase2/test_b14a_entry_schema.py::test_corrupt_legacy_history_aborts_forward_upgrade_without_repair
tests/integration/phase2/test_b14a_entry_schema.py::test_fresh_upgrade_catalog_and_empty_downgrade
tests/integration/phase2/test_b14a_entry_schema.py::test_populated_creation_and_b04_seal_survive_forward_roundtrip
tests/integration/phase2/test_b15_package_schema.py::test_clean_upgrade_catalog_and_empty_downgrade
tests/integration/phase2/test_b16_schema.py::test_catalog_and_root_upgrade_downgrade_preserve_hashes
tests/integration/phase2/test_b16_schema.py::test_roundtrip_restores_exact_0060_function_catalog
tests/integration/phase2/test_b17_freeze_schema.py::test_clean_upgrade_roundtrip_preserves_predecessor_catalog
tests/integration/phase2/test_b17_freeze_schema.py::test_populated_prepared_upgrade_and_frozen_downgrade_refusal
tests/integration/phase2/test_b19_close_prior_art_schema.py::test_empty_downgrade_restores_exact_parent_catalog
tests/integration/phase2/test_b19_close_prior_art_schema.py::test_populated_v1_upgrade_preserves_hash_and_v2_refuses_downgrade
tests/integration/phase2/test_b19_close_prior_art_schema.py::test_preflight_refuses_broken_v1_capture_closure
tests/integration/phase2/test_b20_screening_schema.py::test_empty_downgrade_restores_check_trigger_and_functions
tests/integration/phase2/test_b20_screening_schema.py::test_populated_old_shape_upgrade_preserves_hash
tests/integration/phase2/test_b20_screening_schema.py::test_preflight_rejects_changed_sibling_definition
tests/integration/phase2/test_b21_capture_schema.py::test_catalog_and_owned_downgrade
tests/integration/phase2/test_b21_capture_schema.py::test_populated_v1_upgrade_preserves_hash_nested_ref_and_replay
tests/integration/phase2/test_b21_capture_schema.py::test_unexpected_baseline_refuses_upgrade
tests/integration/phase2/test_b22_prior_art_schema.py::test_catalog_populated_v1_upgrade_and_v2_downgrade_refusal
tests/integration/phase2/test_b22_prior_art_schema.py::test_preflight_rejects_unexpected_shared_guard
tests/integration/phase2/test_b23_novelty_review.py::test_legacy_null_capture_and_new_zero_capture_stay_distinct
tests/integration/phase2/test_b23_schema.py::test_catalog_and_empty_roundtrip
tests/integration/phase2/test_b23_schema.py::test_normal_role_late_issue_and_disposition_denied
tests/integration/phase2/test_b23_schema.py::test_pinned_guard_definitions_restore_byte_for_byte
tests/integration/phase2/test_b23_schema.py::test_populated_v1_upgrade_preserves_hashes_and_children
tests/integration/phase2/test_batch_c_migration.py::test_batch_c_empty_database_roundtrip
tests/integration/phase2/test_batch_g_integration.py::test_each_downgrade_restores_exact_predecessor_catalog
tests/integration/phase2/test_m1_schema.py::test_m1_downgrade_refuses_successor_history
tests/integration/phase2/test_m1_schema.py::test_m1_upgrade_downgrade_catalog_preserves_predecessor_functions
tests/integration/phase2/test_m1_schema.py::test_m1_upgrade_duplicate_draft_preflight_does_not_delete
tests/integration/phase2/test_m2_metadata.py::test_empty_m2_migration_roundtrip
tests/integration/phase2/test_m3_p1r1.py::test_0031_upgrade_accepts_valid_0030_empty_snapshot_and_formal_read
tests/integration/phase2/test_m3_p1r1.py::test_0031_upgrade_refuses_preexisting_gap
tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py::test_pr2_03_upgrade_from_0022_and_empty_downgrade
tests/integration/phase2/test_pr2_03_review_guards.py::test_remediation_child_upgrade_empty_downgrade_and_unique_head
tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_historical_migration_bytes_match_frozen_accepted_tree
tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta
tests/integration/phase2/test_pr2_13_citation_placement.py::test_citation_placement_persists_as_citation_only
tests/integration/phase2/test_pr2_13_citation_rebinding.py::test_forward_guard_preserves_rows_and_downgrade_refuses_history
tests/integration/phase2/test_pr2_14_internal_review.py::test_empty_migration_downgrade_drops_only_new_review_objects
tests/integration/phase2/test_pr2_14_internal_review.py::test_independent_frozen_claim_review_and_issue_are_immutable
tests/integration/phase2/test_pr2_15_decision_schema.py::test_0042_downgrade_refuses_committed_history_without_loss
tests/integration/phase2/test_pr2_15_decision_schema.py::test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables
tests/integration/phase2/test_pr2_17_authorship_schema.py::test_install_upgrade_exact_catalog_and_one_head
tests/integration/phase2/test_pr2_17_authorship_schema.py::test_nonempty_downgrade_refuses
tests/integration/phase2/test_pr2_18_schema.py::test_catalog_and_empty_downgrade
tests/integration/phase2/test_pr2_20_migrations.py::test_empty_install_noop_reconnect_and_permitted_empty_round_trip
tests/integration/phase2/test_pr2_20_migrations.py::test_owning_populated_downgrade_refusal_without_history_loss
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_approval_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_authorship_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_consumption_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_disposition_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_manuscript_checkpoints_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_novelty_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_package_freeze_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_ready_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_resolution_checkpoint_hash_parity
tests/integration/phase2/test_pr2_20_migrations.py::test_populated_revision_checkpoint_hash_parity
tests/integration/phase2/test_revision_action.py::test_catalog_immutable_sql_and_refused_downgrade
tests/integration/phase2/test_revision_action.py::test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog
tests/integration/phase2/test_revision_action.py::test_h2_populated_0044_0051_0052_head_upgrade_reconnect
tests/integration/phase2/test_task12_schema_migration.py::test_downgrade_restricts_unexpected_dependents_without_partial_ddl
EOF
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra --tb=short $(cat /private/tmp/researchbase-pr300-final-pg-selectors.txt) > /private/tmp/researchbase-pr300-final-pg-output.txt 2>&1
```

Observed: **98 passed, 0 failed, 0 skipped, 444 warnings in 111.83s**, exit 0.
The 88 function selectors expand to 98 parametrized cases. This final selection
includes every failure from the earlier 352-case diagnostic run. The inherited
Alembic deprecation accounts for the warnings.

The preceding narrowed rerun also passed: **79 passed, 0 failed, 0 skipped,
354 warnings in 84.37s**, exit 0. Its exact command was:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run pytest -o addopts='' -ra --tb=short $(cat /private/tmp/researchbase-pr300-pg-selectors.txt) > /private/tmp/researchbase-pr300-pg-output.txt 2>&1
```

That temporary selector file held the 70 changed test functions from the final
list above, before adding the diagnostic failures. The 98-case final run
supersedes it; the fully enumerated final selection is the reproducible record.

Earlier diagnostic runs are not passing evidence: the initial architecture /
bootstrap command from README produced 331 passed + 2 failed (stale head-parent
pins); the expanded combined command produced 361 passed + 1 failed (another
head-parent pin). An initial 17-file Phase 2 migration run produced 319 passed +
33 failed; a subsequent 70-selector run produced 62 passed + 17 failed. The
failures exposed historical test fixtures still selecting moving `head`, and a
historical M2 revision assertion. A one-test B01 reproducer also failed before
its fixture upper bound was pinned. These are corrected using explicit accepted
Phase 2 revision values, with the new forward-only production behavior retained.
Initial lint/format attempts also identified formatting/import ordering issues;
the final checks above are the passing runs.

Scope review observed 77 accepted historical migration files byte-identical to
HEAD, 16 zero-byte new markers, zero changed Status lines, and unchanged
AGENTS.md, pyproject.toml and uv.lock. Governing architecture/proposal/harness
files are unchanged. No commit, push or branch operation was performed.

The initial implementation did **not** run the whole suite or Phase 1/2 exit
suites as a whole. The subsequent reviewer reported three full-suite failures,
so the focused 98-case result above did not establish full-suite compatibility.
Review remediation and its separately authorized full check are recorded below.
No independent review PASS or Phase 3 exit is claimed. **STOP after PR3-00.**

## Review remediation

The reviewer identified three historical downgrade tests still starting at the
moving head. The coordination fixture, PR17D downgrade setup and P1-FCR3 round-trip
fixture now start at `0075_m1_reconsideration`. Coordination's installed-revision
assertions name that same accepted revision. P1-FCR3's separate head fixture and
its final re-upgrade still exercise the actual repository head.

The historical head pins change coverage: affected Phase 1/2 downgrade and
round-trip tests no longer upgrade to or downgrade from the actual current head;
they exercise the accepted Phase 2 lineage ending at 0075. This goes beyond a
cosmetic value update. Current-head clean upgrade, populated upgrade, single-head
and forward-only refusal coverage comes from the six PR3-00 PostgreSQL tests;
other upgrade-only tests continue to use the actual head.

PR2-20 now uses the explicit `PHASE2_HEAD` constant for the historical target,
instead of `scripts[-2]`. The unrelated current-head lookup and its import were
removed from the historical M2 round-trip test. The Phase 3 bootstrap file was
inspected through its end: both populated test functions have complete `finally`
blocks, and their setup engines are disposed there.

The requested audit was run before and after the fixes:

```sh
grep -rn "downgrade\|\"head\"\|'head'" tests/ | grep -v 0075
```

Its remaining source matches were inspected. They include upgrade-only current
head checks, historical downgrade targets below 0075, the intentionally refused
PR3-00 downgrades, test definitions/strings and bytecode-cache matches. In
particular, PR11R2 starts with a fresh database per test and restores head only
in teardown; the enum migration test downgrades its historical fixture before
upgrading to head; P1-FCR3 uses a separate 0075 round-trip fixture. No additional
required pin was found in this audit.

Focused remediation command (with the same UV_CACHE_DIR and PostgreSQL PATH
exports shown above):

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_15_coordination.py::test_catalog_and_downgrade_refuses_to_remove_history_guarantees tests/integration/test_pr17dr_migration.py::test_downgrade_removes_all_pr17d_owned_objects tests/integration/test_p1_fcr3_current_pointer.py::test_downgrade_removes_only_p1_fcr3_objects
```

Observed: **3 passed, 0 failed, 0 skipped, 4 warnings in 4.19s**, exit 0.

The exact requested check was attempted:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Observed: pyright 0 errors/warnings/informations; formatter 817 files already
formatted; Ruff all checks passed; `git diff --check HEAD` exit 0. The runner
skipped its quick pre-check because 60 changed test files exceeds its 25-file
threshold, then waited at shared lock acquisition before launching any shards.
Both shared locks were absent. A direct diagnostic confirmed:

```text
mkdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
```

The sandbox permits writes only in this repository and temporary directories.
The runner hardcodes its shared locks under `.pipeline/logs` and also writes
`.pipeline/test_durations.json`; neither is writable here. The waiting invocation
was interrupted (exit 130). The exact six-shard check is therefore **blocked,
not PASS**. No governing harness file or lock was changed to bypass this limit.

A serial full-suite run on a fresh disposable PostgreSQL 18 database was started
as additional verification, using the existing disposable helper, upgrading its
random database to head, then executing:

```sh
uv run pytest -o addopts= -q -rfE -p no:cacheprovider --junitxml=/private/tmp/researchbase-pr300-review-full-junit.xml tests
```

The temporary wrapper redirects output to
`/private/tmp/researchbase-pr300-review-full-output.txt` and drops the database
on completion. Its entry command is:

```sh
uv run python /private/tmp/researchbase-pr300-review-full.py
```

The serial fallback was interrupted (exit 130) before a pytest summary was
produced; the wrapper confirmed its disposable database was dropped. It is not
full-suite passing evidence and does not satisfy the requested six-shard gate.
The original runner's external write restriction remains unresolved in this
sandbox. Final focused module verification is recorded below.

Final focused verification covered the three affected modules in full, the
PR2-20/M2 changes and the complete PR3-00 PostgreSQL suite:

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_15_coordination.py tests/integration/test_pr17dr_migration.py tests/integration/test_p1_fcr3_current_pointer.py tests/integration/phase2/test_pr2_20_migrations.py::test_empty_install_noop_reconnect_and_permitted_empty_round_trip tests/integration/phase2/test_m2_metadata.py::test_empty_m2_migration_roundtrip tests/integration/phase3/test_pr3_00_bootstrap.py
```

Observed: **69 passed, 0 failed, 0 skipped, 71 warnings in 26.64s**, exit 0.
Warnings are the inherited Alembic `path_separator` deprecation. Static checks
were rerun after recording this evidence:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD
```

Observed: pyright **0 errors, 0 warnings, 0 informations**; formatter **817 files
already formatted**; Ruff **all checks passed**; whitespace check **no output**;
combined exit 0. Full six-shard gate: **blocked**, not PASS. The source fixes and
focused verification are complete; the exact runner needs an environment with
write access to its existing external output paths. No Status line, governing
harness file, runtime dependency or production behavior was changed during
remediation. No commit, push or branch operation was performed. **STOP at PR3-00.**
