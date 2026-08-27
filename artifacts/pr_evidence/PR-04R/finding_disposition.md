# Finding Disposition

```text
PR04-REV-001 ACCEPTED -> FIXED BY PR-04R2
PR04-REV-002 ACCEPTED -> FIXED
PR04-REV-003 ACCEPTED -> FIXED BY PR-04R2
Hypothesis stale DRAFT verification -> VERIFIED
```

PR-04R2 closes the remaining PR-04R verification gaps: create rollback now directly checks both identity and version rows, freeze rollback compares every required persisted field, and both concurrent revision tests prove overlap with a barrier before the parent lock. All required cases use real PostgreSQL.
