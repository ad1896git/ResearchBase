# Idempotency report

The idempotency key is `(artifact_id, content_hash)`. A retry returns the existing
ArtifactVersion ID and does not overwrite its locator, media type, size, or metadata. The
database unique constraint is parent-local, so the same bytes under different Artifacts
produce distinct version rows with the same bare digest.

Concurrent duplicate registrations are serialized by the parent row lock and protected by
the unique constraint; both callers resolve to one physical row.
