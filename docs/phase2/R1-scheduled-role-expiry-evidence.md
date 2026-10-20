# R1 scheduled project role expiry — implementation evidence

Owner authorization: 2026-10-20, first slice of
`docs/proposals/R1_Scheduled_Role_Expiry_Contract_DRAFT.md`.

The contract status was updated before implementation. `CloseProjectRole` now
accepts optional `effective_until`, validates and normalizes it to UTC, rejects
backdating at post-lock database time, and uses the same target timestamp for the
role interval and immutable CLOSED event. Existing SERIALIZABLE isolation,
project → role → owner-facts lock order, and both authorization checks remain.
The three specified constraint mappings were added to the existing UoW normalizer.
There are no schema, migration, repository-port, transport, or dependency changes.

Tests cover default/explicit expiry, invalid values/reasons/intervals, constraint
mapping, all four non-OWNER roles, sole-OWNER rollback, open-ended successor
coverage, scheduled-role retries, request conflicts, membership termination and
reactivation, same-role reassignment across expiry, actual blocked writes across
expiry, and lock-free reads before/after expiry.

Existing equivalent used for temporal read evidence: B02's
`begin_strategy(read_only=True)` delegates to `begin_resolution(read_only=True)`
and establishes one REPEATABLE READ, READ ONLY snapshot. Its existing protected
capture query provides the read boundary; no new identity read DTO or port method
was introduced. Tests inspect both SQL and live `pg_locks`: ordinary SELECT
`AccessShareLock` and nonblocking predicate `SIReadLock` are permitted; explicit
relation exclusion locks, advisory locks, and tuple locks are absent.

The downstream writer retains the exact first statement
`LOCK TABLE <strategy_candidate_promotion_repository.S inventory> IN SHARE MODE`
and READ COMMITTED isolation. No downstream production file was changed.

PostgreSQL reported `18.6 (Homebrew)`. One observed cross-expiry run recorded
these database-derived UTC instants:

| Coordinate | 2026-10-20 UTC |
| --- | --- |
| Transaction started | 05:25:12.055968 |
| Lock wait observed | 05:25:12.059829 |
| Scheduled expiry | 05:25:14.994989 |
| Required locks acquired | 05:25:14.997621 |
| Authorization checked | 05:25:14.999667 |

Outcome: `FORBIDDEN`. Persisted deltas for strategy question admissions,
research questions, and research question versions: `[0, 0, 0]`.

## Review remediation and verification

The earlier local run of the three files in ownership-first order reported 31
passes, but did not establish acceptance: the loop's bootstrap-first pre-check
failed. That earlier result and the initial read-only review missed an
order-dependent fixture-registration error. They are superseded by the reruns
below; the earlier full-suite check never reached its shards.

Before editing, the exact pre-check was reproduced with the loop's options and
changed-file order (bootstrap, ownership, temporal auth, unit):

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider -x tests/integration/phase2/test_pr2_00_bootstrap.py tests/integration/phase2/test_pr2_00_ownership.py tests/integration/phase2/test_pr2_00_temporal_auth.py tests/unit/test_phase2_identity_role_expiry.py
```

Relevant error text:

```text
_ ERROR at setup of test_application_schedules_non_owner_role_expiry[REVIEWER] _
E       fixture 'role_expiry_env' not found
ERROR tests/integration/phase2/test_pr2_00_ownership.py::test_application_schedules_non_owner_role_expiry[REVIEWER]
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
22 passed, 23 warnings, 1 error in 12.84s
```

The Phase 2 conftest loads `m3`, which imports ownership's existing SQL fixture
helper. Ownership is therefore imported during conftest initialization, when its
module-level `pytest_plugins` does not reliably register the bootstrap module's
fixture. The fixture was missing when ownership was later collected.

`role_expiry_env`, `_expiry_role`, `_schedule_expiry`, the bootstrap proof verifier,
and the R1 lock-wait helper now live in `tests/integration/phase2/r1_support.py`.
Phase 2 conftest explicitly exposes the shared R1 and B02 fixtures. Ownership and
temporal auth have no cross-test-module imports or `pytest_plugins` declarations.
The reactivation test proves that its returned ID resolves to a new ACTIVE
membership for the expected actor/project, has no restored roles, and leaves the
old role's membership, expiry, and row version unchanged.

Commands below use exported `UV_CACHE_DIR=/tmp/researchbase-lane66-uv` because the
default user cache is outside the sandbox's writable roots.

| Rerun | Result |
| --- | --- |
| Exact four-file pre-check above | 48 passed, 33 warnings in 27.31s |
| Same pre-check options, three PostgreSQL files only, bootstrap → ownership → temporal auth | 31 passed, 33 warnings in 26.35s |
| `uv run pyright` in exact requested chain | 0 errors, 0 warnings, 0 informations |
| `uv run ruff format --check .` in exact requested chain | 785 files already formatted |
| `uv run ruff check .` in exact requested chain | All checks passed |
| `git diff --check HEAD` in exact requested chain | Exit 0 |
| Loop-run six-shard runner's own quick pre-check | 48 passed, 33 warnings in 32.98s |
| Loop-run six-shard run | Exit 0; 12037 passed, 67 skipped, 10156 warnings across six shards |
| Separate single-process full-corpus run on an isolated PostgreSQL DB | Interrupted (130); incomplete, no full-suite PASS claimed |

The repaired pre-check includes the sole-OWNER scheduled-expiry test. Its existing
deferred `ck_project_owner_coverage` constraint rejects the scheduled close at
commit, and the existing 23514 mapping returns `OWNER_COVERAGE_GAP`; the test
asserts rollback to an open role at row version 1 with no CLOSED event.

No production semantics, schema, migration, dependency, governing harness, commit,
branch, or push was added during this remediation. No broader Phase 2 gate is
asserted.

The loop ran the exact requested chain outside the authoring sandbox:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The recorded result in
`.pipeline/runs/t163_impl_r1/20261020-012123/r2_check.txt` is `exit 0`.
The six-shard check completed successfully; the earlier sandbox-blocked attempt
and interrupted single-process fallback do not describe this completed loop run.

| Shard | Recorded result |
| --- | --- |
| 0 | 1756 passed, 1020 warnings in 3307.57s (0:55:07) |
| 1 | 1555 passed, 1711 warnings in 3304.80s (0:55:04) |
| 2 | 3844 passed, 1354 warnings in 3154.41s (0:52:34) |
| 3 | 1814 passed, 66 skipped, 1791 warnings in 3373.83s (0:56:13) |
| 4 | 1720 passed, 1 skipped, 2219 warnings in 3074.52s (0:51:14) |
| 5 | 1348 passed, 2061 warnings in 3268.28s (0:54:28) |

Aggregate recorded result: **12037 passed, 67 skipped, 10156 warnings** across
six shards. This evidence comes from the loop's check, not an author-run full suite.
