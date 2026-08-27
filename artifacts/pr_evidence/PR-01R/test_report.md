# PR-01R Test Report

## Gate checklist

- IRR-P1-001 fixed and adversarially tested: PASS; architecture suite 57 passed overall.
- UUIDv7 timestamp/bit-layout regression coverage: PASS.
- ContentHash negative coverage: PASS.
- `canonical-json-v1` behavior explicitly frozen/documented: PASS.
- Hash/canonical scheme identifiers machine-readable: PASS.
- Unauthorized numeric coercion or Unicode normalization: NONE INTRODUCED.
- No business schema added: PASS.
- No PR-02+ implementation: PASS.
- No Phase 2+ implementation: PASS.
- Ruff: PASS.
- Pyright: PASS.
- pytest: PASS; 66 passed against real PostgreSQL.
- Open P0: 0.
- Open P1: 0.

## Exact verification summary

```text
Full pytest with PostgreSQL: 66 passed in 0.24s
Integration pytest: 1 passed, 65 deselected in 0.19s
Foundation + architecture tests: 57 passed in 0.05s
Ruff: All checks passed!
Pyright: 0 errors, 0 warnings, 0 informations
PostgreSQL: postgres:18-alpine, healthy, PostgreSQL 18.x profile
Alembic: 0001_empty (head); upgrade head exit 0
```

The original PR-01 evidence remains unchanged. Current PR-01R evidence records the restored
database verification separately.
