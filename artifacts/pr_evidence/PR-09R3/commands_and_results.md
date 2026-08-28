# Commands and results

All results below were run fresh from baseline `9c47381` plus implementation
commit `197bd2d`, against the persistent local PostgreSQL 18.6 service unless
marked disposable.

- `DATABASE_URL=... uv run pytest`: PASS — `315 passed in 3.38s`.
- targeted PR-09 application/schema/proof and import-boundary tests: PASS.
- `DATABASE_URL=... uv run pytest tests/integration/test_pr09r2_proof.py -q`: PASS — 11 tests.
- `uv run ruff check .`: PASS — `All checks passed!`.
- `uv run pyright`: PASS — `0 errors, 0 warnings, 0 informations`.
- `uv run ruff format --check .`: FAIL — 8 inherited baseline files; see `formatting_ownership_report.md`.
- scoped `uv run ruff format --check` for changed/owned Python files: PASS.
- PostgreSQL health: PASS — accepting connections.
- PostgreSQL version: PASS — `18.6`.
- persistent `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
- disposable empty→head: PASS.
- disposable downgrade `0009_run_input_seal_fix`→`0008_run_core`: PASS.
- disposable upgrade `0008_run_core`→`0009_run_input_seal_fix`: PASS; current is head.
- disposable database was dropped after the roundtrip.
- No SQLite was used for persistence, constraints, concurrency, or migration proof.

PR-09R4 fresh reruns:

- `DATABASE_URL=... uv run pytest`: PASS — `315 passed in 3.32s`.
- targeted PR-09 application/schema/R2 proof/import-boundary set: PASS.
- concurrent-finish winner metadata test: PASS.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS.
- owned format check: PASS.
- repository format: same 8 inherited baseline failures, reported and not modified.
- PostgreSQL health/version: PASS — accepting connections, version `18.6`.
- persistent `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
