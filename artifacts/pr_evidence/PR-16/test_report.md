# Test Report

Fresh verification was run from final subject head `fac2093`.

| Check | Result |
|---|---|
| full pytest (PostgreSQL-gated tests skipped when no URL) | 360 passed, 259 skipped |
| PR-16 targeted and architecture tests | 20 passed |
| real PostgreSQL CLI integration | 3 passed |
| PR-09–PR-14 PostgreSQL regressions | 141 passed |
| PR-15 HTTP/OpenAPI unit regression | 9 passed |
| PR-15 PostgreSQL HTTP regression | 10 passed |
| Ruff | PASS |
| Pyright | PASS, 0 errors |
| owned formatting | PASS |
| Alembic | `0015_governance_audit (head)` |
| git diff check | PASS |

Transport attack, command-handler map, context forwarding, request-ID isolation, JSON purity, recovery, query
purity, output SQL, and help smoke checks are included in the PR-16 targeted and integration suites.
