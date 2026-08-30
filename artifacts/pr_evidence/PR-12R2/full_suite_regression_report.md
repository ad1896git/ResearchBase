# Full-suite and database-isolation regression

Required sequence executed without manual repair:

1. Migration subset: 2 passed, 1 warning in 3.89s.
2. Shared and disposable Alembic: `0014_claim_evidence (head)`.
3. PR-12 targeted: 75 passed in 1.83s.
4. Full pytest Run A: 486 passed, 1 warning in 9.69s.
5. Shared Alembic: `0014_claim_evidence (head)`.
6. Full pytest Run B: 486 passed, 1 warning in 9.67s.
7. Shared and disposable Alembic: `0014_claim_evidence (head)`.

PostgreSQL was 18.6. The migration subset includes clean upgrade/roundtrip and invalid-legacy fail-closed/remediation-retry coverage. No SQLite and no manual `alembic upgrade` repair were used.
