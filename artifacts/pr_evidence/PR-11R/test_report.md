# PR-11R test report

| Gate | Result |
| --- | --- |
| Full pytest regression | PASS — 408 passed |
| PR-11R focused application/schema/domain | PASS — 47 passed |
| PR-11 PostgreSQL application | PASS — 27 passed |
| PR-11 PostgreSQL schema | PASS — 5 passed |
| Ruff | PASS |
| Pyright | PASS |
| Architecture/import boundaries | PASS — 34 passed |
| PR-11R-owned format | PASS — 7 files |
| Repository-wide format | inherited debt only, 8 files outside PR-11R |
| PostgreSQL health/version | PASS — PostgreSQL 18.6 |
| Alembic current | PASS — `0012_statistical_result_input_guard (head)` |
| Clean migration | PASS |
| Migration downgrade/upgrade roundtrip | PASS |
| Zero-input guard on disposable clean head | PASS — 2 passed |

No SQLite test or migration path was used.
