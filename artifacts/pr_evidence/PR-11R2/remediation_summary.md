# PR-11R2 remediation summary

PR-11R2 closes exactly `PR11R-MIG-001` and `PR11R-EVID-001` on top of reviewed
PR-11R HEAD `6675a7444cdb897d1bf810a55b32b6d88015ea15`.

The implementation is one narrow Alembic revision:
`0013_statistical_result_legacy_input_precheck`. It performs a transactional
PostgreSQL precheck for existing StatisticalResults without inputs. An
offending row aborts the migration with a deterministic manual-remediation
error; no row, Measurement, or input edge is created or changed by the
migration. Existing `0011` and `0012` history is unchanged.

The regression test drives clean upgrade, invalid legacy failure, failed-state
inspection, controlled manual remediation with a legitimate Measurement,
retry, future parent-only rejection, and normal one-/multi-input creation.

Evidence metadata was reconciled from Git-resolved SHAs and historical PR-11R
findings were preserved rather than overwritten.
