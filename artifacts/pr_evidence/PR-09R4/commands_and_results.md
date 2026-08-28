# Commands and results

Baseline: `0feba30`. R4 implementation/test commit: `8a57413`. R4 evidence
package commit: `044c72a`.

- `DATABASE_URL=... uv run pytest`: PASS — `315 passed in 3.32s`.
- targeted PR-09 application/schema/proof/import-boundary tests: PASS.
- concurrent finish winner-metadata test: PASS.
- concurrent start regression: PASS.
- attach-vs-start lock-boundary regressions: PASS.
- exact provenance/closure regressions: PASS.
- real SQL atomicity regression: PASS.
- stale concurrency matrix: PASS.
- sealed-input trigger and FK/RESTRICT regressions: PASS.
- `uv run ruff check .`: PASS — `All checks passed!`.
- `uv run pyright`: PASS — `0 errors, 0 warnings, 0 informations`.
- `uv run ruff format --check tests/integration/test_pr09_application.py`: PASS.
- `uv run ruff format --check .`: FAIL — 8 inherited baseline files; no R4-owned file is among them.
- PostgreSQL health: PASS — accepting connections.
- PostgreSQL version: PASS — `18.6`.
- persistent `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
- `git diff --name-status 9e1bb85..0feba30`: 2 files, both PR-09R3 evidence/reporting.
- `git diff --name-status 0feba30..8a57413`: 1 file, test-only.
- `git diff --name-status 0feba30..044c72a`: 21 files; 1 test and 20 evidence/reporting files.
- no SQLite was used.
