# Commands and results

- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `193 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `47 passed, 138 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- `uv run pytest tests/unit/domain/test_pr05_experiment.py` → `29 passed`.
- `uv run pytest tests/unit/domain/test_pr05_experiment.py -k 'material_payload_is_explicit or each_material_field_changes or each_excluded_version_field or status_is_excluded or frozen_at_is_excluded or identity_current_pointer or identity_hypothesis_link'` → `19 passed, 10 deselected`.
- PostgreSQL health check → `True`.
- `uv run alembic current` on persistent DB → `0004_experiment_spec (head)`.
- Disposable DB `researchbase_pr05r_20260827`: empty upgrade and `0004→0003→0004` roundtrip → PASS; DB removed.
- `git diff --check` → clean.

PR-05R3 added no production code, migration, schema, or persistence behavior; no migration roundtrip was required.
