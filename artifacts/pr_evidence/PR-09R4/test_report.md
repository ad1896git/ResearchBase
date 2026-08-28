# Test report

Fresh full regression against PostgreSQL 18.6: `315 passed in 3.32s`.

The strengthened concurrent-finish test now uses:

- Writer A: `SUCCEEDED`, `0`, `writer-a-success`;
- Writer B: `FAILED`, `73`, `writer-b-failure`.

Exactly one future succeeds. The loser receives `CONCURRENT_MODIFICATION`.
Fresh final state asserts status, finished_at, exit_code, failure_reason, and
row_version against the successful writer's complete command tuple.

All PR-09R3 proof categories were rerun: concurrent start, actual lock-boundary
attach-vs-start, exact provenance/closure, SQL atomicity, stale concurrency,
sealed-input trigger, architecture, schema, and FK/RESTRICT. All passed.
