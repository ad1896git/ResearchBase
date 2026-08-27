# Concurrency report

The application locks the owning Artifact before checking content idempotency and allocating
the next version number. PostgreSQL integration tests deterministically overlap two
duplicate-content writers and two distinct-content writers. Results are respectively one
physical row with one shared ID, and parent-local version numbers `[2, 3]` without pointer
corruption.

Artifact and ArtifactVersion row updates use optimistic `row_version` predicates. A stale
DRAFT metadata writer returns the stable concurrent-modification error.
