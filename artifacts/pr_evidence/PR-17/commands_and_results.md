# Commands and Results

This active report is corrected by PR-17R. The exact final remediation commands and results are in
`artifacts/pr_evidence/PR-17R/commands_and_results.md`.

- Reviewed PR-17 baseline: `03ccba54b8c983815f74d08a2390e0dfa45f8551`.
- PR-17R subject HEAD: `2d8e2abe31d0410717412c182d3cf7bd0811cced`.
- Evidence metadata is created after the subject commit and does not require its own SHA.
- Corrected E2E and architecture selection: `66 passed in 29.14s` on PostgreSQL 18.6.
- Explicit PR-09..PR-16 baseline bundle: `154 passed, 2 skipped, 0 failed` from 156 collected.
- Full pytest: `642 passed, 2 skipped, 0 failed in 56.56s`; the two opt-in PR11R2 migration-matrix skips occurred because
  `PR11R2_MIGRATION_DB_URL` was unset.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors/warnings/informations.
- Owned format check: PASS.
- Repository format check: the same eight unchanged inherited historical P3 files.
- `git diff --check`: PASS.
- PostgreSQL `uv run alembic current`: `0015_governance_audit (head)`.
- Every E2E fixture applies a fresh isolated-schema `alembic upgrade head` before running GSAS-01.
- No new dependency, source module, route, command, model, or migration appears in the PR-17R subject changed-file list.
