# PR-05R Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion. Execute each item with a failing test before production changes.

**Goal:** Close PR05-REV-001 through PR05-REV-006 on top of baseline `1ab6033` while applying AD-PR05-001 and keeping PR-06 unauthorized.

**Architecture:** Keep `hypothesis_id` on the immutable ExperimentSpec identity and out of ExperimentSpecVersion material. Validate canonical material before persistence writes, retain the shared PR-03 freeze/hash helper, and prove transaction/concurrency state using independent PostgreSQL sessions.

**Tech Stack:** Python 3.12, uv, pytest, SQLAlchemy 2, Alembic, PostgreSQL 18, Ruff, Pyright.

## Global Constraints

- Preserve baseline commit `1ab6033`; never amend, rebase, squash, or rewrite it.
- Implement PR-05R remediation only; do not add PR-06 or later tables, commands, or abstractions.
- Use real PostgreSQL for application, rollback, concurrency, constraint, and migration evidence.
- Keep `hypothesis_id` identity-level, immutable after create, and excluded from version material/hash.

### Task 1: Stable invalid-material errors

**Files:** modify `src/researchbase/domain/experiment.py`, `src/researchbase/application/commands.py`; test `tests/unit/domain/test_pr05_experiment.py` and `tests/integration/test_pr05_application.py`.

- [ ] Add tests proving create, DRAFT update, revise, and freeze return `ResearchBaseError(VALIDATION_ERROR)` for unserializable material and preserve `__cause__`.
- [ ] Run the focused tests and observe the raw serializer failure before changing production code.
- [ ] Add one shared canonical-material validation method and call it before repository writes; keep `freeze_material` as the hash authority and catch only `TypeError`/`ValueError` from canonical JSON.
- [ ] Run focused tests and all existing PR-05 tests.

### Task 2: Exact rollback and overlap evidence

**Files:** modify `tests/integration/test_pr05_application.py`.

- [ ] Extend freeze/revise rollback tests with exact pre-state snapshots and fresh UoW/session assertions after injected post-flush failures.
- [ ] Extend genuine concurrent revision tests with exact version IDs, pointer ownership, row version, and no raw DB-error assertions.
- [ ] Run the PostgreSQL tests and retain only evidence from fresh connections.

### Task 3: Material contract and identity immutability evidence

**Files:** modify `tests/unit/domain/test_pr05_experiment.py`, `tests/integration/test_pr05_application.py`; do not modify higher-authority documents.

- [ ] Add independent six-field hash differential tests, explicit field-set golden assertion, excluded-metadata stability, and hypothesis-link stability through revise/freeze.
- [ ] Add a direct freeze-path invalid-material test using a real application/UoW boundary and assert persisted DRAFT pre-state.
- [ ] Verify no relink command or arbitrary repository relink method exists.

### Task 4: Migration and gates

**Files:** update PR-05 evidence; create `artifacts/pr_evidence/PR-05R/`.

- [ ] Use a disposable PostgreSQL database for `0004 -> 0003 -> 0004`, separately verify empty upgrade and persistent DB head without downgrading the persistent database.
- [ ] Run pytest, Ruff, Pyright, architecture, PR-03 contract, PR-04 regression, PR-05/PR-05R integration, and Alembic current checks.
- [ ] Reconcile original PR-05 evidence, generate all 16 PR-05R evidence files, commit remediation and evidence separately, and stop.
