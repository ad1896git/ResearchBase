# Commands and Results

- Starting HEAD: `912f564ff3f8a5e9d4be562f2ed5734eaeaed8f1`.
- Subject implementation/test HEAD: `fac2093` (final formatting fix follows implementation subject `77d2152`).
- `pytest -o addopts='' -q -ra`: `360 passed, 259 skipped` without `DATABASE_URL`; skips are PostgreSQL-gated tests.
- PR-16 targeted/unit/architecture: `20 passed`.
- PR-16 PostgreSQL CLI integration: `3 passed`.
- PR-09–PR-14 PostgreSQL regressions: `141 passed`.
- PR-15 HTTP/OpenAPI unit regression: `9 passed`.
- PR-15 PostgreSQL HTTP regression: `10 passed`.
- `ruff check .`: PASS.
- `pyright`: PASS, 0 errors/warnings.
- owned `ruff format --check`: PASS.
- repository `ruff format --check .`: the same eight unchanged historical P3 files as the accepted baseline.
- `git diff --check`: PASS before evidence files were added.
- PostgreSQL `alembic current`: `0015_governance_audit (head)`.
- PostgreSQL metadata/table comparison: 28 model tables, 28 database tables, unexpected tables 0, missing
  tables 0.
