# PR2-02 implementation verification

## Subjects

- Starting accepted subject: `e08981d0bb7af157a04d78918923e04a3763ba40`
- Implementation subject: `a80ff23a0555b6f629dd40d68372b270dfd5fd61`
- Evidence subject: this file is committed as an evidence-only child; it does not certify its own commit SHA.
- Migration: `0022_source_version_and_merge_lineage`, parent `0021a_source_merge_gov_guards`.
- Phase 1 tag object: `63f6a1d28afa79ce8620fc9233793ab9c40a515d`; peeled frozen baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115`.

## Scope and changed files

PR2-02 adds SourceVersion persistence and lifecycle operations, deterministic content hashes, ArtifactVersion references, correction/retraction lineage, source merge execution using accepted SourceMergeProposal approvals, non-destructive merged-source aliases, HTTP/CLI commands, and migration 0022. It preserves the accepted governance bridge, PR2-01 identity model, and Phase 1 semantics.

Implementation changed 32 files: migration `0022_source_version_and_merge_lineage.py`; CI migration-head expectation; Application, Domain, Persistence, HTTP and CLI modules for SourceVersion and source merge execution; architecture and existing API/CLI contract inventories; PR2-00/01 regression integration tests; and PR2-02 unit/integration tests.

## Verification results

All successful commands below were run against PostgreSQL 18.6 unless stated otherwise.

| Gate | Command / evidence | Result |
|---|---|---|
| Focused SourceVersion and merge integration | `uv run pytest tests/integration/phase2/test_pr2_02_source_version_migration.py -q` | 9 passed; includes four deterministic lock-wait authorization cases, migration fresh install/downgrade behavior, version lifecycle/replay, and atomic merge/exact replay. |
| PostgreSQL suite | `DATABASE_URL=… uv run pytest -o addopts='' -q` | 1,889 passed, 2 skipped, 0 failed, 93 Alembic deprecation warnings; 108.39 seconds on final clean-server run. |
| Ruff | `uv run ruff check .` | PASS; all checks passed. |
| Pyright | `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations. |
| Raw formatter command | `uv run ruff format --check .` | Nonzero, accurately reported: nine files would be reformatted; 244 files already formatted. |
| Formatter baseline delta | Same raw command at starting subject `e08981d0…` and implementation subject | Both report the same nine failures listed below; `NEW_FORMATTER_FAILURES = ∅`. All 31 changed Python files pass `ruff format --check`. |
| Whitespace | `git diff --check` and `git diff --cached --check` before implementation commit | PASS. |
| Phase 1 drift | `git diff --name-status d2400fb… -- migrations/versions/000[1-9]* migrations/versions/001[0-8]*` | Empty; no frozen historical migrations changed. Phase 1 tag object and peeled baseline verified. |
| Migration | Focused migration tests and full suite | Fresh install reaches 0022; 0022 has exact parent 0021a; empty downgrade restores 0021a guards; populated downgrade refuses before losing lineage. |
| PR2-00 / PR2-01 / governance regression | Full suite | Included and passed; no post-expiry challenge success was reproduced. |

Inherited formatter failures, identical at baseline and implementation subjects:

```text
migrations/versions/0004_experiment_spec.py
scripts/pr17dr_evidence.py
tests/integration/test_pr04_application.py
tests/integration/test_pr04_schema.py
tests/integration/test_pr05_application.py
tests/integration/test_pr05_schema.py
tests/integration/test_pr06_application.py
tests/unit/domain/test_pr05_experiment.py
tests/unit/test_pr17dr2_evidence.py
```

## PostgreSQL reproducibility

The integration fixture creates and drops a unique PostgreSQL database for each test. It needs a maintenance database and a role allowed to create databases. A reviewer can start a clean local PostgreSQL 18.6 instance with test-only credentials:

```bash
docker run --detach --name researchbase-pr2-02-postgres \
  --env POSTGRES_USER=researchbase \
  --env POSTGRES_PASSWORD=researchbase \
  --env POSTGRES_DB=researchbase_phase1 \
  --publish 127.0.0.1:5432:5432 \
  postgres:18.6-alpine

# Wait for readiness, then initialize the base DB at the frozen Phase 1 head.
docker exec researchbase-pr2-02-postgres \
  pg_isready -U researchbase -d researchbase_phase1
DATABASE_URL='postgresql+psycopg://researchbase:researchbase@127.0.0.1:5432/researchbase_phase1' \
  uv run alembic upgrade 0018_current_pointer_same_parent_integrity

DATABASE_URL='postgresql+psycopg://researchbase:researchbase@127.0.0.1:5432/researchbase_phase1' \
  uv run pytest -o addopts='' tests/integration/phase2/test_pr2_02_source_version_migration.py
DATABASE_URL='postgresql+psycopg://researchbase:researchbase@127.0.0.1:5432/researchbase_phase1' \
  uv run pytest -o addopts='' -q

docker rm --force researchbase-pr2-02-postgres
```

If port 5432 is occupied, publish `127.0.0.1::5432`, read the assigned host port with `docker port researchbase-pr2-02-postgres 5432/tcp`, and substitute it in `DATABASE_URL`. The URLs above contain only local test credentials, not production secrets.

## Preserved test anomaly and investigation

One explicit-count full-suite run reported 1,887 passed, 2 skipped, and two PR2-02 integration setup failures. Both failures occurred before PR2-02 application code, during the shared bootstrap check, with PostgreSQL `out of shared memory` / `max_pred_locks_per_transaction`. Inspection found 17,407 `SIReadLock` entries associated with backend PIDs absent from `pg_stat_activity`. The disposable server was restarted; its forwarded port changed from 32768 to 32769. The two affected tests passed in isolation on the restarted server, and the complete explicit-count suite then passed: 1,889 passed, 2 skipped. This is recorded as an environment resource anomaly, not classified as flaky or suppressed.

## Idempotency and merge behavior exercised

The integration suite verifies the accepted command key `(deployment_id, actor_id, project_id, command_name, request_id)`, cross-project request-ID reuse, same-project cross-command reuse, exact replay without repeating the protected effect, changed-payload conflict, concurrent same-key merge with one durable merge result, one-time proposal consumption, and canonical alias resolution. SourceVersion commands use scoped command receipts and compare the canonical request hash only after receipt-key lookup.

## Evidence boundary

This evidence describes implementation subject `a80ff23a0555b6f629dd40d68372b270dfd5fd61`. The evidence-only commit SHA is intentionally not stated here. The repository was clean after the implementation commit; this evidence file is the only change in its child commit.
