# PR2-00 P1 Closure — NULL Legacy-State Remediation

This evidence certifies the follow-up remediation subject `57c2bd5a0b556b879703d22ebb3e5d78a7cd3b8c`. The work is limited to the prior review's remaining P1 finding: SQL `NOT IN` predicates return UNKNOWN for NULL values, so a NULL `actor_type` or `lifecycle_status` could evade the frozen `LEGACY-STATE-01` predicate.

## Lineage and review findings

The authorized starting subject is `e756b1392ee25c2753e0837bda8eb905df7de013`; the Phase 1 frozen semantic baseline is `d2400fbeca835c89bd802a4e9d647bda01cfd115`. The formatter contract is `8c45e393c6ba68ab3989acaa4a319bc63c3bea89`. Original PR2-00 implementation/evidence subjects are `5b65f6983dd627757ac7ab7b1fb6befe0a832573` and `7bd3673d3892d02b17d3535b2585ed6f954dd7a5`. The P1 clarification subject is `5a79d9cacc97ffbfd307d8c3f586d2521271194e`; the first remediation/evidence subjects are `21d04de1ec5e11be11581f288a161826fa86377f` and `7d9e01f84e967541c002635bbfb71feddc4173e5`.

The first fresh reviewer returned `FAIL`, `NEW_P0_GAPS=0`, `NEW_P1_GAPS=1`, `NEW_P2_GAPS=0`. It confirmed P1-A closed and identified that SQL `WHERE actor_type NOT IN (...)` and its lifecycle equivalent omit NULL rows. The reviewer could not run PostgreSQL because its isolated context lacked Docker socket access. The remediation adds explicit `IS NULL OR NOT IN (...)` clauses in both migration and runtime global preflight queries and tests them against PostgreSQL with the frozen CHECK and NOT NULL constraints removed.

## Legacy-state proof

The four normative legacy invariants remain unchanged: each project creator resolves to an actor; non-NULL external keys are unique; actor type is one of HUMAN/AGENT/SERVICE; lifecycle is one of ACTIVE/ARCHIVED/RETIRED. The last two predicates now reject both NULL and out-of-domain values. No heuristic selection or repair is performed.

`test_legacy_state_preflight_fails_before_phase2_ddl_and_is_deterministic` has six PostgreSQL cases: orphan creator, duplicate external key, out-of-domain actor type, NULL actor type, out-of-domain lifecycle, and NULL lifecycle. Each invalid database was attempted twice; the same stable error recurred, Alembic remained at 0018, no Phase 2 tables were created, and legacy rows were unchanged. The new NULL cases drop the relevant frozen CHECK and NOT NULL constraints to model altered/restored state explicitly.

`test_null_legacy_state_rejects_bootstrap_without_protected_writes` covers NULL actor type and NULL lifecycle through Application bootstrap. Both return the stable `LEGACY_STATE_INVALID` error on retries and create zero bootstrap, membership, or role-event rows. Existing valid-state, concurrent-preflight, enrollment, and atomicity cases remain in the full PostgreSQL suite. Structured case results are recorded in [p1_closure_null_legacy_preflight.json](p1_closure_null_legacy_preflight.json).

## TEMP-AUTH-01 evidence

The exact transaction-start, lock-wait, expiry, lock-acquired, authorization-check, denial, and protected-effect timestamps were recaptured on this remediation subject with PostgreSQL 18.6. The distinct further-wait case has two actual authorization samples separated by a PostgreSQL-observed lock wait; its second sample occurs after expiry and denies the protected role assignment. See [p1_closure_null_temporal_lock_waits.json](p1_closure_null_temporal_lock_waits.json) for raw structured output. P1-A remains closed.

## Verification

| Verification | Command / result |
| --- | --- |
| PR2-00 PostgreSQL integration, including challenge, temporal, concurrency, migration, and preflight tests | `uv run pytest -o addopts='' -ra tests/integration/phase2`: 37 passed |
| Migration NULL and legacy preflight regressions | 6 migration parameter cases passed; both Application NULL cases passed |
| Timestamp proof after remediation | Three `test_pr2_00_concurrency.py` cross-expiry cases passed; raw timestamps are in the JSON evidence |
| Logging-order predecessor and regressions | Contaminating bootstrap + four logging/redaction tests + migration logger regression: 6 passed |
| Architecture | `uv run pytest -o addopts='' -ra tests/architecture`: 57 passed |
| Full regression | `uv run pytest -o addopts='' -ra`: 1,817 passed, 2 skipped, 0 failed (1,819 collected) |
| Ruff | `uv run ruff check .`: passed |
| Pyright | `uv run pyright`: 0 errors, 0 warnings, 0 informations |
| Changed-file formatting | All four Python files changed by this remediation pass `ruff format --check` |
| Whitespace | `git diff --check`: passed |

The two skips are the existing PR11R2 migration matrix cases requiring `PR11R2_MIGRATION_DB_URL`. The shared full-suite database was kept at the Phase 1 endpoint `0018_current_pointer_same_parent_integrity`; the isolated PR2-00 fixture upgrades disposable per-test databases to 0019. PostgreSQL reported version 18.6.

## Formatter baseline delta

The exact required command remains `uv run ruff format --check .`. Ruff 0.12.12 returned exit 1 on the exact clean starting subject `e756b1392ee25c2753e0837bda8eb905df7de013` and on the PR2-00 tree. Both failure sets are identical: `migrations/versions/0004_experiment_spec.py`, `scripts/pr17dr_evidence.py`, `tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`, `tests/integration/test_pr05_application.py`, `tests/integration/test_pr05_schema.py`, `tests/integration/test_pr06_application.py`, `tests/unit/domain/test_pr05_experiment.py`, and `tests/unit/test_pr17dr2_evidence.py`. `NEW_FORMATTER_FAILURES = []`; all four remediation-changed Python files are formatted. The nine inherited files were not changed for style.

`RAW_FORMATTER_COMMAND = FAIL_INHERITED_BASELINE`; under `FORMAT-BASELINE-01`, `FORMATTER_GATE = PASS_VIA_BASELINE_DELTA`.

## Phase 1 and reviewer PostgreSQL setup

The peeled `phase1-final-v4` tag still equals `d2400fbeca835c89bd802a4e9d647bda01cfd115`. This remediation changes no Phase 1 production file or historical migration; it only changes the still-unaccepted Phase 2 migration 0019, its runtime preflight query, and tests. Phase 1 fixture pinning to 0018 remains test-harness adaptation; Phase 1 assertions remain intact and Phase 2 tests cover 0018→0019.

The integration fixture creates uniquely named disposable databases from `DATABASE_URL`. A fresh reviewer can reproduce the DB setup with the documented test-only local credentials below; if sandbox policy blocks Docker or localhost by default, the reviewer should request the permitted command-level access rather than count the DB suite as passing without execution.

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
uv run alembic upgrade 0018_current_pointer_same_parent_integrity
uv run pytest -o addopts='' -ra tests/integration/phase2
uv run pytest -o addopts='' -ra
docker rm -f researchbase-pr2-review-postgres
```

The URL credentials are disposable local test credentials, not secrets. The test database role needs permission to create/drop disposable databases. The evidence-only commit that contains this report does not certify itself; this report certifies implementation subject `57c2bd5a0b556b879703d22ebb3e5d78a7cd3b8c`.
