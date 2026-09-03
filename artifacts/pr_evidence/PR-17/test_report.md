# Test Report

| Check | Result |
|---|---|
| GSAS-01 direct Application / repeated fresh fixtures | PASS; included in 16 E2E tests |
| Application/FastAPI/Typer equivalence and order independence | PASS |
| historical exactness, immutability, hash invariance | PASS |
| positive/negative closure and governance propagation | PASS |
| HTTP/CLI failure recovery and complete error map | PASS |
| atomicity and fresh-UoW rollback/retry | PASS |
| real PostgreSQL concurrency | PASS |
| query purity and output SQL | PASS |
| scaled SQL performance shape | PASS |
| architecture boundaries | 41 passed |
| PR-09..16 baseline bundle | 124 passed |
| full pytest | 100% reached; no failures; 2 opt-in skips |
| Ruff | PASS |
| Pyright | PASS |
| owned formatting | PASS |
| Alembic | `0015_governance_audit (head)` |

All canonical acceptance database runs use PostgreSQL through the repository's synchronous SQLAlchemy UoW
composition. SQLite is not used.
