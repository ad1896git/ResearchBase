# Task 12: owner-approved forward schema repair

Status: **PASS**. Owner approval: 2026-10-14.

Implemented one new Alembic revision, `0043_pr2_04_schema_contract`, directly after
`0042_pr2_15_minimal_decision`. It adds the two missing UNIQUE constraints, seven
FK indexes plus the exact execution listing index, and changes receipt
`result_dto_version` from INTEGER to SMALLINT. No existing migration was edited.

Upgrade takes transaction-held ACCESS EXCLUSIVE locks on the five affected tables
before any preflight or DDL. Duplicate non-NULL attempt query keys, duplicate
scoped query keys, or out-of-range receipt versions produce explicit diagnostics
and roll back without changing rows, schema, or revision. NULL reservations remain
valid. Downgrade widens the receipt type back to INTEGER and removes only the new
constraints/indexes. No row deletion or CASCADE is used. Unexpected FK dependents
block downgrade and roll back its earlier DDL. These locks block concurrent writes
for the duration of the migration.

Current-head expectations are updated in CI, integration/topology tests, the
static baseline, README, and the exact migration lineage allowlist. Historical
revision tests and original content seals remain intact. A new byte-preservation
check covers all 44 historical migration files; hashes were recorded before edits
in `historical-migration-sha256.json`.

The scoped-FK probe had an additional PostgreSQL incompatibility hidden behind the
missing UNIQUE: a TEMP table cannot reference a permanent table. It now creates
and explicitly drops a dependent table in its disposable database, retaining the
real valid-reference and wrong-scope SQLSTATE assertions and exact UNIQUE name.
The 0042 populated downgrade test now asserts that its installed revision is
preserved on refusal, rather than assuming 0042 is still the repository head.

Verification uses local PostgreSQL 18.6 with DATABASE_URL and RB_TEST_ADMIN_URL as
in Task 9. Exact reproducible commands are in [commands.txt](commands.txt).

| Check | Result |
|---|---|
| Migration lifecycle | 9 passed, 0 failed |
| Migration/schema regression | 16 passed, 0 failed |
| Exact nine Task 9 failure IDs | 9 passed, 0 failed |
| Initial complete serial suite | 4973 passed, 1 failed (committed Task 9 whitespace) |
| Static gate after EOF correction | 1 passed, 0 failed |
| Final full suite, exact partition across five pytest workers | **4974 passed, 0 failed, 0 errors, 0 skipped; all exits 0** |
| Ruff check | PASS, exit 0 |
| Ruff format | PASS, 460 files already formatted, exit 0 |
| Pyright | 0 errors, 0 warnings, 0 informations, exit 0 |
| Shell syntax / git diff check | PASS, exit 0 |

The lifecycle tests exercise empty upgrade; populated 0042→0043→0042→0043 for
planned, reserved, sealed and terminal executions; preservation of every public
row including hashes, provenance, receipts and events; exact logical catalog
restoration on downgrade; two simultaneous NULL query reservations; all FK index
leading columns and the exact listing index; all three preflight failures; and
rollback on an unexpected downgrade dependency. Deliberate corruption is confined
to disposable test databases to reach preflight cases normally prevented by older
PKs/FKs/guards. The migration never bypasses those guards.

Earlier failed development runs and the interrupted first full run are retained
and identified in commands.txt; they are not reported as passing evidence.

The first complete serial run took 4815.36 seconds: every schema/PostgreSQL test
passed, but the final static gate found one extra blank line at EOF in the now
committed Task 9 `pyright.txt`, relative to the unchanged pinned static baseline.
Removed only that blank line; the diagnostic content remains unchanged. The
baseline and whitespace gate remain strict. The corrected static test passes.

The final rerun collects all 4974 node IDs and partitions them exactly once.
All tests outside `tests/integration/phase2/` run in one serial worker to preserve
shared Phase 1 database discipline. Phase 2 tests use per-test disposable databases
and are balanced across four workers. `run_full_sharded.py` verifies both counts
and exact parameter-aware JUnit node identities for every partition, records each
pytest exit code, and aggregates failures/errors/skips. No nodes are omitted or
marked xfail. The explicit partition and individual commands' node lists are in
`full-sharded/partition.json`; each worker uses the recorded pytest flags and its
own log and JUnit file. An early partition run was interrupted to correct the
verification helper's handling of `::` inside parameter IDs, before starting the
final rerun; its incomplete evidence is retained separately.

Final worker results: 2779 / 549 / 548 / 549 / 549 passed, respectively, with zero
failures, errors or skips and exit code 0 in every worker. The longest worker took
1232.30 seconds (20:32). The runner itself exited 0 and verified exact node identity
coverage across all 4974 cases. Final counts are in
[final-counts.json](final-counts.json) and
[the per-worker summary](full-sharded/summary.json).

The final suite includes 3111 integration cases, of which 2195 are Phase 2, and 20 E2E cases. Every one passed. All 44 historical migration hashes were additionally checked against both worktree bytes and the committed HEAD bytes.

Ruff check, Ruff format, Pyright and the strict pinned-baseline whitespace check
all exited 0; exact codes are in [static-exit-codes.json](static-exit-codes.json).
The post-run database inventory matches the Task 9 inventory exactly, including
the preexisting disposable database; this task left no additional test databases.
No commits, pushes or branches were created.
