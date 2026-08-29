# PR-11R3 test report

| Gate | Observation | Result |
| --- | --- | --- |
| Full pytest | `410 passed` | PASS |
| Strengthened migration matrix | Clean populated upgrade plus failed-upgrade catalog inspection | PASS — `2 passed` |
| PR-11 application/schema/unit regressions | Included in focused regression run | PASS |
| Duplicate translation, ordering/boundaries, hash, provenance, query/FK | Included in full/focused regression runs | PASS |
| Immutability, atomicity, same-project provenance | Included in full/focused regression runs | PASS |
| Architecture tests | Existing architecture suite passed | PASS |
| Ruff | `All checks passed!` | PASS |
| Pyright | `0 errors, 0 warnings, 0 informations` | PASS |
| Owned formatting | `1 file already formatted` | PASS |
| PostgreSQL health/version | Real PostgreSQL `18.6`, smoke test passed | PASS |
| Alembic current | `0013_statistical_result_legacy_input_precheck (head)` | PASS |
| Migration roundtrip | `0013 -> 0012 -> 0013` passed | PASS |

Repository-wide `ruff format --check .` reports eight pre-existing files outside
the PR-11R3 change set. This remains a non-blocking inherited P3; the owned
scope is formatted.
