# Commands and results

Baseline:

    git rev-parse HEAD at PR-10 start:
    fe8027dfef4f585566a60f467f66fdd8116e0964

Implementation commits:

    1106702 feat: implement PR-10 measurements
    9e04277 fix: harden PR-10 measurement validation
    733972d test: format PR-10 hash contract coverage
    0661a58 test: complete PR-10 measurement attack matrix

PR-10R remediation commit:

    35efe3d test: harden PR-10 remediation proof

The original PR-10 evidence had three proof-quality gaps: its integration hash
oracle imported production code, its invalid-closure case monkeypatched the validator,
and its historical provenance case did not compare the complete persisted row. These
are reconciled in PR-10R; the original PR-10 implementation and migration remain
unchanged.

Fresh verification:

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

    uv run ruff format --check <PR-10-owned files>
    14 files already formatted

    uv run pytest tests/unit/domain/test_pr10_measurement.py tests/unit/test_pr10_contracts.py tests/architecture/test_import_boundaries.py tests/test_architecture.py
    41 passed

    DATABASE_URL=... uv run pytest tests/test_integration.py
    1 passed in 0.13s

    DATABASE_URL=... uv run alembic current
    0010_measurement (head)

Disposable migration verification: empty to 0010 PASS; 0010 to 0009 PASS;
0009 to 0010 PASS; final current 0010_measurement (head) PASS. PostgreSQL health and
connection smoke passed; PostgreSQL version was 18.6.

Repository-wide uv run ruff format --check .: FAIL on eight inherited non-PR-10
files, documented in formatting_gate_report.md.
