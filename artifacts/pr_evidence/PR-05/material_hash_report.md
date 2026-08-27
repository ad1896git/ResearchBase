# Material hash report

The explicit material payload is exactly:

`title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, `analysis_plan`.

Identity, relationship, lifecycle, timestamps, row versions, pointers, and content hash are excluded. Frozen material uses `canonical-json-v1` serialization and `sha256-cjson-v1`; no second serializer or normalization policy was introduced.
