# Historical supersession full-row report

The regression creates frozen MetricDefinitionVersion V1, a SUCCEEDED Run, and a
Measurement bound to V1. Before revision it captures the complete persisted row:
`id`, `run_id`, `metric_definition_version_id`, `numeric_value`, `structured_value`,
`unit`, `evaluation_scope`, `content_hash`, `created_by`, and `created_at`.

The identity is revised to V2, which makes V1 SUPERSEDED. A new UoW then verifies V1
is SUPERSEDED and compares every captured Measurement field with its post-supersession
value. The exact V1 binding, value representation, unit, scope, creator, timestamp,
and content hash remain unchanged. A new record against SUPERSEDED V1 is rejected.

Result: PASS. `PR10-REV-003` is closed.
