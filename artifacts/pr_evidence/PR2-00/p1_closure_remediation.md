# PR2-00 P1 closure verification

## Subject and lineage

- Original authorized implementation start: `e756b1392ee25c2753e0837bda8eb905df7de013`.
- Formatter contract: `8c45e393c6ba68ab3989acaa4a319bc63c3bea89`.
- Prior PR2-00 implementation: `5b65f6983dd627757ac7ab7b1fb6befe0a832573`.
- Prior evidence-only subject: `7bd3673d3892d02b17d3535b2585ed6f954dd7a5`.
- P1 design clarification: `5a79d9cacc97ffbfd307d8c3f586d2521271194e`.
- Remediation implementation: `21d04de1ec5e11be11581f288a161826fa86377f`.
- Frozen Phase 1 semantic baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115` (`phase1-final-v4^{commit}` verified).
- Database migration: `0019_phase2_bootstrap_membership`, parent `0018_current_pointer_same_parent_integrity`.
- PostgreSQL used: 18.6.

This evidence closes only reviewer findings P1-A (observable TEMP-AUTH-01 timing proof) and P1-B (unspecified invalid legacy-state preflight). It does not include PR2-01 work.

## P1-A: TEMP-AUTH-01 timing evidence

The test instrumentation records PostgreSQL `transaction_timestamp()`, backend PID, actual `clock_timestamp()` samples used by the Application, the observed `pg_stat_activity` lock wait query/event, lock acquisition time, expiry, decision, and persisted row counts. No production observability fields were added. The raw recorded values from the PostgreSQL run are in [p1_closure_temporal_lock_waits.json](p1_closure_temporal_lock_waits.json).

`test_challenge_expiry_after_lock_wait` blocked on `actor_enrollment_challenges ... FOR UPDATE`; the transaction started and the observed wait began before expiry, then the row lock and final `clock_timestamp()` were observed after expiry. The command returned `DENY`; challenge status remained `ISSUED`, with zero binding and binding-event rows.

`test_owner_credential_expiry_after_lock_wait` blocked in `rb_phase2_lock_project`; it started and entered the observed lock wait before credential expiry, then acquired the project lock and checked fresh time after expiry. The command returned `DENY`. Counts for the pre-existing target membership, role, and their history rows stayed at one each.

`test_fresh_time_after_each_required_wait` is a distinct `assign_project_role` test. Its first successful OWNER check precedes a real wait on the target membership/actor `FOR UPDATE` query. The credential expires during that wait. The second check is strictly later than check one, after lock acquisition, and after expiry; the role assignment is denied before any target membership, role, or event count changes.

All recorded cross-expiry cases satisfy:

```text
tx_started_at < expiry_at
lock_wait_started_at < expiry_at
lock_acquired_at >= expiry_at
authorization_checked_at >= lock_acquired_at
authorization_checked_at > expiry_at
effect_result = DENY
```

The further-wait case additionally records `authorization_check_2_time > authorization_check_1_time` and a PostgreSQL lock wait between those checks. TEMP-AUTH-01 still requires all blocking locks, durable reread, then fresh `clock_timestamp()` authorization before effect.

## P1-B: frozen invalid legacy-state predicate

Architecture Correction Addendum A22 `LEGACY-STATE-01` and the PR2-00 execution pack define `VALID_LEGACY_STATE` as all of the following:

1. Every `projects.created_by` resolves to exactly one `actors.id`.
2. Every non-NULL `actors.external_key` is unique.
3. Every actor type is one of `HUMAN`, `AGENT`, or `SERVICE`.
4. Every project lifecycle value is one of `ACTIVE`, `ARCHIVED`, or `RETIRED`.

`INVALID_LEGACY_STATE` is the complement. Multiple actors and projects remain valid; Phase 1 contains no membership, OWNER, or bootstrap-root facts. `created_by` and `external_key` confer no authority. The predicate neither guesses ownership nor repairs data.

Migration 0019 locks `actors` and `projects` in `SHARE ROW EXCLUSIVE` mode and evaluates the predicate before extension creation or Phase 2 DDL. A failure raises stable `LEGACY_STATE_INVALID:<violation-codes>` text and leaves the Alembic revision at 0018 with no Phase 2 tables. Four real PostgreSQL cases cover orphan creators, duplicated external keys, invalid actor type, and invalid project lifecycle. Each unchanged invalid database was attempted twice; both error texts matched and Phase 1 row counts were preserved.

At runtime, first-owner bootstrap takes the actor/project table locks before its first legacy-state read, then takes the deployment lock, checks the predicate, and only then applies the existing empty-database rule. A valid nonempty database still returns `BOOTSTRAP_CLOSED`. The concurrent test commits contradictory duplicate-key state while bootstrap is visibly blocked on its required table lock; bootstrap sees the committed invalid state and returns `LEGACY_STATE_INVALID` with zero protected rows.

Per-project legacy enrollment locks and rereads the project and its creator actor before checking the applicable creator and lifecycle facts. Invalid state maps to the same `LEGACY_STATE_INVALID` Application error and fails before membership, role, or event writes. Both bootstrap and enrollment retry tests compare the full stable error dictionary. A valid legacy project control still enrolls as one ACTIVE membership with one open OWNER role. HTTP maps the error to 409 and CLI maps it to exit 4.

Detailed cases and results are in [p1_closure_legacy_preflight.json](p1_closure_legacy_preflight.json).

## Verification

All commands below ran against PostgreSQL 18.6 where database access applies.

| Area | Command or test set | Result |
|---|---|---|
| PR2-00 PostgreSQL integration | `uv run pytest -o addopts='' -ra tests/integration/phase2` (33 collected) | 33 passed in the final full regression |
| Challenge cross-expiry | `test_challenge_expiry_after_lock_wait` | Passed with timestamp and zero-consumption proof |
| OWNER cross-expiry | `test_owner_credential_expiry_after_lock_wait` | Passed with timestamp and unchanged protected counts |
| Further wait | `test_fresh_time_after_each_required_wait` | Passed with two distinct authorization times and an intervening real wait |
| Legacy-state migration cases | `test_legacy_state_preflight_fails_before_phase2_ddl_and_is_deterministic` (4 parameter cases) | 4 passed |
| Legacy-state Application cases | Invalid bootstrap, invalid legacy enrollment, and table-lock race tests | Passed; valid legacy enrollment control passed |
| Migration | Full PR2-00 migration tests (8 collected) | Passed, including fresh/0018 upgrade, downgrade, refusal, and Phase 1 snapshot checks |
| Architecture | `uv run pytest -o addopts='' -ra tests/architecture` | 57 passed |
| Error contract | focused ErrorCode, HTTP/CLI mapping tests | 8 passed |
| Logging order regression | contaminating bootstrap predecessor + four order-sensitive logging/redaction tests | 5 passed |
| Full regression | `uv run pytest -o addopts='' -ra` | 1,813 passed, 2 skipped, 0 failed (1,815 collected) |
| Ruff | `uv run ruff check .` | Passed: all checks passed |
| Pyright | `uv run pyright` | Passed: 0 errors, 0 warnings, 0 informations |
| Diff whitespace | `git diff --check e756b1392ee25c2753e0837bda8eb905df7de013` | Passed |

The two skips are existing PR11R2 migration tests that require `PR11R2_MIGRATION_DB_URL`. The full suite emitted 46 Alembic `path_separator` deprecation warnings.

## Formatter baseline delta

Ruff 0.12.12 ran the required repository-wide check on a clean `git archive` of exact starting subject `e756b1392ee25c2753e0837bda8eb905df7de013` and on the current implementation tree:

```text
uv run ruff format --check .
baseline exit = 1
current exit = 1
```

Both failure sets are identical:

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

`NEW_FORMATTER_FAILURES = ∅`; `RESOLVED_INHERITED_FAILURES = ∅`. All 29 Git-derived added/modified Python files pass `ruff format --check`. No inherited formatter-failing file was modified, and formatter configuration and command are unchanged.

```text
RAW_FORMATTER_COMMAND = FAIL_INHERITED_BASELINE
FORMATTER_GATE = PASS_VIA_BASELINE_DELTA
```

## Phase 1 integrity

The `phase1-final-v4` peeled commit remains `d2400fbeca835c89bd802a4e9d647bda01cfd115`. This remediation changes only migration 0019 and Phase 2 Application, persistence, transport error mapping, and tests. It changes no Phase 1 production source or historical migration. The earlier PR2-00 harness changes pin Phase 1-only regression setup to frozen revision 0018; the Phase 1 assertions remain, while the separate Phase 2 migration tests cover 0018→0019. No Phase 1 semantic drift was observed.

## Fresh PostgreSQL 18 reviewer setup

The integration fixture creates uniquely named disposable databases from `DATABASE_URL` and drops them after each test. For an isolated fresh reviewer environment, the local container credentials below are test-only and contain no secret:

```bash
docker pull postgres:18-alpine
docker run -d --rm --name researchbase-pr2-review-postgres \
  -e POSTGRES_USER=researchbase_test \
  -e POSTGRES_PASSWORD=researchbase_test \
  -e POSTGRES_DB=researchbase_pr2_test \
  -p 127.0.0.1:55439:5432 postgres:18-alpine
docker exec researchbase-pr2-review-postgres \
  pg_isready -U researchbase_test -d researchbase_pr2_test
export DATABASE_URL='postgresql+psycopg://researchbase_test:researchbase_test@127.0.0.1:55439/researchbase_pr2_test'
uv sync --locked
uv run pytest -o addopts='' -ra tests/integration/phase2
uv run pytest -o addopts='' -ra
docker rm -f researchbase-pr2-review-postgres
```

The container's `POSTGRES_USER` is its local superuser so the fixture can create and drop disposable test databases. Reviewers can omit the full-suite command if only reproducing PR2-00 checks. Do not reuse the illustrative credentials outside this local disposable container.
