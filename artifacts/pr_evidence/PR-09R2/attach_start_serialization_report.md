# Attach/start serialization report (historical PR-09R2 record)

The PR-09R2 test used independent PostgreSQL sessions and transaction IDs, but
its synchronization claim was not tied strongly enough to the exact database
lock acquisition boundary. The PR-09R2 conclusion is withdrawn for that
reason; a barrier or pre-lock observation is not sufficient proof.

PR-09R3 adds SQLAlchemy execution-event evidence keyed to the actual Run
`SELECT ... FOR UPDATE`: each worker records lock-attempted and lock-acquired,
and the competing worker is asserted to have attempted but not acquired the
same boundary before the first worker is released. See
`artifacts/pr_evidence/PR-09R3/lock_boundary_race_report.md` for the
replacement evidence.
