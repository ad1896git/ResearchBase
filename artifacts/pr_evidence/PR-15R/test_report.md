# Test Report

The committed PR-15R suite adds 54 collected tests: 44 route-family/transport cases, one exhaustive
35-route structural binding test, one mixed supplied-ID concurrency test, and expanded PostgreSQL
tests (ten integration tests total in `test_pr15_api.py`). Repository total: 596 collected.

Fresh full run against PostgreSQL: 594 passed, 2 skipped. Both skips are pre-existing optional
PR-11 disposable migration-matrix tests requiring `PR11R2_MIGRATION_DB_URL`.
