# Query contract report

- `get_run_provenance(run_id)`: exact Run identity/state/timestamps, exact ExperimentSpecVersion,
  DatasetSnapshot and ArtifactVersion inputs, Measurements, and Run closure.
- `trace_run_to_inputs(run_id)`: exact spec and input edges ordered by role, ordinal, target ID.
- `trace_claim_to_runs(claim_version_id)`: exact ClaimVersion, unique Runs, every typed evidence path,
  and accepted Claim closure. Paths retain relation type, qualification, source ID, StatisticalResult
  input role/ordinal, Measurement, MetricDefinitionVersion, and Run.
- `get_claim_closure_report`: deterministic projection of the accepted validator.
- Missing roots raise `ResearchBaseError(NOT_FOUND)`. DRAFT and empty-evidence roots return truthful
  closure reports; broken descendants remain closure violations rather than root NOT_FOUND.

