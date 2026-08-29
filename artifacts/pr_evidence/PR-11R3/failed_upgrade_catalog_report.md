# Failed-upgrade catalog report

The invalid-upgrade test creates one zero-input StatisticalResult at revision
`0012_statistical_result_input_guard`, records its complete row snapshot, and
records real PostgreSQL catalog snapshots immediately before attempting
`0012 -> 0013`.

The automated snapshots cover:

- `alembic_version` through `alembic current`;
- all public PostgreSQL functions and definitions;
- all non-internal public triggers and definitions;
- all public constraints and definitions;
- all public relations, including tables, indexes, sequences, and views.

After the expected migration failure, the test asserts:

```text
revision = 0012_statistical_result_input_guard
functions delta = none
triggers delta = none
constraints delta = none
public relations delta = none
invalid StatisticalResult row = unchanged
input count for invalid row = 0
synthetic input = none
```

This is automated in the test itself; no manual catalog SQL is required from a
reviewer. The same test then adds one legitimate Measurement edge in a
controlled fixture-only setup, retries the migration, and verifies the future
zero-input guard and normal one-/multi-input application paths.

Observed result: PASS, 2 migration-matrix tests passed.

