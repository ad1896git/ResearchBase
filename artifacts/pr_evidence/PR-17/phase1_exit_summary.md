# Phase 1 Exit Summary

PR-17R records the Phase 1 acceptance exit for the accepted PR-01 through PR-17 capability line. The final
Alembic head is `0015_governance_audit (head)` on PostgreSQL 18.6. PR-17R adds acceptance evidence and committed
architecture tests only; it adds zero canonical entities, tables, migrations, routes, or CLI commands.

Accepted capability inventory:

- PR-01 through PR-03 establish the repository foundation, actors, projects, workspaces, application boundary,
  persistence composition, and unit-of-work conventions.
- PR-04 establishes versioned ResearchQuestion and Hypothesis lifecycles.
- PR-05 establishes versioned ExperimentSpec records and frozen historical references.
- PR-06 establishes immutable DatasetSnapshot records and input identity.
- PR-07 establishes immutable ArtifactVersion records and artifact input identity.
- PR-08 establishes versioned MetricDefinition records and frozen metric references.
- PR-09 establishes Run lifecycle, sealed dataset/artifact inputs, provenance, and closure.
- PR-10 establishes immutable Measurements and content hashes.
- PR-11 through PR-11R establish StatisticalResult records, typed ordered input edges, guards, and migration
  regression coverage.
- PR-12 through its accepted remediation line establish ClaimVersion, EvidenceRelation, evidence freezing,
  concurrency, atomicity, and claim closure.
- PR-13 establishes read-only provenance, trace, closure, and impact query services.
- PR-14 establishes AuditFinding, ImpactAssessment, ImpactTarget, CorrectionRecord, validity projection, and
  governance propagation.
- PR-15 establishes the FastAPI adapter with the accepted 35-route contract.
- PR-16 establishes the Typer adapter with the accepted 14-group, 35-command contract.
- PR-17 and PR-17R establish the corrected GSAS, cross-adapter observational equivalence, historical exactness,
  immutability, closure, concurrency, atomicity, query, SQL-shape, and governance acceptance evidence.

The canonical schema remains the accepted Phase 1 schema through migration `0015`; no new canonical entity,
table, migration, route, or command was introduced. The Application boundary owns handlers, queries, DTOs, and
business orchestration. FastAPI and Typer call Application directly and transport data through ORM/session-free
DTOs. Provenance and governance are covered by exact Run inputs, trace and closure reads, and governance target,
result, validity, and correction evidence.

The known P3 debt is the same eight inherited Ruff-formatting files: `migrations/versions/0004_experiment_spec.py`,
`tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`,
`tests/integration/test_pr05_application.py`, `tests/integration/test_pr05_schema.py`,
`tests/integration/test_pr06_application.py`, `tests/integration/test_pr06_schema.py`, and
`tests/unit/domain/test_pr05_experiment.py`.

Phase 2 is NOT AUTHORIZED. PR-18 is NOT AUTHORIZED. No Agent runtime, workflow engine, DecisionRecord, or
Approval implementation exists in this Phase 1 exit evidence.
