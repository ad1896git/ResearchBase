# Commands and results (reconciled by PR-05R)

- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `182 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `47 passed, 135 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- Disposable PostgreSQL `researchbase_pr05r_20260827`: empty upgrade, `0004→0003→0004`, and final head → PASS; database removed.
- Persistent `uv run alembic current` → `0004_experiment_spec (head)`.
- `git diff --check` → clean before evidence generation.
