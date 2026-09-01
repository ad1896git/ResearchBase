# AuditFinding concurrency report

Real PostgreSQL concurrency evidence:

- independent PostgreSQL UoWs: YES;
- real lock-boundary overlap: PASS;
- same initial `row_version`: 1;
- exactly one winner: YES;
- loser error: `CONCURRENT_MODIFICATION`;
- final status: `dismissed`;
- final `row_version`: 2;
- partial loser overwrite: NONE.

Both transactions were established before winner release and synchronized at the row-lock/update boundary. No raw database exception escaped the Application boundary.
