# PR-04R Remediation Summary (superseded by PR-04R2)

PR-04R added the initial verification cases without changing production domain semantics, schema, or transaction ownership. Its remaining proof gaps were closed by PR-04R2.

- PR04-REV-001: initial post-flush rollback cases were strengthened in PR-04R2 with direct identity/version absence and exact freeze pre-state comparisons.
- PR04-REV-002: added Application-level cross-parent current-pointer attacks for both domains and verified unchanged persisted pointers.
- PR04-REV-003: initial independent-connection cases were strengthened in PR-04R2 with deterministic barriers proving both workers entered before the parent-lock critical section.
- Hypothesis stale DRAFT mutation: verified through two independent UoWs and conditional row-version updates.

No production code, migration, or schema change was required. PR-04R remains the historical baseline; PR-04R2 is the closure remediation on top of `0573fa5`.
