# Atomicity proof

`test_snapshot_late_failure_rolls_back_and_retry_is_single_row` uses a real PostgreSQL-backed UnitOfWork. A SQLAlchemy `before_cursor_execute` listener observes the actual `INSERT INTO dataset_snapshots` statement. The test then injects failure after `flush()` and before commit.

Observed sequence:

1. real INSERT observed;
2. injected failure raised before commit;
3. UnitOfWork rollback completed;
4. fresh connection reported matching row count `0`;
5. normal retry committed;
6. retry returned a snapshot ID and the new read path confirmed one persisted row.

No production-only failure flag was added.
