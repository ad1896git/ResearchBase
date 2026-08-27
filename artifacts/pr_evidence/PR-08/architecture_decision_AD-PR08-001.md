# AD-PR08-001

The frozen MetricDefinitionVersion material is exactly `{"definition": ..., "unit": ..., "aggregation": ...}`. It uses the existing canonical JSON and `sha256-cjson-v1` primitives. Identity and operational fields are excluded. This is a PR-08 implementation decision and introduces no metric DSL or closed unit/aggregation vocabulary.
