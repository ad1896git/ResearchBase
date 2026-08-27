# Commands and results

- `uv run pytest -q` with real PostgreSQL: PASS, 283 passed.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors, 0 warnings.
- PR-08-owned `uv run ruff format --check ...`: PASS, 11 files.
- Repository-wide `uv run ruff format --check .`: FAIL on 8 inherited baseline files; recorded in `formatting_gate_report.md`.
- `uv run alembic current`: PASS, `0007_metric_definition (head)`.
- PostgreSQL version: PASS, PostgreSQL 18.6.
- Disposable empty→0007→0006→0007 roundtrip: PASS.
