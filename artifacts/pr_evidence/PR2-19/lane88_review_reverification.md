# Lane 88 review reverification — 2026-10-21

Base commit: `286cd9ae985dcad91d3e225b4b50c5c46fadeef5`.

The earlier sharded result (2 failed, 3 errors) remains a failed run. No shared
database/infrastructure cause has been established. The focused reruns below
passed on the unchanged implementation plus this lane's documentation/inventory
diff; no production fix or base-commit comparison was needed for those reruns.

## Reported failures: isolated rerun

The review omitted the repetition number of the temporal test. All five
repetitions were therefore included, giving nine cases for the five reported
test locations.

Exact command (exit 0):

```sh
UV_CACHE_DIR=/tmp/researchbase-lane88-uv uv run pytest \
  tests/integration/phase2/test_pr2_19_novelty.py::test_g7_selected_failed_and_zero_scope_is_disclosed \
  'tests/integration/phase2/test_pr2_04_temporal_phase_acceptance.py::test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry[1-credential_expiry-disclosure-execution]' \
  'tests/integration/phase2/test_pr2_04_temporal_phase_acceptance.py::test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry[2-credential_expiry-disclosure-execution]' \
  'tests/integration/phase2/test_pr2_04_temporal_phase_acceptance.py::test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry[3-credential_expiry-disclosure-execution]' \
  'tests/integration/phase2/test_pr2_04_temporal_phase_acceptance.py::test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry[4-credential_expiry-disclosure-execution]' \
  'tests/integration/phase2/test_pr2_04_temporal_phase_acceptance.py::test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry[5-credential_expiry-disclosure-execution]' \
  'tests/integration/phase2/test_b21_capture_schema.py::test_normal_sql_incomplete_capture_rolls_back[omitted]' \
  tests/integration/phase2/test_pr2_01_source_identity.py::test_receipt_failure_rolls_back_each_command_and_allows_same_key_retry \
  'tests/integration/phase2/test_pr2_04_schema_coverage.py::test_direct_insert_checks_lengths_and_missing_foreign_parents[search_result_records.content_hash-19]' \
  --tb=short
```

Observed: **9 passed, 9 warnings in 19.32s**.

## Named G7 Application evidence

```sh
UV_CACHE_DIR=/tmp/researchbase-lane88-uv uv run pytest -o addopts='' tests/integration/phase2/test_b20_screening_basis.py -k 'zero_hit_negative or exact_captured_verified_comparisons' -v
```

Exit 0. Verbose output explicitly reported PASSED for:

- `test_zero_hit_negative`
- `test_exact_captured_verified_comparisons[RELATED-NOT_CLOSE-True]`
- `test_exact_captured_verified_comparisons[CONTRASTING-NOT_CLOSE-True]`
- `test_exact_captured_verified_comparisons[PARTIAL_OVERLAP-UNCLEAR-False]`
- `test_exact_captured_verified_comparisons[UNCLEAR-UNCLEAR-False]`
- `test_exact_captured_verified_comparisons[IDENTICAL-CLOSE-False]`
- `test_exact_captured_verified_comparisons[HIGHLY_SIMILAR-CLOSE-False]`
- `test_exact_captured_verified_comparisons[RELATED-EXCLUDED-False]`

Observed: **8 passed, 9 deselected, 8 warnings in 9.90s**.

## README hunk

```diff
-repairing immutable history. STOP before Phase 3.
+repairing immutable history. Phase 2 is accepted; Phase 3 proceeds one explicitly
+authorized PR at a time.
```

There is no link in this hunk. The requested
`docs/phase2/phase2_acceptance_2026-10-20.md` is absent from this checkout.
The text reflects the user's explicit acceptance instruction.

## Required check chain: BLOCKED, not PASS

Executed with a writable uv cache (the default user cache is sandbox-denied):

```sh
export UV_CACHE_DIR=/tmp/researchbase-lane88-uv
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Observed before the blocker:

- Pyright: **0 errors, 0 warnings, 0 informations**.
- Ruff format: **798 files already formatted**.
- Ruff check: **All checks passed!**
- `git diff --check HEAD`: exit 0.
- Sharding script's changed-test precheck: **3 passed in 0.03s**.

The script then could not modify its shared mutex directory under
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs`, which is outside
this session's writable roots. Its output included:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
```

The blocked process was interrupted (exit 130); no shard pytest run started in
this attempt. The script also writes the shared `.pipeline/test_durations.json`
outside the writable roots. The governing script and shared coordination were
not changed. A full sharded run in an execution context permitted to use those
shared paths remains required. No full-check success is claimed.
