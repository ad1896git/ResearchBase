# Lock-boundary race report

The two serialization tests use two independent SQLAlchemy sessions/UoWs and
two worker roles (`attach`, `start`). Each role captures `SELECT txid_current()`
inside its own active transaction before invoking the real repository
`get_for_update`; the test asserts both transaction IDs are present and
distinct.

The test installs SQLAlchemy `before_cursor_execute` and `after_cursor_execute`
listeners, keyed only to the Run lock statement (`FROM runs ... FOR UPDATE`).
Thus `lock_attempted` is emitted immediately before the database call and
`lock_acquired` only after that exact call returns. The test would fail if the
workers merely ran sequentially: while the first transaction is held, the
competitor must have attempted the same boundary and must not yet have
acquired it.

## Attach-first

1. Attach transaction begins, records its transaction ID, emits
   `ATTACH_LOCK_ATTEMPTED`, then `ATTACH_LOCK_ACQUIRED`.
2. Attach performs the real mutation and holds its commit after flush.
3. Start transaction begins with a distinct transaction ID, emits
   `START_LOCK_ATTEMPTED`, and is observed with `START_LOCK_ACQUIRED` unset
   while attach is held.
4. Attach is released and commits; start then acquires the lock, observes the
   stale row version, refreshes in a new UoW, and succeeds.
5. Fresh final read: Run `RUNNING`, `inputs_sealed_at` non-null, dataset edge
   present, row version advanced by attach and start. No edge is committed
   after sealing.

## Start-first

1. Start transaction begins, records its transaction ID, emits
   `START_LOCK_ATTEMPTED`, then `START_LOCK_ACQUIRED`.
2. Start performs the real seal/state mutation and holds its commit after
   flush.
3. Attach transaction begins with a distinct transaction ID, emits
   `ATTACH_LOCK_ATTEMPTED`, and is observed with `ATTACH_LOCK_ACQUIRED` unset
   while start is held.
4. Start is released and commits; attach proceeds and fails with the stable
   application error `CONCURRENT_MODIFICATION` from stale row-version
   ordering.
5. Fresh final read: Run `RUNNING`, `inputs_sealed_at` non-null, dataset edge
   absent. No post-seal edge is committed.

Both tests pass. The earlier PR-09R2 pre-lock/barrier claim is withdrawn; this
report is the replacement proof at the actual PostgreSQL lock boundary.
