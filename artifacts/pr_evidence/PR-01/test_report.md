# PR-01 Test Report

## Acceptance gate

- PR-00 baseline preserved: PASS; baseline checks passed before implementation and full regression passed after.
- Typed UUID ID contract: PASS.
- UUIDv7 generation contract: PASS; version, RFC variant, UUID type, and 1,000-generation non-collision test.
- UTC Clock contract: PASS.
- Naive datetime rejection: PASS.
- Deterministic canonical JSON for supported subset: PASS.
- Non-finite JSON rejection: PASS.
- SHA-256 primitives: PASS; known vector, raw bytes, and canonical JSON invariants.
- Normative `ErrorCode` values: PASS; all ten stable values tested.
- Minimal base enum convention: PASS; no later lifecycle/state machine behavior.
- `ExecutionContext`: PASS; required UUIDs, allowed caller types, validation, and immutability tested.
- Foundation caller/framework boundary: PASS.
- Architecture import-boundary tests: PASS.
- Business table added: PASS — none added.
- PR-02+ implementation: PASS — none detected.
- Phase 2+ implementation: PASS — none detected.
- Ruff: PASS.
- Pyright: PASS.
- pytest: PASS; 40 passed.
- Existing bootstrap/migration checks: PASS; PostgreSQL 18.6 healthy and Alembic head valid.
- Open P0: 0.
- Open P1: 0.

## Exact summaries

```text
Foundation + architecture tests: 31 passed
Full pytest with DATABASE_URL: 40 passed in 0.21s
Ruff format: 32 files already formatted
Ruff check: All checks passed!
Pyright: 0 errors, 0 warnings, 0 informations
PostgreSQL: 18.6, healthy
Alembic: 0001_empty (head)
```
