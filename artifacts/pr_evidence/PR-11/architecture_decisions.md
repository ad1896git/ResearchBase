# Architecture decisions

- StatisticalResult is an immutable scientific record, not a versioned identity.
- `StatisticalResultInput` stores exact Measurement UUID provenance; it does not
  duplicate `project_id` and does not use a polymorphic or soft reference.
- The required write path remains Application Service → Repository Port/UoW →
  SQLAlchemy adapter → PostgreSQL.
- Reads use explicit SQLAlchemy Core table selections and map to frozen DTOs;
  ORM entities and Sessions do not cross the application boundary.
- The repository has only add, add-input, get, project-list, and input-list
  operations and never commits.
- No generic Version model/table, generic evidence repository, transaction
  framework, Claim, EvidenceRelation, or PR-12 behavior was introduced.
