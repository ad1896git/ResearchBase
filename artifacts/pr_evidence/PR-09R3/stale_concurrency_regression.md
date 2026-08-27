# Stale concurrency regression

Four independent-UoW PostgreSQL tests use a stale row version and verify the
stable application error plus a fresh final state with no stale side effects:

- dataset attach → `CONCURRENT_MODIFICATION`, no dataset edge from the stale writer;
- artifact attach → `CONCURRENT_MODIFICATION`, no artifact edge from the stale writer;
- start → `CONCURRENT_MODIFICATION`, no stale seal/status/timestamp mutation;
- finish → `CONCURRENT_MODIFICATION`, no stale terminal/outcome mutation.

The post-state checks include status, `inputs_sealed_at`, `started_at`,
`finished_at`, `exit_code`, `failure_reason`, `row_version`, and both input
sets. Each final read is performed through a new UoW/session. The full suite
and targeted proof suite passed.
