# Commands and results

- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `182 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `47 passed, 135 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- `uv run pytest tests/unit/domain/test_pr05_experiment.py` → `18 passed`.
- `uv run alembic current` on persistent DB → `0004_experiment_spec (head)`.
- Disposable DB `researchbase_pr05r_20260827`: empty upgrade and `0004→0003→0004` roundtrip → PASS; DB removed.
- `git diff --check` → clean.
