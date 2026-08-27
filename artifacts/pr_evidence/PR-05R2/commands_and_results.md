# Commands and results

- `uv run pytest tests/unit/domain/test_pr05_experiment.py -k 'material_payload_is_explicit or each_material_field_changes or each_excluded_version_field or status_is_excluded or frozen_at_is_excluded or identity_current_pointer or identity_hypothesis_link'` → `19 passed, 10 deselected`.
- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `193 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `47 passed, 138 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- `uv run pytest tests/unit/domain/test_pr05_experiment.py` → `29 passed`.
- PostgreSQL health check → `True`.
- `uv run alembic current` → `0004_experiment_spec (head)`.
- No migration/schema code changed; no migration roundtrip repeated per pack.
