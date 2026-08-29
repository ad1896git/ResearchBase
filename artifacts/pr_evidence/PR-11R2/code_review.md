# Code review

The production change is limited to `0013_statistical_result_legacy_input_precheck.py`.
It selects one existing StatisticalResult lacking an input and raises a
PostgreSQL `check_violation` with the row id and explicit manual-remediation
instruction. The exception occurs before Alembic records the new revision and
transactional DDL leaves the previous revision and data intact.

The migration has no data-repair branch: it cannot delete rows, create
Measurements, insert edges, retarget provenance, or mark invalid data valid.
The test proves those negative properties and proves retry only after explicit
fixture remediation.

No P0/P1 code finding remains open.
