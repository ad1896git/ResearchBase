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
| Six-shard runner's own quick pre-check | 48 passed, 33 warnings in 30.52s |
| Six-shard run | Blocked before shards by sandbox permissions; interrupted with exit 130 |
| Separate single-process full-corpus run on an isolated PostgreSQL DB | Interrupted (130); incomplete, no full-suite PASS claimed |

The repaired pre-check includes the sole-OWNER scheduled-expiry test. Its existing
deferred `ck_project_owner_coverage` constraint rejects the scheduled close at
commit, and the existing 23514 mapping returns `OWNER_COVERAGE_GAP`; the test
asserts rollback to an open role at row version 1 with no CLOSED event.

No production semantics, schema, migration, dependency, governing harness, commit,
branch, or push was added during this remediation. No broader Phase 2 gate is
asserted.

The exact requested chain was invoked:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

After its successful static checks and pre-check, the runner could not create its
shared mutex under the parent project's `.pipeline/logs`, which is outside the
sandbox's writable roots. It printed:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

The blocked runner was interrupted (130). Its script, queue, locks and duration
registry were not modified. This is not a passing six-shard check. The separate
single-process full-corpus run uses the same pytest options and every sorted
`tests/**/test_*.py` file against a fresh PostgreSQL database upgraded to head;
it does not claim the sharded runner succeeded. Its pytest invocation is:

```sh
uv run pytest -o addopts= -q -rfE -p no:cacheprovider <all sorted test files>
```

The optional single-process fallback was stopped before completion. The external
runner's timing registry totals 10,334 seconds across 517 timed files; this
fallback would not establish that the exact shared sharded command passed. No
full-suite counts or gate success are claimed from that interrupted attempt.
Completing the exact check requires a session allowed to write the shared
`.pipeline/logs` mutex directory and `.pipeline/test_durations.json` registry.
The full runner must be retried there after this fixture repair.
