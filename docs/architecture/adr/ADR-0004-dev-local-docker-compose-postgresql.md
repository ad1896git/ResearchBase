# ADR-0004: DEV_LOCAL / Docker Compose PostgreSQL

- Status: Accepted
- Context: Developers need a repeatable local PostgreSQL service and CI must exercise a real database.
- Decision: Use Docker Compose with a PostgreSQL 18 service for the local development profile.
- Consequences: Docker availability is an explicit PR-00 acceptance prerequisite.
- Rejected alternatives: SQLite fallback and an unpinned local database substitute.
- Upstream authority: TDG-1
- Scope: Phase 1

