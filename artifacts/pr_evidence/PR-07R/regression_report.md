# Regression report

The original PR-07 contracts remain covered and passing: exact-byte SHA-256, ArtifactStore
verification, storage-before-DB, DB rollback, missing/tampered object rejection,
same-parent idempotency, duplicate and distinct-content concurrency, same-parent current
pointer enforcement, frozen-field database immutability, and FROZEN→SUPERSEDED.

No migration was added by PR-07R. No PR-08, Run, role, Measurement, Claim, Phase 2+, generic
Version ORM, S3/MinIO, or GC subsystem was introduced.
