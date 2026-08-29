# Migration report

Migration `0011_statistical_result` is immediately after
`0010_measurement`; `alembic current` on the integration database reported:

```text
0011_statistical_result (head)
```

On the named disposable PostgreSQL 18.6 database:

1. clean base → head succeeded through all migrations;
2. current reported `0011_statistical_result (head)`;
3. `0011 → 0010` succeeded;
4. `0010 → 0011` succeeded;
5. current again reported `0011_statistical_result (head)`.

The disposable database was removed after verification. No SQLite migration
or test was used.

This report is historical evidence for the reviewed PR-11 HEAD
`9592b66dc3372fae18fdd66555203f0788e407e2` and intentionally records the then
current `0011` head. PR-11R adds the separate narrow
`0012_statistical_result_input_guard` migration; its current and roundtrip
observations are recorded in `artifacts/pr_evidence/PR-11R/migration_report.md`.
