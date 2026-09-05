# Baseline Regression Report

This active report is corrected by PR-17R. The prior PR-17 replay record was incomplete and its count is
superseded by the exact reproducible bundle recorded in
`artifacts/pr_evidence/PR-17R/baseline_regression_report.md`.

The explicit PostgreSQL PR-09 through PR-16 baseline bundle was replayed with 156 selected tests:

`154 passed, 2 skipped, 0 failed`

The two skips are the opt-in PR11R2 migration-matrix tests because `PR11R2_MIGRATION_DB_URL` was not set.
The PR-17R E2E and architecture selection passed `66 passed` on PostgreSQL 18.6.
