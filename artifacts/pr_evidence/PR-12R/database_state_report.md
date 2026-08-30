# Database-state report

PostgreSQL version observed after restarting the repository's local service: 18.6 on aarch64-unknown-linux-musl.

The shared development/integration database is `researchbase` and reported `0014_claim_evidence (head)` before the required migration-subset sequence, after the immediate PR-12 targeted suite, after full Run A, and after full Run C.

The migration-test database is the separate disposable database `researchbase_pr12r_migration_20260830`. The migration module's finalizer restored it to the dynamically discovered repository head; a direct `alembic current` immediately afterward reported `0014_claim_evidence (head)`.

The shared database was initialized at 0014 before the proof sequence. No manual `alembic upgrade head` was run between migration tests, the immediate PR-12 targeted suite, Run A, or Run C.
