# Commands and results

Fresh PR-06R verification commands:

```text
DATABASE_URL=... uv run pytest tests/integration/test_pr06_application.py tests/integration/test_pr06_schema.py
27 passed in 0.69s

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pytest tests/unit/domain/test_pr06_dataset.py tests/architecture tests/test_architecture.py
41 passed in 0.17s
```

The final full suite and migration/health results will be recorded here after the final fresh gates. Baseline: `c92f119`; no new migration is expected.

Final fresh gate results:

```text
DATABASE_URL=... uv run pytest
234 passed in 1.60s

DATABASE_URL=... uv run pytest tests/integration/test_pr06_application.py tests/integration/test_pr06_schema.py
27 passed in 0.69s

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pytest tests/unit/domain/test_pr06_dataset.py tests/architecture tests/test_architecture.py
41 passed in 0.17s

PostgreSQL health/version
PostgreSQL 18.6 on aarch64-unknown-linux-musl

DATABASE_URL=... uv run alembic current
0005_dataset_snapshot (head)

Disposable migration roundtrip
0005 upgrade: PASS; downgrade to 0004: PASS; upgrade to 0005: PASS;
final current: 0005_dataset_snapshot (head); disposable database removed.

New migration: NONE.
```
