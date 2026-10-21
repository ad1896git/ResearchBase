# PR2-00 intermittent challenge expiry remediation evidence

## Subjects and scope

- Frozen Phase 1 semantic baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115`.
- Prior formatter contract: `8c45e393c6ba68ab3989acaa4a319bc63c3bea89`.
- Original PR2-00 implementation: `5b65f6983dd627757ac7ab7b1fb6befe0a832573`.
- Prior evidence: `7bd3673d3892d02b17d3535b2585ed6f954dd7a5`.
- P1 clarification: `5a79d9cacc97ffbfd307d8c3f586d2521271194e`.
- Prior remediation implementation: `57c2bd5a0b556b879703d22ebb3e5d78a7cd3b8c`.
- Prior remediation evidence / failed review subject: `5ac921ed29083dce725809a9d64ae0739bff4c93`.
- This remediation implementation: `fd82490f457a2893c0f39f65d64a069d118e6521`.
- Scope: `tests/integration/phase2/test_pr2_00_challenges.py` only. No production source, Phase 1 source, or migration changed.

The previous independent review reported one failure in
`tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait`:
the application returned a successful binding after the reviewer observed PostgreSQL time
at or beyond expiry and released the held lock. That failed execution did not emit the
transaction, lock, or authorization timestamps, so its exact timestamp sequence is not
available and the failure has not been reproduced locally. It would be inaccurate to claim
that the production trigger or application accepted an expired challenge in a reproduced
run.

The test previously released the lock at the first database clock sample at or beyond
expiry. The bounded diagnostics found no production stale-time, timestamp precision,
timezone, row-refresh, or isolation defect. The best-supported classification is
`TEST_TIMING_MARGIN_BUG`: the test allowed effectively zero post-expiry scheduling margin.
The regression now waits until PostgreSQL time is at least 250 ms beyond expiry before
releasing the lock, verifies observed lock wait/acquisition and authorization timestamps,
and prints the complete trace before its assertions so any recurrence is diagnosable. This
classification is supported by test construction and successful stress, but is not a
reproduction of the reviewer's exact successful-consumption event.

## Temporal semantics and production path

The frozen rule is `issued_at <= authorization_time < expires_at`; equality is expired.
The application rejects `authorized_at >= expires_at`, and migration 0019's challenge
transition trigger permits consumption only when `OLD.issued_at <= clock_timestamp()` and
`clock_timestamp() < OLD.expires_at`. The final path rereads the challenge under
`SELECT ... FOR UPDATE` and samples fresh `clock_timestamp()` values after required locks.
It samples again after the inserts before commit. No production change was needed or made.

The test observed PostgreSQL 18.6, `SERIALIZABLE` isolation, database timezone `UTC`, and
`issued_at` / `expires_at` as `timestamp with time zone` with microsecond precision (6).
The returned Python datetimes were timezone-aware UTC. The lock monitor observed the
consumer backend waiting on the challenge `SELECT ... FOR UPDATE` with PostgreSQL wait type
`Lock` and wait event `transactionid`.

## Recorded successful denial trace

Captured from the final implementation using:

```bash
DATABASE_URL='postgresql+psycopg://researchbase_test:researchbase_test@127.0.0.1:55439/researchbase_pr2_test' \
  uv run pytest -o addopts='' -s \
  tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait -ra
