# PR-04R Test Report

The final suite has 147 passing tests. The integration selection has 30 passing tests.

The seven original PR-04 application tests plus six remediation cases passed, including:

- ResearchQuestion and Hypothesis create rollback after an explicit flush and before commit;
- ResearchQuestion and Hypothesis freeze rollback after version/pointer work is flushed;
- ResearchQuestion and Hypothesis cross-parent current-pointer attacks;
- Hypothesis stale DRAFT update from independent UoWs;
- concurrent ResearchQuestion revision allocation;
- concurrent Hypothesis revision allocation.

No raw `IntegrityError` was returned by the concurrent revision application paths; the losing request returned `CONCURRENT_MODIFICATION`.
