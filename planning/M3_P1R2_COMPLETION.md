# M3-P1R2 downgrade lock closure evidence

## Candidate and scope

- Worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m3-literature-evidence`.
- Branch: `feature/m3-literature-evidence`.
- Starting HEAD: `1ab7754f42b5e861d27b7149fa0d982b5a84ec10`; branch and clean worktree verified before editing.
- Implementation SHA: `2c4e311740ab565b6060d1bd2e0c0faccd9bcae6`.
- Production diff: only the downgrade in `migrations/versions/0031_m3_snapshot_relation_cardinality.py`. The new `tests/integration/phase2/test_m3_p1r2.py` tests the real Alembic path. No other production code, 0030 migration, frozen contract, hash code, dependency, or Harness file changed.
- Prior M3 evidence is preserved. Repository evidence identifies only disposable PostgreSQL use of 0031; a non-disposable deployment inventory was not available.

## Root cause and lock/transaction design

The former downgrade checked the snapshot table, then dropped the cardinality triggers, without explicitly obtaining a write-blocking lock before the check. The previous independent review reproduced the check/insert/drop interleaving on a minimal PostgreSQL 18.6 schema. The new Case B real-Alembic test **passed against the old migration**, so that exact race was not reproduced through the original combined Alembic `op.execute` call. The old migration nevertheless lacked the required explicit lock guarantee: the new Case C regression was run before the production edit and failed with `real downgrade never acquired both locks` (pytest exit 1). This is the RED evidence; it is not a successful final test.

The correction executes `LOCK TABLE literature_support_snapshots, literature_evidence_relations IN ACCESS EXCLUSIVE MODE` before either table is read for protected history. The table order matches the 0031 upgrade. The downgrade then checks both tables and refuses any row (`P17D5`); only an empty state reaches the two 0031-specific trigger drops and function drop. Online Alembic uses `context.begin_transaction()`, and PostgreSQL reports transactional DDL. The separate lock statement, history check, trigger removal, and Alembic revision update occur in the same transaction. ACCESS EXCLUSIVE conflicts with writers and remains held until commit or rollback. It is a migration-interval guarantee, not a permanent write prohibition after a successful downgrade.

## Real PostgreSQL 18.6 / Alembic cases

The phase-2 fixture creates and drops a separate disposable database for each test. All four new tests invoke `alembic.command.downgrade` against the real schema.

| Case | Observed result |
| --- | --- |
| A: valid populated history before downgrade | Rejected with SQLSTATE `P17D5`; revision remains 0031, both cardinality triggers remain, snapshot and formal read unchanged. |
| B: writer holds insert lock before downgrade | PostgreSQL blocking relationship was observed. After the valid insert committed, downgrade refused history; revision remained 0031, both triggers remained, formal read was VALID. This test also passed on the old migration and is not claimed as an old-code RED reproduction. |
| C: downgrade paused immediately after the actual Alembic lock operation | Both ACCESS EXCLUSIVE locks were present in `pg_locks`; revision was still 0031 and both triggers still existed. A separate snapshot INSERT timed out with SQLSTATE `55P03` and did not commit. After release, the empty downgrade committed to 0030 and removed the two triggers. |
| D: failed downgrade rollback | After Case A's refusal, a direct-SQL ordinal-1 relation set still failed at commit with SQLSTATE `23514`; no partial enforcement removal occurred. |
| E: empty downgrade | Revision became 0030; only `m3_snapshot_relation_cardinality` and `m3_relation_cardinality` disappeared from the two table trigger inventories, and the 0031 function was removed. No other trigger in those tables changed. |

The Case C test intercepts the Alembic `op.execute` call only **after** the real lock SQL has executed, pauses the migration before its history check, and inspects PostgreSQL locks and a separate writer connection. It does not replace the SQL or fake the lock.

## Verification commands and results

All commands ran from the candidate worktree using PostgreSQL 18.6 at `127.0.0.1:55451`; the maintenance `/postgres` URL made the fixture create isolated databases.

1. `DATABASE_URL='postgresql+psycopg://onephone@127.0.0.1:55451/postgres' PYTHONPATH='src:.' ../m1-identity-onboarding/.venv/bin/python -m pytest -q -c pyproject.toml tests/integration/phase2/test_m3_p1r2.py --tb=short --disable-warnings` — exit 0, **4 passed**.
2. `DATABASE_URL='postgresql+psycopg://onephone@127.0.0.1:55451/postgres' PYTHONPATH='src:.' ../m1-identity-onboarding/.venv/bin/python -m pytest -q -c pyproject.toml tests/integration/phase2/test_m3_p1r2.py tests/integration/phase2/test_m3_p1r1.py tests/integration/phase2/test_m3_evidence.py tests/test_architecture.py --tb=short --disable-warnings --junitxml=/tmp/rb-m3-p1r2-focused.xml` — exit 0, **36 passed, 0 failed/errors/skipped**; retained as `planning/m3_p1r2_evidence/focused-tests.xml`.
3. `DATABASE_URL='postgresql+psycopg://onephone@127.0.0.1:55451/postgres' PYTHONPATH='src:.' ../m1-identity-onboarding/.venv/bin/python -m pytest -q -c pyproject.toml tests/integration/phase2/test_m0_provider_cancellation.py::test_migration_empty_roundtrip_and_populated_downgrade tests/integration/phase2/test_m0_provider_cancellation.py::test_fresh_migration_empty_roundtrip tests/integration/phase2/test_m2_metadata.py::test_empty_m2_migration_roundtrip --tb=short --disable-warnings --junitxml=/tmp/rb-m3-p1r2-migration.xml` — exit 0, **3 passed, 0 failed/errors/skipped**; retained as `planning/m3_p1r2_evidence/migration-tests.xml`.
4. `../m1-identity-onboarding/.venv/bin/ruff check --no-cache migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m3_p1r2.py` — exit 0, `All checks passed!`.
5. `../m1-identity-onboarding/.venv/bin/ruff format --check --no-cache migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m3_p1r2.py` — exit 0, `2 files already formatted`.
6. `../m1-identity-onboarding/.venv/bin/pyright --pythonpath ../m1-identity-onboarding/.venv/bin/python migrations/versions/0031_m3_snapshot_relation_cardinality.py tests/integration/phase2/test_m3_p1r2.py` — exit 0, `0 errors, 0 warnings, 0 informations`. Pyright also emitted `venv .venv subdirectory not found in venv path ...`; this did not change the reported diagnostic counts.
7. `git diff --check` and `git diff --cached --check` — exit 0.

No full historical repository suite or non-disposable deployment test was run. The active 0031 cardinality, hash, M3-01 projection, and architecture regressions in the focused suite passed. Final independent review and real scientific independent-human verification remain outstanding. M3 acceptance is not approved; M4 is not authorized.
