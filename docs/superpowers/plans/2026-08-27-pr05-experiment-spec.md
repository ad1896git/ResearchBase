# PR-05 ExperimentSpec Implementation Plan

## Scope

Implement only the concrete `ExperimentSpec` and `ExperimentSpecVersion` Phase 1 slice from the PR-05 Execution Pack. Preserve the accepted PR-04/PR-04R/PR-04R2 baseline and do not add PR-06 or later scientific tables.

## Design

1. Add framework-neutral domain identity/version objects that reuse `VersionStatus`, `freeze_material`, canonical JSON, typed IDs, UTC clocks, and stable ResearchBase errors.
2. Add narrow application commands and repository/UoW ports for create, draft edit, revise, freeze, identity lookup, current lookup, and ordered history.
3. Add concrete SQLAlchemy models/repository adapters and a single `0004_experiment_spec` Alembic migration with PostgreSQL RESTRICT foreign keys, status/version constraints, and the same-parent current-pointer integrity checks exercised by application tests.
4. Enforce optional Hypothesis existence and same-project linkage during create and freeze without requiring a frozen HypothesisVersion.
5. Prove optimistic concurrency, transaction atomicity, rollback cleanliness, pointer ownership, frozen immutability, and migration round trips using the existing PostgreSQL integration test style.
6. Generate the complete PR-05 evidence package only after all required gates have fresh recorded results.

## Test-first sequence

- Add domain and reusable version-contract tests for material editing, transitions, protocol validation, and deterministic frozen hashes.
- Add PostgreSQL application/schema tests for lifecycle, validation, pointer attacks, history, concurrency, rollback, and constraints.
- Implement the smallest production changes needed to turn those tests green.
- Run full pytest, integration, architecture, Ruff, Pyright, Alembic head and round-trip checks.
- Review the final diff for PR-06/Phase 2 leakage and write evidence.
