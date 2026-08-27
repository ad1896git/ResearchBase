# Commands and results

- `uv run pytest -q` with real PostgreSQL: PASS, 304 passed.
- PR-09/PR-09R application and schema tests: PASS, 15 passed.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors, 0 warnings, 0 informations.
- PR-09/PR-09R-owned `uv run ruff format --check ...`: PASS, 15 Python files.
- Repository-wide `uv run ruff format --check .`: FAIL on 8 inherited baseline files; no PR-09R-owned file is among them.
- `uv run alembic current`: PASS, `0009_run_input_seal_fix (head)`.
- PostgreSQL version query: PASS, 18.6.
- Disposable empty upgrade and `0009 -> 0008 -> 0009`: PASS.
- No SQLite was used for persistence/constraint/migration verification.
