# Test report

Final full regression: `481 passed in 19.18s`, including the two disposable PostgreSQL PR-11 migration regressions. The PR-12-owned PostgreSQL schema/application/closure/atomicity/concurrency/FK suite passed 35 tests. The PR-12 concurrency suite passed 7 tests; the architecture suite passed 39 tests.

The unit suite passed the direct PR-03 harness, independent support-set and Claim hash oracles, canonical key-order tests, semantic/excluded metadata differentials, lifecycle, empty evidence, DTO, and narrow repository contract checks. No PR-13 implementation was detected.

## PR-12R reconciliation

The independent review found that the original full-suite count was not reproducible under a shared migration-test database. After remediation, the complete PostgreSQL-backed suite passed twice: Run A `483 passed, 1 warning in 9.78s`; Run C `483 passed, 1 warning in 9.56s`. The PR-12 targeted suite passed 66 tests immediately after the migration subset. The support-set oracle now uses literal rows, closure has a three-input/two-or-more-run later-input attack, and the SQL guard matrix covers both source types plus SUPERSEDED and ABANDONED.
