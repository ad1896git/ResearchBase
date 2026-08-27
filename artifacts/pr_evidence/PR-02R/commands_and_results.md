# PR-02R Commands and Results

## Baseline and scope

```text
git rev-parse HEAD before evidence: 1fbb4634066cbcd49454590609486dfcebeca30f
git merge-base --is-ancestor dd69bbf HEAD: PASS
git merge-base --is-ancestor 57a8d15 HEAD: PASS
git merge-base --is-ancestor 99e0888 HEAD: PASS
git diff --check: PASS
```

The working tree had only the expected user-provided execution packs and `.DS_Store` files
untracked; no baseline commit was amended or rewritten.

## TDD and targeted checks

```text
New literal dynamic-import tests before scanner change: 4 expected failures
tests/architecture/test_pr02_boundaries.py: 10 passed
tests/integration/test_pr02_transactions.py: 9 passed
```

## Fresh gates

```text
uv run pytest: 96 passed in 0.31s
uv run pytest -m integration: 16 passed, 80 deselected in 0.27s
uv run pytest tests/architecture tests/test_architecture.py: 26 passed in 0.02s
uv run ruff check .: All checks passed!
uv run pyright: 0 errors, 0 warnings, 0 informations
uv lock --check: Resolved 38 packages
uv run --locked ruff format --check .: 47 files already formatted
```

The integration suite used the real PostgreSQL connection; SQLite was not used.

## PostgreSQL and Alembic

```text
PostgreSQL: healthy postgres:18-alpine, PostgreSQL 18.6
Alembic current before round-trip: 0002_actor_project_workspace (head)
Alembic downgrade 0002 -> 0001: PASS
Alembic upgrade 0001 -> 0002: PASS
Alembic current after round-trip: 0002_actor_project_workspace (head)
```
