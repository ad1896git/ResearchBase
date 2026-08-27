# PR-04 ResearchQuestion and Hypothesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the concrete ResearchQuestion and Hypothesis identity/version slices with exact PR-03 lifecycle/hash reuse, transactional application flows, current pointers, optimistic concurrency, history queries, and PostgreSQL migration.

**Architecture:** Keep four framework-neutral Domain dataclasses in `domain/research.py`. Keep four SQLAlchemy models and explicit mappers in persistence, narrow domain-specific repository ports in application, and one synchronous UnitOfWork transaction per command. Application validates same-parent and same-project invariants; PostgreSQL enforces concrete foreign keys, checks, uniqueness, and restrict deletion.

**Tech Stack:** Python 3.12, uv, SQLAlchemy 2.x, Alembic, PostgreSQL 18, pytest, Ruff, Pyright.

## Global Constraints

- Preserve the accepted PR-03/PR-03R baseline at `4dfffd8`.
- Implement PR-04 only; do not implement PR-05 or later phases.
- Reuse `VersionStatus`, `freeze_material`, `canonical-json-v1`, and `sha256-cjson-v1`.
- Do not add a generic Version entity, Version ORM/table, VersionRepository, or global version registry.
- Domain must not import SQLAlchemy, persistence, FastAPI, or Typer.
- Repositories never commit; the UnitOfWork owns one transaction per Application command.
- Use concrete UUID foreign keys with `ON DELETE RESTRICT`; do not use polymorphic primary-chain references.
- Preserve frozen material and historical versions; stale optimistic updates raise `CONCURRENT_MODIFICATION`.

### Task 1: Concrete Domain Types and Version Contract

**Files:**
- Create: `src/researchbase/domain/research.py`
- Test: `tests/unit/domain/test_pr04_research.py`

- [ ] Write failing tests for exact fields, validation, material payload selection, PR-03 freeze/hash reuse, and four concrete lifecycle types.
- [ ] Run the tests and confirm the module/types are missing.
- [ ] Implement `ResearchQuestion`, `ResearchQuestionVersion`, `Hypothesis`, and `HypothesisVersion` with typed UUIDs, explicit material payload methods, immutable frozen dataclasses, and `freeze_material`/`require_transition` composition.
- [ ] Run the unit and reusable contract tests.

### Task 2: PostgreSQL Migration and ORM Mapping

**Files:**
- Create: `migrations/versions/0003_research_question_hypothesis.py`
- Modify: `src/researchbase/persistence/models.py`
- Test: `tests/integration/test_pr04_schema.py`

- [ ] Write failing schema tests for the four tables, CHECK/UNIQUE/FK/RESTRICT constraints, JSONB/TIMESTAMPTZ/UUID columns, and no cascade.
- [ ] Implement migration `0003_research_question_hypothesis` with deferred current-pointer foreign keys and reversible downgrade to `0002_actor_project_workspace`.
- [ ] Add explicit SQLAlchemy models and keep current-pointer FK ownership concrete.
- [ ] Run schema tests against PostgreSQL 18 and migration upgrade/downgrade roundtrips.

### Task 3: Domain Repositories and UnitOfWork

**Files:**
- Modify: `src/researchbase/application/ports.py`
- Modify: `src/researchbase/persistence/repositories.py`
- Modify: `src/researchbase/persistence/uow.py`
- Test: `tests/integration/test_pr04_transactions.py`

- [ ] Write failing tests for add/get/current/history, same-parent pointer rejection, explicit expected-row-version updates, and repository non-commit behavior.
- [ ] Implement narrow ResearchQuestion/Hypothesis repositories, explicit ORM-to-Domain mappers, row-lock reads, max-version queries, current-pointer updates, and stale update translation.
- [ ] Extend the existing UoW with the two repositories without changing session ownership or commit semantics.
- [ ] Run repository, transaction, and concurrency tests.

### Task 4: Application Commands and History Queries

**Files:**
- Modify: `src/researchbase/application/commands.py`
- Modify: `src/researchbase/application/dto.py`
- Test: `tests/integration/test_pr04_application.py`

- [ ] Write failing tests for atomic create, revise, freeze, draft update, history ordering, pointer ownership, project consistency, and stable errors.
- [ ] Implement create/revise/freeze/update commands for both concrete types, checking actor/project/RQ preconditions and using one UoW per command.
- [ ] Move current pointers atomically, supersede frozen bases during revision, preserve all prior material, and expose read DTOs/history without ORM objects.
- [ ] Run application and history tests against real PostgreSQL.

### Task 5: Full Verification and Evidence

**Files:**
- Modify: `tests/architecture/test_import_boundaries.py`
- Create: `artifacts/pr_evidence/PR-04/` required evidence files

- [ ] Run full pytest with PostgreSQL, PR-03 contract tests, architecture tests, Ruff, Pyright, lock/format checks, Alembic roundtrip, and PostgreSQL health checks.
- [ ] Audit the diff for PR-05/later implementation, generic Version storage, cascades, and persistence/UoW regressions.
- [ ] Generate the complete PR-04 evidence package with exact command outputs and fingerprints.
- [ ] Commit implementation and evidence as new commits on top of `4dfffd8`, then STOP.
