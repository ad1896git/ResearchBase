# PR-02 Test Report

## Gate checklist

- Actor domain model: PASS.
- Project domain model: PASS.
- Workspace domain model: PASS.
- Repository ports and ORM/domain mapping: PASS.
- UnitOfWork shared transaction and explicit commit/rollback: PASS.
- Create/get application commands: PASS.
- ExecutionContext `created_by` propagation: PASS.
- PostgreSQL UUID/TIMESTAMPTZ/row-version schema: PASS.
- Actor type and lifecycle CHECK constraints: PASS.
- Partial unique `external_key` constraint: PASS.
- Concrete foreign keys with `ON DELETE RESTRICT`: PASS.
- Migration upgrade/downgrade/upgrade: PASS.
- Domain/application architecture boundaries: PASS.
- No ORM objects exposed by application read models: PASS.
- No VersionStatus or version state machine: PASS.
- No PR-03+ or Phase 2+ implementation: PASS.
- Ruff: PASS.
- Pyright: PASS.
- pytest: PASS; 92 passed against real PostgreSQL.
- Open P0: 0.
- Open P1: 0.

## Exact verification summary

```text
Full pytest with PostgreSQL: 92 passed in 0.40s
Integration pytest: 16 passed, 76 deselected in 0.28s
Architecture tests: 22 passed in 0.03s
Ruff: All checks passed!
Pyright: 0 errors, 0 warnings, 0 informations
PostgreSQL: 18.6, healthy postgres:18-alpine
Alembic: 0002_actor_project_workspace (head); downgrade/upgrade round-trip passed
```

The accepted PR-01 and PR-01R evidence packages remain unchanged.
