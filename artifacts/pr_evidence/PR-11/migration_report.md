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
