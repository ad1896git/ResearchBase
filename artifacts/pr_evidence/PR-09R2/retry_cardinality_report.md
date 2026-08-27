# Retry cardinality report (reconciled)

The PR-09R2 evidence stated retry cardinality but did not preserve exact edge
identity/role/ordinal in its report. PR-09R3 closes that proof gap. The
replacement regression asserts, from fresh PostgreSQL reads:

- failed `create_run` leaves no visible Run; the retry is counted by its exact id and equals `1`;
- dataset retry equals `(run_id, dataset_snapshot_id, TEST, 0)` with exact count `1`;
- artifact retry equals `(run_id, artifact_version_id, MODEL, 0)` with exact count `1`.

The complete Run pre-state and both input sets are compared after each injected
rollback. No `flush(); observed_insert=True` flag is used as proof. The
authoritative R3 report is `artifacts/pr_evidence/PR-09R3/retry_identity_report.md`.
