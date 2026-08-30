# Commands and results

- `uv run pytest -rA tests/integration/test_pr11r2_migration.py`: 2 passed, 1 warning in 3.89s.
- Shared/disposable `uv run alembic current` after migration subset: `0014_claim_evidence (head)`.
- PR-12 targeted suite: 75 passed in 1.83s.
- Full pytest Run A: 486 passed, 1 warning in 9.69s.
- Shared Alembic after Run A: `0014_claim_evidence (head)`.
- Full pytest Run B: 486 passed, 1 warning in 9.67s.
- Shared/disposable final Alembic: `0014_claim_evidence (head)`.
- `uv run pytest tests/unit/domain/test_pr12_claim.py`: 33 passed.
- Focused closure determinism: 1 passed on real PostgreSQL.
- `uv run ruff check .`: PASS.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- Architecture tests: 39 passed.
- PR-12R2-owned format: 4 files already formatted.
- Repository-wide format: 8 inherited files would reformat; 106 files already formatted.
- `git diff --check`: PASS.
- `git diff 3564361..HEAD -- src migrations`: empty.

No manual database repair occurred. SQLite was not used.

## PR-12R3 final-head reconciliation

- `git rev-parse 16228b9`: `16228b935c9c87053b97f574a2c57e4c181b372a`.
- `git rev-parse b973356`: `b973356f494bb75a2f324be8455a9f54934e9f5d`.
- `git diff --name-only 16228b9..b973356`: exactly 3 PR-12R2 evidence files.
- `git diff --name-status 16228b9..b973356`: exactly 3 modified (`M`) evidence files.
- `git diff --stat 16228b9..b973356`: 3 files changed, 14 insertions, 1 deletion.
- Final metadata range set equality: PASS.
- Source/test/migration files in the final metadata range: 0.

The evidence directly records the R2 reviewed and post-final current HEAD as `b973356f494bb75a2f324be8455a9f54934e9f5d`.
