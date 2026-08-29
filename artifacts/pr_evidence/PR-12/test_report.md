# Test report

Final full regression: `481 passed in 19.18s`, including the two disposable PostgreSQL PR-11 migration regressions. The PR-12-owned PostgreSQL schema/application/closure/atomicity/concurrency/FK suite passed 35 tests. The PR-12 concurrency suite passed 7 tests; the architecture suite passed 39 tests.

The unit suite passed the direct PR-03 harness, independent support-set and Claim hash oracles, canonical key-order tests, semantic/excluded metadata differentials, lifecycle, empty evidence, DTO, and narrow repository contract checks. No PR-13 implementation was detected.
