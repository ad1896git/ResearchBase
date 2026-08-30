# Commands and results

Executed from the repository root with real PostgreSQL:

- Old-state reproduction in separate disposable database `researchbase_pr12r_oldstate_20260830`: Alembic upgrade to `0013_statistical_result_legacy_input_precheck` succeeded; `uv run alembic current` reported `0013_statistical_result_legacy_input_precheck`; `uv run pytest -q --tb=short tests/integration/test_pr12_schema.py` failed 3 tests because PR-12 claim tables were absent. This database was not the shared database and was not repaired as part of the required sequence.
- `PR11R2_MIGRATION_DB_URL=<disposable> uv run pytest -rA tests/integration/test_pr11r2_migration.py`: 2 passed, 1 warning.
- `<disposable> uv run alembic current`: `0014_claim_evidence (head)`.
- Immediately afterward, shared-DB PR-12 targeted suites: 66 passed in 1.71s.
- Full Run A with shared `DATABASE_URL` and disposable migration URL: 483 passed, 1 warning in 9.78s.
- Full Run C with the same two URLs, no repair: 483 passed, 1 warning in 9.56s.
- Shared `uv run alembic current` after Run A and Run C: `0014_claim_evidence (head)`.
- `uv run ruff check .`: `All checks passed!`
- `uv run pyright`: `0 errors, 0 warnings, 0 informations`.
- Scoped `uv run ruff format --check` over PR-12R-owned tests: 4 files already formatted.
- Repository-wide formatter: the same 8 inherited non-PR-12 files remain; no historical files were modified.
- `git diff --check`: PASS.
- `git diff -- src tests migrations`: empty after the remediation commit and throughout evidence generation.

No manual `alembic upgrade head` occurred between the migration subset, immediate targeted tests, Run A, or Run C. SQLite was not used.

## PR-12R2 reconciliation

- Migration subset: 2 passed, 1 existing Alembic warning in 3.89s.
- Shared and disposable `alembic current` immediately afterward: `0014_claim_evidence (head)`.
- PR-12 targeted immediately afterward: 75 passed in 1.83s.
- Full pytest Run A: 486 passed, 1 warning in 9.69s.
- Shared `alembic current` after Run A: `0014_claim_evidence (head)`.
- Full pytest Run B, without repair: 486 passed, 1 warning in 9.67s.
- Shared and disposable final revisions: `0014_claim_evidence (head)`.
- Oracle unit suite: 33 passed.
- Focused multi-input closure determinism test: 1 passed on real PostgreSQL.
- Architecture: 39 passed.
- Ruff: PASS. Pyright: 0 errors. PR-12R2-owned format: 4 files already formatted.
- Repository-wide format: the same 8 inherited files would be reformatted; 106 files already formatted.
- `git diff 3564361..HEAD -- src migrations`: empty.

No manual Alembic repair occurred anywhere in the R2 sequence. SQLite was not used.
