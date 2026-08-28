# Independent hash oracle report

The PR-10R tests do not import `researchbase.foundation.hashing` and do not call
`sha256_canonical_json`, `canonical_json_bytes`, or a production material builder.
They independently construct `run_id`, `metric_definition_version_id`,
`numeric_value`, `structured_value`, `unit`, and `evaluation_scope`; serialize the
supported canonical-json-v1 subset with test-owned `json.dumps` settings
(`ensure_ascii=False`, sorted keys, compact separators, `allow_nan=False`); encode
UTF-8; and call stdlib `hashlib.sha256` directly.

The real PostgreSQL application regression verifies returned and persisted hashes for
both a numeric Measurement and a structured Measurement. The numeric case includes a
structured evaluation scope; the structured case includes canonical key-order and
duplicate-content behavior. The unit regression uses one deterministic shared
baseline and changes exactly one material field at a time. Separate `dataclasses`
replacement checks vary `id`, `created_by`, and `created_at` independently and prove
the hash is unchanged.

Result: PASS. `PR10-REV-001` is closed.
