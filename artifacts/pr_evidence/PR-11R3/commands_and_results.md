# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase`.
Database-backed commands used the real local PostgreSQL service; no SQLite
database, URL, or test path was used.

## Baseline and inventory

```text
git rev-parse HEAD before changes: e62d19f97c965003492648df84a220a25b3ebffa
git diff --name-only e62d19f..716e316: 15 paths
git diff --name-status e62d19f..716e316: 2 modified, 12 added, 1 modified test path
```

The PR-11R3 target-range inventory was regenerated with Git from
`e62d19f..716e316` and is set-equal to `changed_files.txt`. It includes the two
PR-11R2 evidence paths that were changed in that target range and excludes
older cumulative/pre-existing files. PR-11R3 added no `src/` or `migrations/`
path.

## Fresh verification commands

```text
uv run pytest
uv run ruff check .
uv run pyright
uv run ruff format --check .
uv run ruff format --check tests/integration/test_pr11r2_migration.py
uv run pytest tests/integration/test_pr11r2_migration.py -q
uv run pytest tests/unit/test_pr11_contracts.py tests/unit/domain/test_pr11_statistical_result.py tests/integration/test_pr11_application.py tests/integration/test_pr11_schema.py tests/integration/test_pr11r2_migration.py tests/architecture/test_import_boundaries.py tests/test_architecture.py -q
uv run pytest tests/test_integration.py -q
uv run alembic current
uv run alembic downgrade 0012
uv run alembic upgrade 0013_statistical_result_legacy_input_precheck
```

## Observed results

```text
full pytest: 410 passed in 15.41s
Ruff: All checks passed!
Pyright: 0 errors, 0 warnings, 0 informations
repository format: 8 files would be reformatted; 92 already formatted
owned migration-test format: 1 file already formatted
architecture tests: passed
PR-11R3 migration matrix: 2 passed
focused PR-11/PR-11R/PR-11R2/architecture regression: passed
PostgreSQL health smoke: 1 passed
PostgreSQL server: 18.6
Alembic current: 0013_statistical_result_legacy_input_precheck (head)
persistent roundtrip: downgrade to 0012 passed; upgrade to 0013 passed
```

The repository-wide formatting debt is inherited and remains outside the
PR-11R3 change set. The scoped owned-file format check passed.
