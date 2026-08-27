# Attach/start serialization report

The two outcomes are tested separately against real PostgreSQL and independent
SQLAlchemy sessions/UoWs. A repository wrapper runs `SELECT txid_current()` in
each worker's UoW before its real `SELECT ... FOR UPDATE`, records distinct
transaction IDs, and signals the active transaction. The first worker holds
its transaction after the real Run mutation flush; the competing worker is
then alive and attempting the same Run lock. Commit release is controlled only
after both database transactions have reached the relevant synchronization.

Attach-first:

- attach returns from the real Run lock first and holds the transaction;
- attach mutation is flushed, then start's independent transaction records a distinct active txid and attempts the Run lock;
- attach commits, the competing initial start observes the established stale row version and retries from a fresh UoW;
- final Run is `RUNNING`, `inputs_sealed_at` is non-null, and the dataset edge is present in the sealed input set.

Start-first:

- start returns from the real Run lock first and holds the transaction;
- start mutation is flushed, then attach's independent transaction records a distinct active txid and attempts the Run lock;
- start commits, attach proceeds and fails with the actual stable `CONCURRENT_MODIFICATION` ordering error;
- final Run is `RUNNING`, `inputs_sealed_at` is non-null, and the dataset edge is absent.

Fresh final reads verify row versions and input sets. No edge is committed after
the seal timestamp. The earlier PR-09R report's pre-lock barrier claim is
withdrawn; this report is the replacement proof.
