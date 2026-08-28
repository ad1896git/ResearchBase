# Test report

Full PostgreSQL-backed regression: `315 passed in 3.38s`.

The PR-09R3 proof module has 11 tests covering real-SQL atomicity, attach-first
and start-first lock-boundary serialization, prior exact-provenance retention,
four stale row-version cases, finalized superseded closure/start behavior,
FROZEN-only authoring, and ABANDONED closure invalidity.

The targeted PR-09 application, schema, proof, and architecture import-boundary
set passed. Existing coverage for concurrent start/finish, sealed-input
trigger attacks, closure DTO ordering/determinism, and FK/RESTRICT also passed
in the targeted and full suites.

Ruff check and Pyright passed. Owned-file formatting passed. Repository-wide
format has the eight inherited failures documented separately.

The final review found a remaining concurrent-finish proof gap: the historical
test used identical terminal metadata. PR-09R4 reran the full suite at
`315 passed` after adding distinguishable writer metadata and winner-field
assertions for status, finished_at, exit_code, failure_reason, and
row_version.
