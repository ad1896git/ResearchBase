# Commands and results

All commands were run from the ResearchBase repository.

```text
DATABASE_URL=... uv run alembic upgrade head
PASS — main database upgraded to 0005_dataset_snapshot.

DATABASE_URL=... uv run pytest tests/integration/test_pr06_application.py tests/integration/test_pr06_schema.py
15 passed in 0.45s

DATABASE_URL=... uv run pytest
222 passed in 1.36s

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pytest tests/architecture tests/test_architecture.py tests/unit/domain/test_pr06_dataset.py
41 passed in 0.15s

DATABASE_URL=... uv run alembic current
0005_dataset_snapshot (head)

git diff --check
PASS — no whitespace errors.
```

The migration report records the separate disposable-database upgrade/downgrade/upgrade roundtrip.
