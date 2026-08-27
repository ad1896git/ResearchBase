# Idempotency report

The application computes the content hash before lookup and queries `(dataset_id, content_hash)`.

- First create inserts one snapshot.
- Same dataset and equivalent material returns the existing snapshot ID.
- A different `manifest_locator` does not change the hash and does not rewrite the stored locator.
- The same material on a different Dataset has the same bare content hash but creates a distinct row.
- The database uniqueness constraint is the final duplicate guard.

Covered by `tests/integration/test_pr06_application.py` create/get, locator-independent retry, cross-dataset, and concurrency tests. Expected duplicate races are translated and resolved through a fresh UnitOfWork; raw `IntegrityError` is not exposed to the caller.
