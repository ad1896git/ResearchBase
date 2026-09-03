# Architecture Decisions

- The acceptance workflow is test-only and uses the public Application command/query interfaces.
- FastAPI and Typer are exercised as independent peer adapters; neither adapter calls the other.
- Each acceptance fixture creates a unique PostgreSQL schema and runs `alembic upgrade head` before composing
  fresh Application/UoW services.
- Deterministic test IDs and a fixed UTC clock make material hashes and normalized projections comparable across
  independent adapter executions without changing production ID or clock behavior.
- Historical advancement creates later legal versions/snapshots and a separate later run; original frozen
  scientific records are queried again from fresh UoWs.
- SQL instrumentation is attached only by tests and is removed in `finally` blocks. It observes statement class
  and count; it does not provide a production fault hook.
- Atomicity uses the same failing-UoW test seam already accepted by PR-12. The seam flushes to observe the
  transaction boundary and then raises, allowing PostgreSQL rollback to be verified from fresh reads.
