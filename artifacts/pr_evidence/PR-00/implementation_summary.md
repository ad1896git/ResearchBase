# PR-00 Implementation Summary

## Status

PR-00 bootstrap implementation completed. The repository is an independent Git repository
at `/Users/onephone/Documents/Codex/ResearchBase`. No business-domain implementation was
performed.

## Implemented

- Python 3.12 / uv project configuration and lockfile.
- Minimal package boundaries for foundation, persistence, application, API, and CLI.
- Synchronous SQLAlchemy + psycopg connectivity smoke adapter.
- Empty Alembic bootstrap migration; no scientific tables.
- FastAPI `/health` smoke adapter.
- Typer `version` and `status` smoke commands.
- SHA-256 content-addressed filesystem ArtifactStore infrastructure port and smoke backend.
- Docker Compose PostgreSQL 18 development profile and CI workflow.
- ADR-0001 through ADR-0007.
- Architecture drift tests and PR-00 evidence package.

## Scope statement

ResearchQuestion, Hypothesis, ExperimentSpec, Run, Dataset, Artifact domain entities,
Measurement, StatisticalResult, EvidenceRelation, Claim, governance behavior, Agent Runtime,
Phase 2, Phase 3, and Phase 4 functionality were not implemented.

