# Test report

| Area | Result |
| --- | --- |
| Domain hash and immutable values | 14 passed |
| Application/repository contracts | 3 passed |
| PR-11 PostgreSQL application integration | 18 passed |
| PR-11 PostgreSQL schema integration | 4 passed |
| Architecture and import boundaries | 33 passed |
| Full pytest regression | 396 passed |
| Ruff | PASS |
| Pyright | PASS |
| PR-11-owned formatting | PASS, 14 files |
| PostgreSQL health | PASS |
| PostgreSQL version | 18.6 |
| Alembic current | `0011_statistical_result (head)` |
| Clean migration and 0010↔0011 roundtrip | PASS |

The full regression includes all accepted PR-00 through PR-10 tests and the
new PR-11 tests. No SQLite test path was used.
