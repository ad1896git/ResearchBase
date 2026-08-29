# Legacy zero-input migration report

## Migration shape

`0013_statistical_result_legacy_input_precheck` is a child of
`0012_statistical_result_input_guard`. It contains only a PostgreSQL `DO`
precheck and a no-op downgrade. `0012` and `0011` were not rewritten.

The query is equivalent to:

```sql
SELECT sr.id
FROM statistical_results AS sr
WHERE NOT EXISTS (
  SELECT 1
  FROM statistical_result_inputs AS sri
  WHERE sri.statistical_result_id = sr.id
)
LIMIT 1;
```

## Fresh real-PostgreSQL matrix

The disposable database was `researchbase_pr11r2`, PostgreSQL `18.6`.

| Case | Observation |
| --- | --- |
| clean previous head `0012` → head | PASS; reaches `0013_statistical_result_legacy_input_precheck` |
| invalid legacy parent-only row → head | PASS; Alembic exits non-zero with `zero-input StatisticalResult invariant violation` and `manual remediation required` |
| revision after failed upgrade | PASS; `alembic current` remains `0012_statistical_result_input_guard`, not `0013` |
| invalid row after failure | PASS; parent count `1`, input count `0` |
| synthetic repair | PASS; none created by migration |
| controlled manual remediation | PASS; one legitimate Application-created Measurement is attached to the legacy row with the fixture-only immutability trigger bypass, then the trigger is re-enabled |
| retry after remediation | PASS; reaches `0013` |
| final future parent-only raw SQL | PASS; commit rejected and fresh counts are parent `0`, input `0` |
| final normal Application one-input | PASS |
| final normal Application multi-input | PASS |

The development database initially contained two prior test-fixture parent-only
rows. The precheck reported them one at a time. Each was inspected, not
deleted, and manually remediated with a real Measurement before the development
database retry reached `0013`. This was explicit fixture remediation, not
automatic migration behavior.
