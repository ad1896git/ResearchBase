# PR-10R architecture review

The remediation preserves the required Caller → Application Service → Repository
Port/UoW → SQLAlchemy Adapter → PostgreSQL path. The real invalid-closure setup uses
PostgreSQL only as an adversarial test fixture and does not add a production bypass.
The independent oracle is test-owned; no domain or application layer is coupled to
test code.

The Git range contains no production source or migration change. No StatisticalResult,
Claim, MeasurementVersion, generic Version ORM/table, generic polymorphic reference,
Phase 2+ behavior, or new transaction framework was introduced. The migration head
remains `0010_measurement`.

Architecture result: PASS.
