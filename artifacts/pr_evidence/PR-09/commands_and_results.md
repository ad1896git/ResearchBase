# Commands and results

- PR-09 baseline `uv run pytest -q` with real PostgreSQL: PASS, 300 tests; coverage limitations are reconciled by PR-09R.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors, 0 warnings, 0 informations.
- PR-09-owned `uv run ruff format --check ...`: PASS, 14 Python files (ownership count corrected by PR-09R).
- Repository-wide `uv run ruff format --check .`: FAIL on 8 inherited baseline files; recorded separately.
- PR-09 baseline `uv run alembic current`: PASS, `0008_run_core (head)`; PR-09R advances the final head to `0009_run_input_seal_fix`.
- PostgreSQL version query: PASS, 18.6.
- Disposable empty upgrade and `0008 -> 0007 -> 0008`: PASS.
- PR-09 baseline PostgreSQL application/schema tests: PASS, 11 tests; PR-09R adds the hardening matrix.
