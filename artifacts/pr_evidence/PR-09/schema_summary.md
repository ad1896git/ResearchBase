# PR-09 schema summary

Migration `0008_run_core` adds exactly these tables:

- `runs`: exact Run identity, exact frozen ExperimentSpecVersion FK, lifecycle timestamps/outcome, `row_version`, status/seal checks.
- `run_dataset_inputs`: composite PK `(run_id, dataset_snapshot_id, role)`, exact DatasetSnapshot FK, closed role check, non-negative application ordinal.
- `run_artifact_inputs`: composite PK `(run_id, artifact_version_id, role)`, exact ArtifactVersion FK, closed role check, non-negative application ordinal.

All seven new foreign keys use `ON DELETE RESTRICT`. No polymorphic main-chain reference or generic Version table was added. PostgreSQL inspection confirmed the exact columns and constraints.
