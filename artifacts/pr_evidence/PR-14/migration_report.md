# Migration report

- Disposable PostgreSQL database from base → `0015_governance_audit`: PASS.
- `0015 → 0014`: PASS; catalog after downgrade reported 0 PR-14 tables, 0 PR-14 triggers, and 0 PR-14 functions.
- `0014 → 0015`: PASS.
- Persistent DB final head: `0015_governance_audit`.
- Exactly one PR-14 migration and four authorized tables: PASS.
