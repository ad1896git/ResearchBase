# PR-17R Test Report

| Check | Result |
|---|---|
| corrected GSAS, Application/HTTP/CLI, fresh fixtures, adapter orders | PASS; included in 66-test selection |
| projection anti-cheat and cross-adapter equality | PASS |
| historical exactness and immutability/hash | PASS |
| positive and broken-descendant closure | PASS |
| real Claim evidence/freeze concurrency | PASS |
| atomicity and fresh-UoW rollback/retry | PASS |
| version revise, Claim freeze, Run transition, AuditFinding races | PASS |
| query purity, SQL shape, error equivalence | PASS |
| HTTP and CLI regression | PASS |
| Agent-ready architecture | PASS |
| exact PR-09..16 baseline regression | 156 collected; 154 passed; 2 skipped; 0 failed |
| full pytest | 642 passed; 2 skipped; 0 failed in 56.56s |
| Ruff check | PASS |
| Pyright | PASS |
| owned formatting | PASS |
| repository-wide formatting | expected inherited P3 failure in eight unchanged files |
| Alembic | `0015_governance_audit (head)` |

The two baseline and full-suite skips are the opt-in PR11R2 migration-matrix cases because
`PR11R2_MIGRATION_DB_URL` was not set. All canonical acceptance database runs use PostgreSQL 18.6; SQLite is not
used.
