# Commands and results

- `uv run pytest -q` with real PostgreSQL: PASS, 300 tests.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors, 0 warnings, 0 informations.
- PR-09-owned `uv run ruff format --check ...`: PASS, 13 files.
- Repository-wide `uv run ruff format --check .`: FAIL on 8 inherited baseline files; recorded separately.
- `uv run alembic current`: PASS, `0008_run_core (head)`.
- PostgreSQL version query: PASS, 18.6.
- Disposable empty upgrade and `0008 -> 0007 -> 0008`: PASS.
- PR-09 PostgreSQL application/schema tests: PASS, 11 tests.
