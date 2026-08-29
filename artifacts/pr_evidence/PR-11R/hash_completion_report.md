# Hash completion report

AD-PR11-001 remains unchanged. StatisticalResult material is exactly
`analysis_type`, `result_payload`, and `analysis_definition`, using the
existing `canonical-json-v1` / `sha256-cjson-v1` semantics.

The independent standard-library JSON/SHA-256 oracle does not import the
production hash helper. Fresh differential tests changed exactly one input
metadata field at a time and observed unchanged content hashes for
`measurement_id`, `input_role`, and `ordinal`. A separate result-payload
key-order test observed equivalent hashes. An unserializable
`analysis_definition` produced `ResearchBaseError(VALIDATION_ERROR)` rather
than a raw serializer exception.

No production hash semantics changed.
