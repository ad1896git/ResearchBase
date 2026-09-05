# Phase 1 Exit Summary

PR-17R records the Phase 1 acceptance exit for accepted PR-01 through PR-17 capabilities. The final Alembic head
is `0015_governance_audit (head)` on PostgreSQL 18.6. PR-17R adds acceptance evidence and architecture tests;
it adds zero canonical entities, tables, migrations, routes, or CLI commands.

Accepted capability inventory:

- PR-01 through PR-03: repository foundation, actors, projects, workspaces, persistence composition, and UoW.
- PR-04: versioned ResearchQuestion and Hypothesis lifecycles.
- PR-05: versioned ExperimentSpec records and frozen historical references.
- PR-06: immutable DatasetSnapshot records and input identity.
- PR-07: immutable ArtifactVersion records and artifact input identity.
- PR-08: versioned MetricDefinition records and frozen metric references.
- PR-09: Run lifecycle, sealed dataset/artifact inputs, provenance, and closure.
- PR-10: immutable Measurements and content hashes.
- PR-11 through PR-11R: StatisticalResult records, typed ordered input edges, guards, and migration regressions.
- PR-12 through its accepted remediation line: ClaimVersion, EvidenceRelation, evidence freezing, concurrency,
  atomicity, and claim closure.
- PR-13: read-only provenance, trace, closure, and impact query services.
- PR-14: AuditFinding, ImpactAssessment, ImpactTarget, CorrectionRecord, validity, and governance propagation.
- PR-15: FastAPI adapter with 35 routes.
- PR-16: Typer adapter with 14 groups and 35 commands.
- PR-17 and PR-17R: corrected GSAS, observational cross-adapter equality, historical exactness, immutability,
  closure, concurrency, atomicity, query, SQL-shape, and governance evidence.

The canonical schema remains the accepted Phase 1 schema through migration `0015`; the Application boundary owns
handlers, queries, DTOs, and orchestration. FastAPI and Typer call Application directly. DTOs are ORM/session-free.
Provenance and governance are covered by exact Run inputs, trace and closure reads, and target/result/validity/
correction evidence.

Known P3 debt is the same eight inherited Ruff-formatting files: `migrations/versions/0004_experiment_spec.py`,
`tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`,
`tests/integration/test_pr05_application.py`, `tests/integration/test_pr05_schema.py`,
`tests/integration/test_pr06_application.py`, `tests/integration/test_pr06_schema.py`, and
`tests/unit/domain/test_pr05_experiment.py`.

Phase 2 is NOT AUTHORIZED. PR-18 is NOT AUTHORIZED. No Agent runtime, workflow engine, DecisionRecord, or
Approval implementation exists.
