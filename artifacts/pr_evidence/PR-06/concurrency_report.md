# Concurrency report

`test_concurrent_same_content_creation_is_idempotent` uses two independent SQLAlchemy sessions and a deterministic `Barrier` immediately before commit. Both transactions attempt the same `(dataset_id, content_hash)`.

Observed result: exactly one physical `dataset_snapshots` row, both callers return the same snapshot ID, and neither caller receives a raw expected `IntegrityError`. The composite unique constraint remains the database final guard.
