# M3 Alembic URL boundary correction — conditional evidence

- Base: `3aa97c8dbe12697731eb011322002e3964e6383a`.
- Initial implementation: `cbc3b3f9125c2796e10d00417dfc297b0dfd8fdc`.
- Final implementation after narrow P2 test correction:
  `9f6fa42b2f10345fe073ac4c71cbe28c53a7f5a6`.
- Scope: `docs/phase2/M3-ALEMBIC-URL-boundary-scope.md`.
- Branch/worktree: `feature/m3-alembic-url-boundary`,
  `worktrees/m3-alembic-url-boundary`.

## Reproduction and correction

The pre-change standalone `test_pg_m3_migration_from_phase1_and_empty_roundtrip`
failed before database connection: `Config.set_main_option()` rejected the
fixture's SQLAlchemy URL with `host=%2Fprivate%2Ftmp` as invalid ConfigParser
interpolation. The shared fixture now emits an equivalent literal-slash
Unix-socket host, while `migrations/env.py` escapes literal percent signs
once when an environment URL is passed into ConfigParser. A separate real
PostgreSQL test sets an encoded URL in `DATABASE_URL`, migrates the disposable
database, checks ConfigParser roundtrip and checks the actual database target.
The old M3 roundtrip test is pinned to its intended 0031 revision; `head`
now includes the later reviewed PR2-10 0032 migration.

## Actual checks

- Test cluster preflight: PostgreSQL 18, port 55442,
  `data_directory=/private/tmp/rb-m3-postgres`, system identifier
  `7695073913076924777`, peer user `onephone`. It is separate from durable
  retained M2/M3 port 55440. Each test created and dropped its own database;
  read-only post-test inventory found no nondefault database on port 55442.
- Full `tests/integration/phase2/test_m3_evidence.py`: **13 passed**, exit 0.
  Raw output `M3-ALEMBIC-URL-m3-pg-output.txt`, SHA-256
  `3021abbf43e242e6227cc593efa9169d40f7dfd208cda76869d9668e05393012`.
  After the P2 test-only correction, the affected encoded-URL PostgreSQL test
  passed again in one newly created/dropped disposable database (exit 0).
- `tests/integration/phase2/test_pr2_10_discussion_persistence.py`:
  **9 passed**, exit 0, nine disposable create/drop pairs. Raw output
  `M3-ALEMBIC-URL-pr210-pg-output.txt`, SHA-256
  `d8429a994921c901bc01b0e273e6b9c21f12554b1505554161d56514d71c2d1b`.
- Focused unit, architecture, M2 provider and M3 registration regression:
  **115 passed**, exit 0 (same command as reviewed PR2-10 evidence).
- Ruff on the three changed Python files: PASS. Pyright with explicit shared
  Python 3.12.14 interpreter: **0 errors, 0 warnings**. The first Pyright
  invocation without `--pythonpath` produced missing-import errors because
  this isolated worktree has no local `.venv`; that invocation is not counted
  as a pass.
- Read-only retained M3 data-only dump SHA-256 remained
  `667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`,
  equal to the accepted pre-run baseline. No retained writes, schema changes,
  provider calls or Human Gate actions occurred.

The two previously established execution-service cancellation failures and
the separate migration-list assertion remain tracked as baseline failures,
not passes. No live provider, Human Gate, TDG2 or formal milestone acceptance
is inferred from these integration checks.

## Independent review

The first fresh read-only review of `cbc3b3f` found no P0/P1 but one P2:
the new regression test hardcoded the socket directory. The narrow follow-up
`9f6fa42` derives the socket path from the fixture, then percent-encodes it.
A second fresh read-only review of final SHA `9f6fa42` reported conditional
**PASS** with no P0/P1/P2 findings. Neither reviewer modified the candidate
or reran the database tests. This is conditional technical closure only;
formal M3 or Phase 2 milestone acceptance is not claimed.
