# Run and metric eligibility report

record_measurement requires an existing Run with status SUCCEEDED, sealed inputs,
and a complete ProvenanceClosureValidator report. PLANNED, RUNNING, FAILED, and
CANCELLED runs are rejected. The referenced MetricDefinitionVersion must exist and be
FROZEN; DRAFT and later non-frozen states are rejected for new records. A global
metric is allowed, while a project-scoped metric must match the Run project.

The application integration matrix passed for the Run states, draft metric, frozen
metric, project mismatch, and historical supersession cases.

Result: PASS.
