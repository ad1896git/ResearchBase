# Commands and results

- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest` -> `193 passed`.
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run ruff check .` -> `All checks passed!`.
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pyright` -> `0 errors, 0 warnings, 0 informations`.
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest tests/unit/domain/test_pr05_experiment.py -k 'material_payload_is_explicit or each_material_field_changes or each_excluded_version_field or status_is_excluded or frozen_at_is_excluded or identity_current_pointer or identity_hypothesis_link'` -> `19 passed, 10 deselected`.
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest tests/architecture tests/test_architecture.py` -> `27 passed`.
- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -m integration` -> `47 passed, 146 deselected`.
- PostgreSQL health check -> `True`.
- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic current` -> `0004_experiment_spec (head)`.
- `git diff --name-only 66c4f3d..0269e69` -> only `tests/unit/domain/test_pr05_experiment.py`.
- New migration -> `NONE`.

The initial sandboxed PostgreSQL attempt was blocked by the environment's network restriction; the same required checks were rerun with approved local PostgreSQL access and passed.
