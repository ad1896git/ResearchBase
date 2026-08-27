# Test report

The PR-07 unit, architecture, and integration tests cover nullable project identity,
validation, exact raw-byte SHA-256, store verification and ordering, missing/tampered
objects, size/hash mismatches, idempotent retries, same-parent/different-parent behavior,
concurrent duplicate and distinct content, row-version conflicts, freeze, history, current
pointer ownership, rollback, PostgreSQL checks/FKs/uniques, and frozen-field trigger
immutability.

PR-07R adds an independent store-derived byte-size attack and valid-update test, plus a
direct ArtifactVersion adapter invocation of the shared PR-03 lifecycle/immutability
harness. Result: full suite `264 passed`; PR-07 integration/schema subset `22 passed`;
focused contract/architecture/store tests `78 passed`.
