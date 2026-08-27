# Finding Disposition

```text
PR04-REV-001 ACCEPTED -> FIXED
PR04-REV-002 ACCEPTED -> FIXED
PR04-REV-003 ACCEPTED -> FIXED
Hypothesis stale DRAFT verification -> VERIFIED
```

All required cases use real PostgreSQL. Rollback postconditions use a new connection/UoW; concurrent revision cases use independent transactions/connections.
