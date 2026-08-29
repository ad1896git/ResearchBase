# Migration failure and recovery report

The invalid-legacy run used a disposable PostgreSQL database and first moved
from `0012` down to `0011`, inserted exactly one parent-only StatisticalResult,
and upgraded back to `0012`. The attempted `0012` → `0013` upgrade then failed
inside the migration transaction.

Observed after failure:

- Alembic revision stayed at `0012_statistical_result_input_guard`.
- The invalid parent row remained the same row with the same project, actor,
  payload, and hash.
- Its input count remained zero.
- No input edge, Measurement, schema object, or false head marker was created
  by the failed migration.
- The existing 0012 deferred trigger/function remained present and coherent.

After explicit fixture remediation by adding a legitimate Measurement input,
the same `alembic upgrade head` command succeeded and recorded `0013`. The
clean and final-head roundtrips also succeeded. PostgreSQL transactional DDL
therefore prevented a half-migrated accepted state.
