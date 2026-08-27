# Optimistic concurrency report

Every mutating Run path checks the caller's expected `row_version`. Attach, start, and finish increment it through compare-and-update persistence. Stale attach/start/finish attempts produce `CONCURRENT_MODIFICATION`; no raw expected-row database error leaks through the application boundary.