```

All timestamps below are PostgreSQL-derived UTC timestamps with microsecond precision:

```text
challenge_id                  = 1c2949ac-5509-40a7-99dc-a0643b2b0961
challenge_issued_at           = 2026-10-03 05:31:42.844886+00:00
challenge_expires_at          = 2026-10-03 05:31:45.844886+00:00
tx_started_at                 = 2026-10-03 05:31:42.852026+00:00
lock_wait_started_at          = 2026-10-03 05:31:42.863048+00:00
expiry_crossed_at             = 2026-10-03 05:31:46.103710+00:00
lock_released_at_observed     = 2026-10-03 05:31:46.106680+00:00
lock_acquired_at              = 2026-10-03 05:31:46.106720+00:00
authorization_check_1_time    = 2026-10-03 05:31:46.112571+00:00
authorization_check_2_time    = 2026-10-03 05:31:46.112982+00:00
effect_result                 = DENY (ENROLLMENT_CHALLENGE_EXPIRED)
persisted challenge status    = ISSUED
persisted bindings            = 0
persisted binding events      = 0
```

`lock_released_at_observed` is sampled immediately after the controller rolls back the
lock-holding transaction; it is an observed post-release upper bound, not a server-side
timestamp taken inside the rollback operation. The test proves transaction start and
observed lock wait precede expiry, PostgreSQL time advances at least 250 ms past expiry
before release, and the lock is acquired and fresh authorization checks occur after expiry.

## Reproduction and stress

Before the test change, the isolated case passed 20/20 runs, the ordered bootstrap/challenge/
concurrency group passed 5/5 runs, and a full suite passed 1,817 tests with 2 skips. These
runs did not reproduce the reviewer failure.

After the test change:

- Isolated challenge expiry stress: 10 runs, 10 passed, 0 failed.
- Ordered `test_pr2_00_bootstrap.py`, `test_pr2_00_challenges.py`, and
  `test_pr2_00_concurrency.py` stress: 3 runs, all passed; 19 tests passed per run.
- Challenge + OWNER concurrency and temporal tests: 5 passed.
- Final concurrency suite, including challenge expiry and distinct OWNER further-wait:
  4 passed.
- Final PR2-00 unit, architecture, migration, challenge, temporal, concurrency, identity,
  and ownership command: 24 passed.
- Final full suite after the final assertions: 1,817 passed, 2 skipped, 0 failed (1,819
  collected). The skips are the existing PR11R2 migration matrix cases requiring
  `PR11R2_MIGRATION_DB_URL`.

## Formatter baseline delta

The repository-wide command remains `uv run ruff format --check .`; it was not narrowed or
reconfigured. Ruff is `0.12.12`.

- Exact original baseline: `e756b1392ee25c2753e0837bda8eb905df7de013`.
- Baseline command, run from an isolated `git archive` of that subject: exit 1; nine files
  reported (the inherited set recorded in the PR2-00 execution pack).
- Current command: exit 1; the same nine files reported, zero new failures.
- Changed-file formatter check:
  `uv run ruff format --check tests/integration/phase2/test_pr2_00_challenges.py`;
  1 file already formatted.
- Formatter gate: `PASS_VIA_BASELINE_DELTA`.

The nine inherited paths are `migrations/versions/0004_experiment_spec.py`,
`scripts/pr17dr_evidence.py`, `tests/integration/test_pr04_application.py`,
`tests/integration/test_pr04_schema.py`, `tests/integration/test_pr05_application.py`,
`tests/integration/test_pr05_schema.py`, `tests/integration/test_pr06_application.py`,
`tests/unit/domain/test_pr05_experiment.py`, and `tests/unit/test_pr17dr2_evidence.py`.
None was changed.

## Verification results

Commands run against the isolated local PostgreSQL 18 test database:

```text
PR2-00 focused unit/architecture/integration command: 24 passed
challenge + OWNER temporal/concurrency command: 5 passed
concurrency suite: 4 passed
full suite: 1,817 passed, 2 skipped, 0 failed
uv run ruff check .: PASS
uv run pyright: 0 errors, 0 warnings, 0 informations
repository-wide formatter raw command: FAIL on the same nine inherited baseline files
changed-file formatter check: PASS
git diff --check: PASS
```

Ruff lint and Pyright pass. The Phase 1 baseline tag still peels to
`d2400fbeca835c89bd802a4e9d647bda01cfd115`. This remediation changes one Phase 2 integration
test only; no frozen Phase 1 production source or historical migration was touched.

## PostgreSQL reviewer reproduction

The reviewer can use an isolated PostgreSQL 18 container, consistent with this run:

```bash
docker run --rm --name researchbase-pr2-review-postgres \
  -e POSTGRES_DB=researchbase_pr2_test \
  -e POSTGRES_USER=researchbase_test \
  -e POSTGRES_PASSWORD=researchbase_test \
  -p 55439:5432 postgres:18
```

In a second shell, from the repository root:

```bash
export DATABASE_URL='postgresql+psycopg://researchbase_test:researchbase_test@127.0.0.1:55439/researchbase_pr2_test'
uv run pytest -o addopts='' -s tests/integration/phase2/test_pr2_00_concurrency.py::test_challenge_expiry_after_lock_wait -ra
uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_concurrency.py tests/integration/phase2/test_pr2_00_temporal_auth.py -ra
uv run pytest -o addopts='' -ra
```

The container can be stopped with `docker stop researchbase-pr2-review-postgres`; `--rm`
removes it. The test credentials are local disposable credentials, not repository secrets.

## Evidence chronology

The evidence subject is a child of remediation implementation
`fd82490f457a2893c0f39f65d64a069d118e6521`; it certifies that subject and does not
self-reference. Review must independently rerun PostgreSQL tests and challenge the timing
and scheduling behavior. The previous reviewer failure remains unreproduced locally, so a
fresh PASS is required before the PR2-00 gate can close.
