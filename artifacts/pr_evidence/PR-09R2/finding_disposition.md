# PR-09R2 finding disposition

- `PR09R-REV-008`: CLOSED. Exact `INSERT`/`UPDATE` SQL is observed with SQLAlchemy `after_cursor_execute`; a same-connection query proves the target mutation was visible before the injected failure, and fresh UoWs prove rollback.
- `PR09R-REV-009`: CLOSED. Create, dataset attach, and artifact attach retries are asserted at exact cardinality `== 1`; all rollback paths compare complete Run state and both input sets in new UoWs.
- `PR09R-REV-010`: CLOSED. Attach-first and start-first are separate PostgreSQL serializations with independent sessions, distinct `txid_current()` values, real Run lock-boundary observation, active competing transactions, controlled commit release, and fresh final reads.
- `PR09R-REV-011`: CLOSED. Integration coverage proves Runs retain exact ExperimentSpecVersion V1, ArtifactVersion A1, and DatasetSnapshot D1 after the owning identity/current pointer or later snapshot changes.
- `PR09R-REV-012`: CLOSED. Separate PostgreSQL stale-writer tests cover dataset attach, artifact attach, start, and finish; each verifies `CONCURRENT_MODIFICATION`, no stale side effects, and fresh final state.
- `PR09R-REV-013`: CLOSED. PR-09R's unsupported flush-flag and pre-lock-barrier claims are explicitly withdrawn; the replacement evidence is tied to actual commands, tests, migration head, PostgreSQL version, and Git state.

No P0 or P1 findings remain in the PR-09R2 scope.
