# Exact provenance report

Measurements persist direct foreign-key bindings to run_id and
metric_definition_version_id; no identity-level or current-pointer resolution is
used. An integration regression recorded against MetricDefinitionVersion V1, moved
the identity current pointer to V2, and verified the Measurement still references V1.

Result: PASS.
