# Commands and results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.
Database-backed commands used PostgreSQL `18.6`; no SQLite path was used.

## Git and migration

```text
git status --short
git log --oneline --decorate -12
git diff 6675a744..HEAD
git diff --name-only 6675a744..HEAD
uv run alembic current
uv run alembic upgrade head
```

The implementation/test commits were resolved as
`1e557818d1a2baa3f1929a7c2eb3c8f20a9a64e5` and
`2304c081f668a01a7663624a271728431a9ba745`.

## Fresh verification commands and observations

```text
uv run pytest
uv run ruff check .
uv run pyright
uv run ruff format --check .
uv run pytest tests/integration/test_pr11r2_migration.py
uv run pytest tests/integration/test_pr11_application.py tests/integration/test_pr11_schema.py
uv run pytest tests/architecture/test_import_boundaries.py tests/test_architecture.py
```

Observed results:

```text
DATABASE_URL=... uv run pytest: 410 passed in 10.36s
DATABASE_URL=... PR11R2_MIGRATION_DB_URL=... uv run pytest: 410 passed in 10.36s
focused PR-11/PR-11R2/application/schema/architecture gates: 58 passed in 6.74s
PR-11 unit + focused architecture gates: 84 passed in 2.80s
architecture tests: 34 passed in 0.17s
PR11R2 migration matrix: 2 passed
uv run ruff check .: All checks passed!
uv run pyright: 0 errors, 0 warnings, 0 informations
PR-11R2-owned format: 3 files already formatted
repository-wide format: 8 pre-existing files would be reformatted; none is in the PR-11R2 change set
PostgreSQL health smoke: 1 passed in 0.13s
PostgreSQL: 18.6
alembic current: 0013_statistical_result_legacy_input_precheck (head)
development guard-state query: invalid_zero_input=0; tgdeferrable=true; tginitdeferred=true
```

The full suite was run with both database variables set, so all PostgreSQL
integration tests and the disposable migration matrix executed. No SQLite
path was used.
