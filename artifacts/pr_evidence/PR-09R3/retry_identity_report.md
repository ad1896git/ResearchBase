# Retry identity report

Rollback/retry assertions use fresh PostgreSQL reads and exact read models.

| Operation | Exact retry edge | Exact count |
|---|---|---:|
| dataset attach | `(run_id, dataset_snapshot_id, TEST, 0)` | `1` |
| artifact attach | `(run_id, artifact_version_id, MODEL, 0)` | `1` |

Create retry also counts the exact Run identifier as `1`. After each injected
failure, a new UoW compares the complete Run pre-state and both input sets;
the failed writer leaves no extra edge or state mutation. Proof uses SQL
execution observation and fresh-state reads, never a boolean set after
`flush()`.
