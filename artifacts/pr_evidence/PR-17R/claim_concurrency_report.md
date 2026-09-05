# Claim Concurrency Report

The Claim evidence-link versus freeze test uses independent PostgreSQL UoWs and connections. It records distinct
backend PIDs, initial ClaimVersion status and row version, lock-boundary events, worker outcomes, and final fresh
state. The required interleaving is:

```text
freeze_lock_acquired
link_lock_requested
release_requested
freeze_released
link_lock_acquired
```

The accepted winner is freeze. The link worker loses with the stable `CONCURRENT_MODIFICATION` error. The final
ClaimVersion is `FROZEN`, its row version advances exactly once, its evidence set remains empty, and closure is
complete. The test requires explicit worker counts and outcomes, distinct backend identities, and no partial
overwrite; it contains no vacuous `all([])` assertion.

The representative version-revise, Claim freeze, Run transition, and AuditFinding row-version regressions also
pass using independent PostgreSQL transactions.
