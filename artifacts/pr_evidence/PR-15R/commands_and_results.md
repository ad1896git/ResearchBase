# Commands and Results

- Baseline: `1afe9845fb04cbbb243b290aecea84e6b74f1b0c`.
- Committed reviewed test subject/evidence parent: `f05f33e6e16f6d7159fc0b3a93e5440f227d860a`.
- Full pytest with PostgreSQL: exit 0; 594 passed, 2 pre-existing optional migration-matrix skips (596 collected).
- PR-15/PR-15R targeted PostgreSQL: 67 passed.
- Architecture plus PR-09 through PR-14 regression selection: 194 passed.
- Ruff: PASS.
- Pyright: 0 errors, 0 warnings.
- Repository format: same 8 inherited historical files; 130 formatted.
- PR-15R owned Python format: 4 files pass.
- Alembic: `0015_governance_audit (head)`.
- SQL replay: run 9/9; trace small 15/15 and multipath 17/17; impact small 3/3 and multipath 6/6 direct/HTTP SELECTs; added 0.
- `git diff --check`: PASS.
