# Transaction and atomicity report

Snapshot creation uses one Application command and one UnitOfWork transaction. The late-failure test flushes the real INSERT and raises before commit. The UnitOfWork rolls back; a new database connection verifies zero snapshot rows. A normal retry then succeeds and creates one row.

Covered by `test_snapshot_late_failure_rolls_back_and_retry_is_single_row`.
