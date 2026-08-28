# PR-10R commands and results

Baseline and range:

    git rev-parse HEAD at PR-10R start: 41a886344f277e84c7d63891c5b4351262329e30
    remediation commit: 35efe3d test: harden PR-10 remediation proof
    remediation commit: 9c5a87a test: remove production builder from hash oracle
    git diff --name-only 41a8863..9c5a87a: exactly two test files

Fresh verification at the reviewed implementation head:

    DATABASE_URL=... uv run pytest
    356 passed

    DATABASE_URL=... uv run pytest tests/integration/test_pr10_schema.py tests/integration/test_pr10_application.py
    20 passed

    DATABASE_URL=... uv run pytest tests/unit/domain/test_pr10_measurement.py
    17 passed

    uv run ruff check .
    All checks passed!

    uv run pyright
    0 errors, 0 warnings, 0 informations

    uv run ruff format --check tests/integration/test_pr10_application.py tests/unit/domain/test_pr10_measurement.py
    2 files already formatted

    DATABASE_URL=... uv run pytest tests/test_integration.py
    1 passed

    DATABASE_URL=... uv run alembic current
    0010_measurement (head)

Disposable PostgreSQL migration roundtrip:

    empty database -> alembic upgrade head: PASS
    0010_measurement -> alembic downgrade 0009_run_input_seal_fix: PASS
    0009_run_input_seal_fix -> alembic upgrade head: PASS
    final disposable current: 0010_measurement (head)

PostgreSQL health/version: Docker service healthy; PostgreSQL 18.6.

Repository-wide `uv run ruff format --check .` reports only eight inherited files
outside PR-10/PR-10R. This remains documented as an inherited formatting issue; the
owned PR-10R files pass their scoped formatting check.
