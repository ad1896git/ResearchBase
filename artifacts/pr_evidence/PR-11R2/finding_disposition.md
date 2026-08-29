# PR-11R2 finding disposition

| Finding | Severity | Disposition | Independent proof |
| --- | --- | --- | --- |
| PR11R-MIG-001 | P1 | CLOSED | Real PostgreSQL legacy zero-input upgrade fails before `0013` is recorded; row and zero-input state remain unchanged; controlled legitimate input remediation allows retry; new parent-only commits remain rejected. |
| PR11R-EVID-001 | P1 | CLOSED | PR-11R and PR-11R2 implementation/test/evidence SHAs resolve from Git; reviewed PR-11R HEAD and current-head semantics are explicitly separated; inventories are set-equal to Git. |

Previously closed PR-11R findings F-002 through F-007 remain closed and were
regressed by the fresh test suite. F-001 remains closed by the existing
`0012` deferred guard plus the PR-11R tests.

Open P0: none.

Open P1: none.
