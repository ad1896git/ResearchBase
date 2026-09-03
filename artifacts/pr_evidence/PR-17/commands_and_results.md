# Commands and Results

- Starting HEAD: `0eed8d85f4009a4f5265a697476423b7cdaf8ea4`.
- Subject implementation/test HEAD: `745de1b0cb90e6f590fc28f2da1e0317809e3e5a`.
- Evidence metadata is created after the subject commit and does not require its own SHA.
- `uv run pytest -o addopts='' -q tests/e2e`: `18 passed in 23.73s` on PostgreSQL.
- Explicit PR-09..PR-16 bundle: `124 passed in 18.20s`.
- Architecture tests: `41 passed in 0.26s`.
- Full pytest: reached `100%` with no failures; 2 opt-in PR11R2 migration-matrix skips because
  `PR11R2_MIGRATION_DB_URL` was unset.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors/warnings/informations.
- Owned format check: PASS.
- Repository format check: the same eight unchanged inherited historical P3 files.
- `git diff --check`: PASS before evidence files.
- PostgreSQL `uv run alembic current`: `0015_governance_audit (head)`.
- Every E2E fixture applies a fresh isolated-schema `alembic upgrade head` before running GSAS-01.
- No new dependency, source module, route, command, model, or migration appears in the subject changed-file list.
