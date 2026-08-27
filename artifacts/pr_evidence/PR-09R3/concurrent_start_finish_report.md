# Concurrent start/finish report

Existing PR-09 concurrency regressions were rerun against PostgreSQL:

- concurrent start: one writer wins, the other fails stably, and the final Run
  is coherent `RUNNING` with one row-version increment;
- concurrent finish with conflicting `SUCCEEDED` and `FAILED` outcomes: one
  writer wins, the other fails, and the winner's status, finish timestamp,
  exit code, failure reason, and row version remain final.

The R3 full suite and targeted PR-09 application/proof suites passed. This
remediation does not redesign Run state transitions or schema.
