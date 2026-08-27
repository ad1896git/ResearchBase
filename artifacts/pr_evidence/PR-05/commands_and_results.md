# Commands and results

- `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` → `171 passed`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`.
- `DATABASE_URL=... uv run pytest -m integration` → `43 passed, 128 deselected`.
- `uv run pytest tests/architecture tests/test_architecture.py` → `27 passed`.
- `uv run alembic current` → `0004_experiment_spec (head)`.
- `uv run alembic downgrade 0003_research_question_hypothesis && uv run alembic upgrade head` → successful transactional downgrade/upgrade.
- `git diff --check eda94d650a66bc693a21a2948200aae60ee357d7..f11f3eec619daaff0761bd1911e3f29aab838330` → clean.
