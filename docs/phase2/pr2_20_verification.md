# PR2-20 focused verification

Subject `1ae0036344c26057b1e70c7bbd3daf4e5d3b2d51`; authored dirty diff `f01f97fc03bf5cff9f3bfccfce2d46e7d2ef6121b0e820b363c8f6f8d336e47e`. Generated reports/evidence are excluded from their own digest.

[Machine commands and logs](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/verification.json). The verifier never runs the whole suite. Static checks have no pytest counts. Skipped large cases are BLOCKED timing evidence, not passes.

| Command | Exit | Passed | Failed | Errors | Skipped |
| --- | --- | --- | --- | --- | --- |
| `uv sync --locked --group dev` | 0 | — | — | — | — |
| `uv run ruff check .` | 0 | — | — | — | — |
| `uv run ruff format --check .` | 0 | — | — | — | — |
| `uv run pyright` | 0 | — | — | — | — |
| `uv run alembic heads` | 0 | — | — | — | — |
| `uv run pytest tests/unit tests/architecture --junitxml tmp/pr220-verification/unit-architecture.xml` | 0 | 2156 | 0 | 0 | 0 |
| `uv run pytest tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_security.py tests/e2e/test_pr2_20_benchmark.py --junitxml tmp/pr220-verification/changed-postgres.xml` | 0 | 48 | 0 | 0 | 48 |
| `uv run pytest tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_19_citation_trace.py --junitxml tmp/pr220-verification/owning-postgres.xml` | 0 | 81 | 0 | 0 | 0 |
| `uv run pytest tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py --junitxml tmp/pr220-verification/phase1-golden.xml` | 0 | 20 | 0 | 0 | 0 |
| `RB_PR220_BENCHMARK=1 uv run pytest tests/e2e/test_pr2_20_benchmark.py --junitxml tmp/pr220-verification/large-benchmark.xml` | 0 | 3 | 0 | 0 | 48 |

Independent read-only review found subject exclusion, false exit-PASS, raw secret-validation and benchmark-attribution defects during authoring. Those were corrected and covered by focused tests. Follow-up read-only review confirmed those fixes and found no remaining semantic P0/P1 in that scope; a missing test import was corrected before this run. No reviewer or owner exit acceptance is inferred from this log. The existing transport destination finding remains P1 and prevents exit success. Host/profile prerequisites and real PaperQA2 intake remain BLOCKED. Owner dispositions for inherited contracts are not attached. STOP; wait for explicit Phase 3 GO.

Additional focused PostgreSQL expiry evidence: `uv run pytest -s tests/integration/phase2/test_pr2_19_races.py::test_cross_expiry_five_database_timestamps --junitxml tmp/pr220-verification/five-timestamps.xml` — exit 0; **1 passed, 0 failed, 0 errors, 0 skipped**. The [raw database timestamps](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/five-timestamps.txt) and [command record](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/five-timestamps.json) retain the five witnessed times and zero protected effects.

## B31-S3 part A review follow-ups

For the S3 worker profiles, real-wait evidence exists only for `workers == 4`:
`_s3_contend` witnesses blocked backends through `pg_locks` before releasing the
holder. `workers == 1` is the uncontended baseline and supplies no real-wait evidence.
S3 benchmark timing alone does not prove a backend wait. The saved S3 profile records
only worker counts completed in the current pytest session.

Focused follow-up verification (2026-10-20; all `uv` commands use
`UV_CACHE_DIR=.uv-cache`):

- `uv run ruff check .`: all checks passed.
- `uv run ruff format --check .`: 783 files already formatted.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- `uv run pytest tests/unit tests/architecture -q`: exit 0; 6,183 passed.
  The double-quiet output suppresses totals; a matching `--collect-only` run
  confirmed 6,183 collected, with no skips or failures in the completed run.
- `uv run pytest tests/e2e/test_pr2_20_benchmark.py::test_s3_prior_art_selection_profile -o addopts='' -q`:
  6 passed, 0 failed, 0 skipped.
- `uv run pytest 'tests/e2e/test_pr2_20_benchmark.py::test_s3_prior_art_selection_profile[EMPTY-1]' -o addopts='' -q --basetemp=tmp/s3-review-single`:
  1 passed; saved JSON asserted `concurrency_profiles == [1]`.
- `uv run pytest 'tests/e2e/test_pr2_20_benchmark.py::test_s3_prior_art_selection_profile[EMPTY-1]' 'tests/e2e/test_pr2_20_benchmark.py::test_s3_prior_art_selection_profile[EMPTY-4]' -o addopts='' -q --basetemp=tmp/s3-review-both`:
  2 passed; saved JSON asserted `[1]` then `[1, 4]` in that session.
  Initial runs with these explicit basetemps had 1 and 2 setup errors because the
  parent `tmp/` directory was absent; the results above followed its creation.
- `uv run pytest 'tests/integration/phase2/test_pr2_18_concurrency.py::test_expiry_across_required_database_wait[credential-request-coverage]' 'tests/integration/phase2/test_pr2_18_concurrency.py::test_expiry_across_required_database_wait[role-foreign_key-prior_art]' tests/integration/phase2/test_b19_close_prior_art_concurrency.py::test_post_claim_wait_credential_expiry tests/integration/phase2/test_b17_package_freeze.py::test_consumed_grant_cannot_freeze_a_fresh_package -q`:
  exit 0; all 4 selected tests passed.
- `uv run pytest tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_novelty.py -q`:
  exit 0; 113 passed, 2 skipped, 0 failed, 0 errors. Matching collection confirmed
  75 governance + 40 novelty cases; the two skips are the existing
  `test_s3_superseded_manuscript_freeze_trace_race` cases (`pending M1-S1`).
  Double-quiet output suppressed totals; the completed run reported two skips
  and no failures/errors across the 115 collected cases.

No whole-suite run, source/migration edits, commits, pushes, or branch creation.
