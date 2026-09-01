# Schema report

PostgreSQL 18.6 contains exactly these PR-14 business tables: `audit_findings`, `impact_assessments`, `impact_targets`, and `correction_records`. Exact-column, enum, FK/RESTRICT, constraint, and trigger tests pass. No unauthorized uniqueness or business table was added. Alembic head is `0015_governance_audit`.
