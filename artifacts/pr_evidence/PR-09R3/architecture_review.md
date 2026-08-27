# Architecture review

Architecture conformance: PASS.

The production change is limited to the closure validator's finalized-state
policy. The tests use application commands, repository/UoW boundaries, and
real PostgreSQL; SQLAlchemy event listeners are test-only proof instrumentation.
The domain does not depend on SQLAlchemy, FastAPI, Typer, or a session.

Scope audit confirms no new business table, migration, RunVersion, generic
Version ORM/table, Measurement, PR-10, Phase 2+ implementation, generic
polymorphic provenance, or direct persistence bypass. The architecture import
boundary tests and migration allowlist pass. Existing Run Core schema and
`0009_run_input_seal_fix` are unchanged.
