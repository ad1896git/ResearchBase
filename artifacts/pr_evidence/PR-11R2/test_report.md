# PR-11R2 test report

This report is finalized from fresh command output after the implementation
and architecture-test commits.

| Gate | Result |
| --- | --- |
| Full pytest | PASS — 410 passed in 10.36s |
| PR-11R2 migration attack matrix | PASS — 2 tests passed on disposable PostgreSQL |
| PR-11 application/schema regressions | PASS — included in focused run |
| Duplicate translation, ordering/boundaries, hash, provenance, query/FK, immutability, atomicity | PASS — included in full and focused runs |
| Same-project provenance | PASS — included in full and focused runs |
| Ruff | PASS — all checks passed |
| Pyright | PASS — 0 errors, 0 warnings, 0 informations |
| Architecture tests | PASS — 34 passed; authorized 0013 is included in the migration inventory |
| PostgreSQL health/version | PASS — PostgreSQL 18.6 |
| Alembic current | PASS — `0013_statistical_result_legacy_input_precheck (head)` |
| Clean migration | PASS |
| Invalid legacy migration failure | PASS |
| Manual remediation retry | PASS |
| Migration roundtrip | PASS |
| Repository-wide format | P3 inherited debt — 8 pre-existing files outside PR-11R2 would be reformatted |
| PR-11R2-owned format | PASS — 3 files already formatted |

No SQLite test or migration path was used.
