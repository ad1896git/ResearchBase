# B30-S3 reviewer remediation evidence — 2026-10-20

Scope: tests/support only, approved status line, and reviewer-requested Architecture
Questions. No production code, migrations, schema, dependency, branches or commits.
The complete PR2-19 gate remains BLOCKED. Unresolved cases are recorded with exact
S3/owner quotes and source locations in
`docs/proposals/B30S3_Architecture_Questions_2026-10-20.md` (AQ-S3-01 through 08).
No pending requirement was converted to a pass, skip or xfail.

## Environment

All successful uv commands below used
`export UV_CACHE_DIR=/private/tmp/rb-lane65-uv-cache` to keep uv writes inside
allowed temporary storage. The initial literal isolated command without that
setting exited 2 before pytest: uv could not open
`/Users/fengwang/.cache/uv/sdists-v10/.git` (Operation not permitted).
`RB_TEST_ADMIN_URL` and `DATABASE_URL` were supplied by the lane environment;
real disposable PostgreSQL 18 databases were used. Credentials/URLs are not
reproduced in this evidence file.

## Reported PR2-04 failure, isolated

Exact command after the cache environment setting:

```sh
uv run pytest tests/integration/phase2/test_pr2_04_maximum_accounting_acceptance.py::test_pg_maximum_32_queries_96_attempts_and_no_97th_reservation -x
```

First isolation: exit 0, `1 passed, 1 warning in 4.30s`.
Repeated isolation: exit 0, `1 passed, 1 warning in 2.72s`.
Full second stdout is in `b30s3_accounting_isolation.log`. There is no failing
traceback in either isolation. No baseline failure was established. The previously
reported sharded failure may be load-sensitive; this is a possibility, not a
proven diagnosis. That test and its production path remain unchanged.

## Focused unit and architecture

```sh
uv run pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/architecture/test_pr2_19_boundaries.py -x --tb=short
```

Exit 0: `132 passed, 44 warnings in 23.91s`.

## Static checks

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD
```

Final stdout retained in `b30s3_final_static.log`: exit 0; Pyright `0 errors,
0 warnings, 0 informations`; `783 files already formatted`; Ruff `All checks
passed!`; diff check no stdout. These checks were rerun after test fixes.

## Requested full check — incomplete, not PASS

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The first attempt reached the runner quick pre-check, which caught the newly added
role fixture using principals from different deployments (`1 failed, 44 passed,
119 warnings in 48.82s`); no shards ran. The fixture was corrected to use its
own deployment's principal, through owning identity Application commands.

The next attempt passed static checks and its quick pre-check:
`162 passed, 185 warnings in 157.77s (0:02:37)`. It then repeatedly failed on:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

These shared runner paths are outside the writable workspace roots. The runner
could not acquire its shared concurrency slot and was interrupted (reported
exit 1); no shard results exist for this run. Full stdout is retained in
`b30s3_requested_check.log`. No runner/mutex bypass or external file edit was used.
The full command has NOT passed and requires the loop's runner environment.
The final G4 saved-role replay case and subsequent observed role-wait variants
were added after that pre-check collected tests and are verified separately.

## Changes exercised

- G2: native candidate isolation, capture/explicit question/adapted hypothesis
  composition with and without an organizational question parent, independently
  hashed CAS bytes, command StateDelta inventories, compute/CAS outside DB
  transactions, first SHARE write inventories, fresh lock-free snapshot reads,
  exact replay/changed-payload conflicts, invalid selectors/no answer, corrupted
  CAS, immutable histories, deferred creation guard denial and fault rollback.
- G4: owning-command session/turn/close/transcript binding, legacy HUMAN/AGENT
  request_promotion denial, manual HUMAN hypothesis admission, exact command
  deltas, CAS bytes/digest, first SHARE and lock-free restart snapshot, exact
  replay/changed payload conflict, missing roots, OPEN/unbound denial, missing/
  corrupted CAS, immutable receipts/admissions, missing-admission guard failure,
  insert/constraint rollback, same-request two-backend barrier serialization.
- Both: credential revocation while PostgreSQL witnesses the SHARE wait; owning
  Application role closures during witnessed waits; historical replay/read after
  writer loss with VIEWER entitlement retained and fresh writes denied.
- Reports: concrete labels restricted to G2/G4, landed owners marked available,
  historical blockers preserved, unresolved S3 cases explicitly BLOCKED, full
  gate remains fail-closed and availability is not acceptance.

## Focused PostgreSQL final results

See appended results below and the retained stdout logs.

Final current suffix command (after all role-wait variants):

```sh
uv run pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py --tb=short -x
```

Exit 0: `54 passed, 153 warnings in 151.32s (0:02:31)`.
Full stdout: `b30s3_final_suffixes.log`.

The newly added role-replay/wait variants were also isolated with:

```sh
uv run pytest tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py -k 'historical_replay or saved_replay' -x --tb=short
```

Exit 0: `6 passed, 45 deselected, 18 warnings in 13.73s`. Deselecting by an
explicit focused `-k` selector is not a skipped or passed disputed S3 obligation.

Focused owner regression command (planned single promotion files substituted by
existing split owner suites):

```sh
uv run pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_replay.py tests/integration/phase2/test_b02_strategy_concurrency.py tests/integration/phase2/test_b02_strategy_schema.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_10_binding_contract.py --tb=short -x
```

This run collected before the final G4 replay and extra role-wait variants. Its
current suffix coverage is complemented by the final 54-case run above.

Owner regression result: exit 0,
`212 passed, 534 warnings in 527.92s (0:08:47)`.
Full stdout: `b30s3_focused_postgres.log`. This count is not a full-suite count.

Final disposition: implemented and verified the non-conflicting G2/G4 test
composition, report contracts, and architecture checks. Disputed expectations
remain explicit Architecture Questions. The requested full sharded command is
still incomplete because its shared runner paths cannot be written in this
sandbox. No full-gate success or resolution of those owner questions is claimed.
