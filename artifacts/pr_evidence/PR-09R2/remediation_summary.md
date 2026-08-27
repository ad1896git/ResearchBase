# PR-09R2 remediation summary

PR-09R2 is a proof-quality remediation on top of baseline `9a35f9f`.

Scope was limited to the six requested review gaps:

- observe the exact Run SQL and same-transaction visibility before injected rollback;
- compare complete Run/input pre-state in a fresh UoW and prove retry cardinality;
- replace the pre-lock barrier race with two DB-relevant PostgreSQL serializations;
- prove exact frozen ExperimentSpecVersion, ArtifactVersion, and DatasetSnapshot provenance;
- exercise independent stale row-version writers for dataset attach, artifact attach, start, and finish;
- reconcile the earlier PR-09R evidence without redesigning Run Core or adding a migration.

The only production-facing file changed is none. The implementation remains at
the accepted PR-09R state, including migration `0009_run_input_seal_fix`.

PR-10/Measurement was not implemented.
