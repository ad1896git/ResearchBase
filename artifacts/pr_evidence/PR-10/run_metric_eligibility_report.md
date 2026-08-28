# Run and metric eligibility report

record_measurement requires an existing Run with status SUCCEEDED, sealed inputs,
and a complete ProvenanceClosureValidator report. PLANNED, RUNNING, FAILED, and
CANCELLED runs are rejected. The referenced MetricDefinitionVersion must exist and be
FROZEN; DRAFT and later non-frozen states are rejected for new records. A global
metric is allowed, while a project-scoped metric must match the Run project.

The application integration matrix passed for the Run states, draft metric, frozen
metric, project mismatch, and historical supersession cases. The original closure
case used a monkeypatched validator and therefore was only a harness check, not a
proof against a persisted invalid state. PR-10R persists a SUCCEEDED Run whose
experiment_spec_version_id points to a real DRAFT ExperimentSpecVersion in
PostgreSQL; the real validator reports incomplete closure and record_measurement
rejects it without inserting a Measurement.

Result after PR-10R: PASS.
