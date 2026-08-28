# Concurrent-finish winner report

The test uses two independent UoWs/connections and the established
DB-relevant `synchronize_run_lock` barrier before the real Run lock. Both
transactions are active at the competing lock boundary, and release is
controlled by the database lock ordering.

Writer A:

- status: `SUCCEEDED`
- exit_code: `0`
- failure_reason: `writer-a-success`

Writer B:

- status: `FAILED`
- exit_code: `73`
- failure_reason: `writer-b-failure`

Exactly one writer succeeds. The loser receives stable application error
`CONCURRENT_MODIFICATION`; no raw database/SQLAlchemy exception is exposed.

Using a NEW UoW/session after both futures complete, the persisted row is
compared against the command tuple belonging to the successful future:

- status: matches winner
- finished_at: populated coherently
- exit_code: matches winner
- failure_reason: matches winner
- row_version: `started.row_version + 1`

All final fields match winner: YES.

Loser partial overwrite: NO. The loser is rejected by stale row-version
ordering before it can commit any terminal-field mutation.
