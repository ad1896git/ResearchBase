# Commands and Results

- starting `git rev-parse HEAD`: `ce94d738129fee584744c1a7e1eef8fd334ea225`; ending evidence SHA is resolved independently from Git.
- `git status --short`: pre-existing untracked repository/evidence files recorded and preserved.
- `git log --oneline --decorate -30`: baseline lineage inspected; no intervening commit.
- full `pytest -q -ra`: exit 0; two pre-existing optional disposable migration-matrix skips.
- PR-15 targeted PostgreSQL: 13 passed.
- PR-12–14 regression PostgreSQL: 61 passed.
- PR-09–11 regression PostgreSQL: 54 passed.
- `ruff check .`: pass.
- `pyright`: pass, 0 errors/warnings.
- `alembic current`: `0015_governance_audit (head)`.
- `ruff format --check .`: eight unchanged historical files remain; owned PR-15 files pass.
- `git diff --check`: pass.
