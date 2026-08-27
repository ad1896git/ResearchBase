# Material hash report (reconciled by PR-05R)

The explicit material payload is exactly `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, and `analysis_plan`. PR-05R independently freezes a baseline and one variant for each field and asserts a different hash. It also varies version identity/metadata and asserts hash stability. AD-PR05-001 confirms identity-level `hypothesis_id` is excluded from version material/hash and is immutable after create. Frozen material uses `canonical-json-v1` and `sha256-cjson-v1`; no second serializer or normalization policy was introduced.
