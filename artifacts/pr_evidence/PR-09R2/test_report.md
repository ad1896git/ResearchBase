# Test report

The fresh full suite passed with `312 passed` against PostgreSQL 18.6.

The PR-09/PR-09R2 targeted set passed 23 tests. The new proof module contains
8 tests: one exact-SQL atomicity test covering create/dataset attach/artifact
attach/start/finish, two independent attach/start serialization tests, one
exact-provenance test, and four stale row-version tests.

Existing PR-09 regression coverage also passed for sealed-input trigger
attacks, closure DTO/order and start failure, FK/RESTRICT behavior, terminal
state handling, concurrent start/finish, architecture boundaries, and Run
domain contracts.

The repository-wide format check remains an inherited baseline failure only;
the two PR-09R2-owned Python files pass scoped formatting.
