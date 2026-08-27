# Transaction and atomicity report

Snapshot creation uses one Application command and one UnitOfWork transaction. The late-failure test flushes the real INSERT and raises before commit. The UnitOfWork rolls back; a new database connection verifies zero snapshot rows. A normal retry then succeeds and creates one row.

Covered by `test_snapshot_late_failure_rolls_back_and_retry_is_single_row`.

The original test did not prove that a real INSERT occurred before the injected failure. PR-06R adds a SQLAlchemy execution-event observation and reconciles this report in `artifacts/pr_evidence/PR-06R/atomicity_proof.md`.
