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
