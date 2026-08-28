# Exact provenance report

Measurements persist direct foreign-key bindings to run_id and
metric_definition_version_id; no identity-level or current-pointer resolution is
used. The original regression proved only that the V1 identifier remained visible.
PR-10R captures every persisted Measurement field before V1 is superseded, moves the
identity current pointer to V2, and verifies field-for-field equality in a new UoW,
including the exact V1 binding and content_hash. New recording against SUPERSEDED V1
remains rejected.

Result after PR-10R: PASS.
