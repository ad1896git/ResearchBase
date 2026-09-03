# Baseline Regression Report

The explicit PostgreSQL PR-09 through PR-16 bundle passed:

`124 passed in 18.20s`

The full repository pytest run reached 100% with no failures. Two opt-in PR11R2 migration-matrix tests were
skipped because `PR11R2_MIGRATION_DB_URL` was not set; all required current-head PostgreSQL integration tests
ran. The separate PR-17 E2E suite passed `16 passed`.
