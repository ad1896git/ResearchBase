# Application Equivalence Report

Committed PostgreSQL tests compare HTTP with accepted Application behavior for:

- ExperimentSpec create/freeze: same frozen status and deterministic content hash.
- Run start/finish: same terminal status and row-version semantics.
- structured Measurement: same structured value and unit.
- AuditFinding: same severity and initial status.
- Run provenance, ClaimVersion trace, and downstream impact: complete DTO/JSON equality.
- stable errors: same public code mapped deliberately; no HTTP-only mutation or rule exists.

Semantic drift observed: none.
