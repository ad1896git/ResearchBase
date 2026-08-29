# Finding disposition

| Finding | Severity | Disposition | Proof |
| --- | --- | --- | --- |
| F-001 | P1 | CLOSED | Deferred PostgreSQL constraint trigger rejects repository/UoW and raw-SQL parent-only commits; normal one/multiple-input commands pass. |
| F-002 | P1 | CLOSED | Repository translates only the named input-PK conflict to `ResearchBaseError(VALIDATION_ERROR)` and preserves `IntegrityError` as cause. |
| F-003 | P1 | CLOSED | Git-resolved baseline, implementation, payload, and review metadata are recorded; inventory set equality is verified. |
| F-004 | P2 | CLOSED | Reverse-insertion tie ordering and role lengths 32/33/empty are covered. |
| F-005 | P2 | CLOSED | Independent hash oracle, isolated input-metadata exclusions, key-order equivalence, and malformed analysis definition are covered. |
| F-006 | P2 | CLOSED | V1/M1/S remains exact after V2 supersedes V1. |
| F-007 | P2 | CLOSED | Missing query paths and fresh FK/RESTRICT survival assertions are covered. |

No P0 or P1 findings remain open.

## Subsequent independent review

The final independent review performed after PR-11R found two later findings
at reviewed HEAD `6675a7444cdb897d1bf810a55b32b6d88015ea15`:

| Finding | Severity | Historical disposition at PR-11R HEAD | PR-11R2 disposition |
| --- | --- | --- | --- |
| PR11R-MIG-001 | P1 | OPEN — `0012` did not precheck legacy zero-input rows. | CLOSED by migration `0013` plus real PostgreSQL failure/recovery matrix. |
| PR11R-EVID-001 | P1 | OPEN — fingerprint omitted later evidence commits and reviewed HEAD. | CLOSED by Git-resolved fingerprint reconciliation and set-equal inventories. |

These findings are recorded rather than erased from the PR-11R history.
