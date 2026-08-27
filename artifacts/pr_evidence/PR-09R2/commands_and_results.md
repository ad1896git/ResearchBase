# Commands and results

These are the historical PR-09R2 results. PR-09R3 fresh results are appended
below and are authoritative for the current remediation gate.

- `DATABASE_URL=... uv run pytest`: PASS — `312 passed in 3.06s`.
- `DATABASE_URL=... uv run pytest tests/integration/test_pr09_application.py tests/integration/test_pr09_schema.py tests/integration/test_pr09r2_proof.py -q`: PASS — `23 passed`.
- `uv run pytest tests/architecture tests/unit/domain/test_pr09_run.py tests/contracts -q`: PASS — `29 passed`.
- `uv run ruff check .`: PASS — `All checks passed!`.
- `uv run pyright`: PASS — `0 errors, 0 warnings, 0 informations`.
- `uv run ruff format --check tests/integration/test_pr09_application.py tests/integration/test_pr09r2_proof.py`: PASS — both files already formatted.
- `uv run ruff format --check .`: FAIL, truthfully — 8 inherited baseline files would be reformatted; 77 files already formatted. No PR-09R2-owned file is among them.
- PostgreSQL health/version query: PASS — `health True`, `version 18.6`.
- persistent `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
- disposable migration: PASS — empty database upgraded to `0009`, downgraded to `0008_run_core`, upgraded to `0009`, verified at head, then dropped.
- No SQLite was used for persistence, constraint, concurrency, or migration proof.

PR-09R3 fresh reruns:

- `DATABASE_URL=... uv run pytest`: PASS — `315 passed in 3.38s`.
- `DATABASE_URL=... uv run pytest tests/integration/test_pr09_application.py tests/integration/test_pr09_schema.py tests/integration/test_pr09r2_proof.py tests/architecture/test_import_boundaries.py -q`: PASS.
- `uv run ruff check .`: PASS — `All checks passed!`.
- `uv run pyright`: PASS — `0 errors, 0 warnings, 0 informations`.
- `uv run ruff format --check .`: FAIL, truthfully — the same 8 inherited baseline files would be reformatted; no PR-09R3-owned file is among them.
- scoped `uv run ruff format --check` for changed PR-09R3 Python files: PASS.
- PostgreSQL health/version: PASS — accepting connections, version `18.6`.
- persistent `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
- disposable migration: PASS — empty→`0009`, downgrade to `0008_run_core`, upgrade to `0009`, verified at head, then dropped.
- No SQLite was used.
