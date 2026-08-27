# Commands and results

- `uv run pytest tests/unit/domain/test_pr05_experiment.py -k 'status_is_excluded or frozen_at_is_excluded or identity_current_pointer_is_excluded'` → `3 passed`.
- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `185 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `47 passed, 138 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- `uv run alembic current` → `0004_experiment_spec (head)`.
- No migration/schema code changed; no migration roundtrip repeated per pack.
