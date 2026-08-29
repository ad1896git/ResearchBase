# Commands and results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.
PostgreSQL commands used the real local PostgreSQL service at
`localhost:5432/researchbase`; the migration roundtrip used a separate named
disposable database.

## Baseline and Git

```text
git rev-parse HEAD
934e8690fc3f8459b1632e896f5c3be01abf8c1f

git diff --name-status 934e8690fc3f8459b1632e896f5c3be01abf8c1f..5093639
14 expected PR-11 implementation/test/migration paths
```

Implementation commit:

```text
5093639b7ebdfa205c0304aa9914603fb6f13d11 feat: implement PR-11 statistical results
```

The first evidence payload commit was:

```text
f4ccdf8c5f78f48cb6c5f295224bfe46bf68b6b0 docs: add PR-11 evidence package
```

The final Git-verification metadata follow-up remains within this same
evidence directory; its final HEAD is recorded by the completion report and is
not encoded as a self-referential value.

## Verification

```text
uv sync --locked
Resolved 38 packages in 1ms; Checked 34 packages in 0.68ms

DATABASE_URL=... uv run pytest
396 passed in 10.58s

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pytest tests/test_architecture.py tests/architecture
33 passed in 0.19s

uv run ruff format --check <PR-11-owned paths>
14 files already formatted

DATABASE_URL=... uv run pytest tests/integration/test_pr11_schema.py tests/integration/test_pr11_application.py
22 passed in 1.95s

DATABASE_URL=... uv run pytest tests/test_integration.py
1 passed in 0.13s

DATABASE_URL=... uv run alembic current
0011_statistical_result (head)

SELECT version(), current_database(), current_schema()
PostgreSQL 18.6 on aarch64-unknown-linux-musl, ...; researchbase; public
```

The required repository-wide formatting command was also run. It reported
eight pre-existing files outside PR-11 (`0004_experiment_spec.py`, PR-04,
PR-05, and PR-06 integration tests, and `tests/unit/domain/test_pr05_experiment.py`).
The PR-11-owned scoped check passed; no inherited file was reformatted.

## Migration verification

```text
temporary database: researchbase_pr11_disposable
clean base -> head: PASS
current: 0011_statistical_result (head)
0011 -> 0010_measurement: PASS
0010_measurement -> 0011_statistical_result: PASS
current: 0011_statistical_result (head)
temporary database dropped after verification
```

The atomicity test used SQLAlchemy execution events and fresh UoW rollback
verification; it did not use a boolean set after flush as proof.
