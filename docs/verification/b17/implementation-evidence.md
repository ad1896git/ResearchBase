# B17 prepared-package freeze — post-review verification

This report records the post-review commands and their final results. Earlier
failed development runs remain archived; their counts are not used as acceptance
results here. The full requested check is **BLOCKED / NOT PASS** in this sandbox.

## Corrections

All current-head assertions in the reviewer's nine named migration files now
expect `0065_b17_prepared_package_freeze`. Existing migration inventory entries
and historical byte baselines are unchanged; 0065 is appended to the inventories.

The [archived failure excerpt](logs/expiry-original-failure.txt) shows the old
expiry-replay failure occurred during the **initial freeze**, at
`application/approval.py`'s final advancing-clock expiry check, before replay.
The two-second grant expired during fixture setup and initial freeze. The
`b17_authorization_checked_at` DETAIL path was not the failing path. The fixture
now allows thirty seconds for setup and derives its polling deadline from the
remaining database-observed lifetime. The three real lock-wait expiry tests also
allow setup time while retaining the original acquisition/authorization ordering
assertions and unchanged-state checks. Production expiry checks are unchanged.

The proposal's first line is exactly:

> APPROVED by owner 2026-10-18 — first slice authorized for implementation

Confirmed with `git diff HEAD -- docs/proposals/B17_Prepared_Package_Freeze_Contract_DRAFT.md`.

## Current verification

Commands are recorded verbatim in [commands.txt](commands.txt). Tests use real
local PostgreSQL 18.6 and existing uv dependencies. No full-suite success is
inferred from focused checks.

| Post-fix command/group | Result |
| --- | --- |
| Final standalone Pyright/format/Ruff/HEAD-whitespace prefix | Exit 0; 0 type errors/warnings, 710 files formatted, Ruff passed |
| Exactly the nine reviewer-listed migration test files | 164 passed, 0 failures, 371 warnings, 514.21s |
| Complete original 99-case B17 acceptance command | 99 passed, 0 failures, 389 warnings, 798.61s |
| Both B17 unit files and B17 architecture file | 64 passed, 0 failures, 0.97s |
| Refreshed table/grant/deferred expiry witnesses | 3 passed, 0 failures, 12 warnings, 54.82s |
| Requested Pyright/format/Ruff/HEAD-whitespace/sharded-suite chain | INCOMPLETE: static prefix passed; runner attempt interrupted because central runner writes are forbidden; exit 1; sharded suite NOT RUN |

The 99-case command includes all five B17 integration files plus the G7 suffix
and dependency inventory. The additional 64-case command covers both B17 unit
files and the B17 architecture file. Thus every B17 test file is included, without
mislabeling the literal all-B17 file selection as 99 cases.

The requested chain is:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

`UV_CACHE_DIR=/tmp/rb-b17-uv` is exported for the permitted dependency cache.
The runner must write its mutex under
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs` and update
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/test_durations.json`.
Those paths are outside the session's writable roots. A direct temporary-file
write probe returned `PermissionError: [Errno 1] Operation not permitted` for the
mutex directory. The runner and its mandatory concurrency mutex are unchanged.
Writable runner paths or execution outside this sandbox are required to complete
that exact chain; focused results do not substitute for it. The runner attempt was
stopped through its execution session after the write denial was confirmed. That
interrupted its changed-file precheck, producing a nonzero exit. The [captured
check transcript](logs/reviewer-exact-check.txt) is explicitly not a PASS result.
No sharded-suite count is claimed. The runner and its mutex were not bypassed.

## Historical migration integrity

The [historical migration audit](historical-migration-check.json) verified all
**26 frozen accepted migration hashes** and
byte-compared all **66 pre-existing HEAD migration files**: none changed. Only
`0065_b17_prepared_package_freeze.py` is new. The historical-bytes test's failure
was its final stale head assertion, after its hash checks; its historical prefix
verifier and baseline were not modified.

## Guide-prescribed migration locks and runtime lock evidence

The approved guide §12.1, lines 440–444, says:

> Upgrade first locks affected tables, verifies existing package/receipt graphs,
> then replaces guards/constraints.

It prescribes both locking and predecessor verification. It does not explicitly
name ACCESS EXCLUSIVE. That mode acquires the locks required by the affected
constraint DDL up front, before validating and replacing the guards. The seven
locked tables are the existing package/consent/receipt/grant graph whose guards
and constraints change in this migration; unrelated lane tables are not changed.

The runtime proof is separate from migration DDL. All tests named below passed
in the clean 99-case run ([log](logs/reviewer-b17-99.txt)):


- `prepare_freeze_write` uses SERIALIZABLE. Its first four transactional SQL
  statements are the literal inventory SHARE lock, Publication SHARE ROW
  EXCLUSIVE, Package SHARE ROW EXCLUSIVE and approval inventory SHARE lock,
  followed by timeouts. The observed runtime test
  `test_literal_first_sql_and_lock_order` asserts those statements and lock order.
- Reads use REPEATABLE READ with `postgresql_readonly=True`.
  `test_replay_and_all_package_reads_have_no_transitive_locks` captures completed
  replay, package/history/preview and receipt SQL, rejects explicit table,
  advisory and row locks and writes, and asserts unchanged state.
- Ordinary package/consent writes retain READ COMMITTED. The dedicated real wait
  tests still prove fresh authorization after table/grant/deferred waits and
  expiry denial without partial scientific history. The [refreshed post-fix
  expiry witnesses](expiry-witnesses.txt) and [three-case log](logs/reviewer-expiry-witnesses.txt)
  retain the actual transaction, wait, expiry, acquisition and authorization times.

## Scope and benchmark

The slice implements atomic prepared-package freeze, exact current consent
capture, supersession, immutable hashes/events/receipt, grant consumption and
historical read/replay. No new canonical table, external send, route or CLI is
introduced. The proposal records existing-name substitutions.

Archived bounded benchmark samples are informational, not a full performance
acceptance gate. Their profile remains BLOCKED for unavailable host/owning
acceptance evidence; large-profile acceptance is NOT ESTABLISHED. Unrelated
Phase 2 and novelty blockers remain inventoried. No commit, push or branch
creation was performed.

## Reviewable source locations

- [Application freeze and history](../../../src/researchbase/application/prepared_submission.py)
- [Concrete B13 consumption and final expiry checks](../../../src/researchbase/application/approval.py)
- [Persistence isolation and lock prefix](../../../src/researchbase/persistence/prepared_submission_repository.py)
- [Pure package hash/types](../../../src/researchbase/domain/prepared_submission.py)
- [Single new migration](../../../migrations/versions/0065_b17_prepared_package_freeze.py)

Obsolete development logs were removed from the diff to keep these changes
reviewable. The original failure excerpt and post-review results remain.
