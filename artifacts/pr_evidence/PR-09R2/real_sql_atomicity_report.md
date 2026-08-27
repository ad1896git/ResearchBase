# Real SQL atomicity report

The rollback harness uses a new `FailingUnitOfWork` for each application call.
Its `commit()` flushes pending work only to make the database statement execute,
then raises the injected failure. Proof does not rely on a flush flag.

An SQLAlchemy `after_cursor_execute` listener records exactly one target
statement for each operation and immediately runs a visibility query on the
same SQLAlchemy connection and transaction. The listener is guarded against
recursive observation of its visibility query. The operation then fails before
commit. Fresh application reads use new UoWs and compare the complete Run
read model plus both ordered input sets against the pre-state.

Observed target statements:

- `create_run`: one `INSERT INTO runs`; same-transaction project/spec query saw one row; fresh state saw zero rows; retry count for the retried Run was exactly one.
- dataset attach: one `INSERT INTO run_dataset_inputs`; same-transaction target-edge query saw one row; fresh complete Run/input state matched pre-state; retry left exactly one dataset edge.
- artifact attach: one `INSERT INTO run_artifact_inputs`; same-transaction target-edge query saw one row; fresh complete Run/input state matched pre-state; retry left exactly one artifact edge.
- start: one `UPDATE runs`; same-transaction query saw `RUNNING` with non-null seal/start timestamps; fresh complete state remained pre-start; the normal start then succeeded.
- finish: one `UPDATE runs`; same-transaction query saw `SUCCEEDED`, non-null finish timestamp, and exit code `0`; fresh complete state remained pre-finish; the normal finish then succeeded.

This directly satisfies the requested real-SQL-before-failure proof and does
not alter production transaction or schema behavior.
