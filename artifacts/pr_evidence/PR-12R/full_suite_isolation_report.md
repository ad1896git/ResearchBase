# Full-suite isolation report

## Previous failure mode

The reviewed PR-12 migration harness targeted the PR-11 head `0013_statistical_result_legacy_input_precheck`. When migration tests are directed at the shared integration database, that stale target leaves it below PR-12's `0014_claim_evidence` head; the following PR-12 schema/application tests then cannot be treated as a reproducible full-suite run.

This failure mode was independently reproduced in the isolated disposable database `researchbase_pr12r_oldstate_20260830`: `alembic current` reported `0013_statistical_result_legacy_input_precheck`, and the PR-12 schema probe failed all 3 tests because `claims` and `claim_versions` were absent. The reproduction database was separate from the shared database and was not used in the required remediation sequence.

## Remediation

`tests/integration/test_pr11r2_migration.py` now uses a dedicated `PR11R2_MIGRATION_DB_URL` database and an autouse module finalizer. The finalizer derives the current repository head from Alembic's `ScriptDirectory`, runs `upgrade` to that discovered head, and asserts `alembic current` reports it. The PR-11-specific `0013` target remains only the migration-under-test, not the cleanup target.

## Required sequence

- Migration subset: 2 passed, 1 Alembic deprecation warning.
- Immediately after migration subset, disposable database: `0014_claim_evidence (head)`.
- PR-12 targeted tests immediately afterward: 66 passed.
- Full-suite Run A: 483 passed, 1 warning, 9.78s.
- Full-suite Run C: 483 passed, 1 warning, 9.56s.
- Shared database after Run A and Run C: `0014_claim_evidence (head)`.
- Manual database repair between these stages: NO.
