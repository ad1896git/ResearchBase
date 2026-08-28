# Atomicity report

The real record_measurement path was run with a failing UoW. An SQLAlchemy
after_cursor_execute listener observed exactly one INSERT INTO measurements before
the injected failure. The same transaction queried the inserted row and observed one
row before the fault. A fresh UoW then observed no row after rollback. Retrying the
same command produced exactly one persisted Measurement.

Result: PASS.
