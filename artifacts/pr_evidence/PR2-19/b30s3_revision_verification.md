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

## Earlier interrupted full-check attempt (superseded by loop evidence)

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
That local attempt did not pass; the loop subsequently completed the full check below.
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

## Corrected loop full-run evidence

Source: `.pipeline/runs/t162_impl_b30s3/20261020-012123/r2_check.txt`.
The loop's real full run completed with **exit 0: 12051 passed, 67 skipped**
(`10257 warning` in the aggregate output). Quick pre-check: `166 passed,
197 warnings in 196.70s (0:03:16)`. Shard pass counts: 1510, 1687, 3939,
1490, 1629, 1796; skips: 0, 0, 0, 1, 0, 66. This supersedes the earlier
interrupted local runner attempt above. This follow-up does not rerun the whole suite.

## Write isolation evidence

`tests/integration/phase2/b30_observations.py::sql_protocol` probes PostgreSQL
`SHOW transaction_isolation` and `SHOW transaction_read_only` after every
observed statement. `assert_first_share` defaults to `READ_COMMITTED`, asserts
that the first write statement is the exact SHARE inventory in that isolation,
and asserts every statement in each write transaction stays READ COMMITTED and
read-write. Both G2 and G4 suffix tests invoke it. Read-only preflight transactions
are separately asserted REPEATABLE READ. These are actual server settings.

Final disposition of original revision: focused suffix evidence above plus the
loop's full-run result; the full PR2-19 gate remains BLOCKED. Director follow-up
resolves AQ-S3-01..07; AQ-S3-08 remains OPEN. Follow-up focused verification is
recorded separately below.


## Director follow-up 2026-10-20

Tests and docs only. AQ-S3-01..07 follow the director's B02/B03 precedence;
AQ-S3-08 remains OPEN and the informational full gate remains fail-closed.
G2 now checks exact B02 §5.2 capture/question/hypothesis hashes, DRAFT question
parent composition, NULL scientific hash state, advisory SQL/keys, distinct-ID
duplicates, other-actor replay denial and inaccessible-source precedence. G4
checks the B03 §5.2 candidate/input literals, existing receipt/admission/session
closure, NULL scientific hash state, HUMAN admission, AGENT denial through
`promote_discussion_to_hypothesis`, advisory SQL/keys and transcript mismatch
precedence. AGENT denial uses an Application-created unbound AGENT, with no
SQL-forged actor type, membership or subject binding; it is not a positive bound
AGENT fixture or evidence resolving AQ-S3-08.

Duplicate-loser races retain the winner's uncommitted Application write until a
second backend is witnessed via `pg_blocking_pids`; `pg_stat_activity` must show
`wait_event_type='Lock'`. G2 losers wait on relation locks and return
DUPLICATE_CONTENT after the winner commits. G4 waits on the landed receipt or
candidate advisory lock; same request returns the winner and distinct request
returns DUPLICATE_CONTENT. Whole-command StateDelta proves exactly one output.

All commands use `UV_CACHE_DIR=/private/tmp/rb-lane65-uv-cache`.

Static checks (each exit 0):

```sh
uv run pyright
uv run ruff format --check .
uv run ruff check .
git diff --check HEAD
```

Observed: `0 errors, 0 warnings, 0 informations`; `783 files already formatted`;
`All checks passed!`; diff check emitted no output.

Focused unit and architecture command (exit 0):

```sh
uv run pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/unit/phase2/test_b02_strategy_promotion_hashes.py tests/unit/phase2/test_b02_strategy_promotion_uow.py tests/unit/phase2/test_b02_strategy_promotion_contract.py tests/architecture/test_pr2_19_boundaries.py tests/architecture/test_b02_strategy_promotion_boundaries.py -x --tb=short
```

`235 passed, 45 warnings in 50.19s`.

Isolated backend-wait command (exit 0):

```sh
uv run pytest tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py -k 'duplicate_loser or two_connection_barrier' -s -x --tb=short
```

`4 passed, 53 deselected, 12 warnings in 14.82s`. Actual server witnesses:

```text
G2_DUPLICATE_WAIT question 1099 1103 ('Lock', 'relation')
G2_DUPLICATE_WAIT hypothesis 1244 1248 ('Lock', 'relation')
G4_RECEIPT_CANDIDATE_WAIT True 1321 1347 ('Lock', 'advisory')
G4_RECEIPT_CANDIDATE_WAIT False 1420 1454 ('Lock', 'advisory')
```

The two numbers are winner and waiter backend PIDs; both are real PostgreSQL
backends. The winner was released only after these observations.


Development diagnostics, all corrected before final verification:

- The complete focused suffix command shown below first stopped at `1 failed,
  9 passed, 21 warnings in 19.33s` (exit 1): the test incorrectly queried
  scientific `hash_scheme` as a physical column. It now checks persisted NULLs
  plus repository-loaded `hash_scheme=None`.
- Subsequent attempts of that same command stopped at `1 failed, 35 passed,
  99 warnings in 92.47s` and `1 failed, 35 passed, 99 warnings in 100.75s`
  (both exit 1). The new actor fixture supplied uppercase text instead of the
  existing `ActorType.AGENT` enum. The latter attempt had already loaded the
  old test while the correction was being prepared.
- `uv run pytest tests/integration/phase2/test_pr2_19_discussion.py -x --tb=short`
  diagnosed the same enum issue (`1 failed, 1 passed, 6 warnings in 4.46s`,
  exit 1), then the closure query's incorrect question-input column spelling
  (`1 failed, 4 passed, 15 warnings in 17.21s`, exit 1). The query now uses
  the landed `discussion_session_question_inputs.version_id`.
- `uv run pytest tests/integration/phase2/test_pr2_19_discussion.py -k 'explicit_manual or forbidden_promotion' -x --tb=short`
  verified both corrections: exit 0, `5 passed, 21 deselected, 15 warnings in
  11.68s`.

These were test-authoring defects, not changes to production behavior; no failed
or deselected case is reported as passing.


Final focused PostgreSQL command, repeated on the final test code:

```sh
uv run pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py -x --tb=short
```

First completed final run: exit 0, `60 passed, 171 warnings in 145.67s (0:02:25)`.

Second completed final run: exit 0, `60 passed, 171 warnings in 138.66s (0:02:18)`.
Both complete runs include the G2 and G4 modules and dependency inventory, with
zero skips. Their 171 warnings are the existing Alembic `path_separator`
deprecation warnings. No production/migration edits were made between those runs.

Final scope checks:

```sh
git diff --check HEAD
git diff --name-only HEAD -- src migrations
git status --short
```

The first two commands exited 0 with no output. Status lists exactly seven
modified files: this evidence, the AQ record, the S3 draft, the G2/G4 integration
modules, their dependency inventory and the unit report contract. No full-suite
command, commit, push or branch creation was performed in this follow-up.
AQ-S3-08 and the full PR2-19 gate remain OPEN/BLOCKED respectively.
