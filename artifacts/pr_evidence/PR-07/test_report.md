# Test report

The PR-07 unit, architecture, and integration tests cover nullable project identity,
validation, exact raw-byte SHA-256, store verification and ordering, missing/tampered
objects, size/hash mismatches, idempotent retries, same-parent/different-parent behavior,
concurrent duplicate and distinct content, row-version conflicts, freeze, history, current
pointer ownership, rollback, PostgreSQL checks/FKs/uniques, and frozen-field trigger
immutability.

Result: full suite `262 passed`; PR-07 integration/schema subset `21 passed`.
