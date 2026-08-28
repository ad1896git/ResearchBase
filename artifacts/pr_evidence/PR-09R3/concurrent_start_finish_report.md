# Concurrent start/finish report (historical PR-09R3 record)

Existing PR-09 concurrency regressions were rerun against PostgreSQL:

- concurrent start: one writer wins, the other fails stably, and the final Run
  is coherent `RUNNING` with one row-version increment;
- concurrent finish with conflicting `SUCCEEDED` and `FAILED` outcomes: one
  writer wins, the other fails, and the winner's status, finish timestamp,
  exit code, failure reason, and row version remain final.

The PR-09R3 final review identified that this test did not yet use
distinguishable writer metadata or assert the winning exit code and failure
reason. That P2 gap remained open at the R3 endpoint. PR-09R4 closes it by
passing `SUCCEEDED/0/writer-a-success` versus
`FAILED/73/writer-b-failure` and matching all persisted terminal fields to the
actual winning future. See the PR-09R4 winner report.

The R3 full suite and targeted PR-09 application/proof suites passed. This
remediation does not redesign Run state transitions or schema.
