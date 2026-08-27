# Stale row-version matrix

Each row is a separate PostgreSQL integration test. Two independent service
instances first read the same Run row version. One writer commits; the second
writer submits the stale version from its independent read. A new UoW verifies
the final state and that the stale writer added no side effects.

| Operation | Winner | Stale writer result | Fresh-state proof |
|---|---|---|---|
| dataset attach | one TEST edge, row version +1 | `CONCURRENT_MODIFICATION` | complete Run state and both input sets unchanged after stale attempt; exactly one dataset edge |
| artifact attach | one MODEL edge, row version +1 | `CONCURRENT_MODIFICATION` | complete Run state and both input sets unchanged after stale attempt; exactly one artifact edge |
| start | Run becomes `RUNNING`, sealed, row version +1 | `CONCURRENT_MODIFICATION` | status/seal/start/finish/outcome/version and both input sets unchanged after stale attempt |
| finish | Run becomes `SUCCEEDED`, row version +1 | `CONCURRENT_MODIFICATION` | seal/start/finish/outcome/version and both input sets unchanged after stale attempt |

No stale writer persisted a partial mutation.
