# AD-PR10-001 — Measurement material hash

The exact material payload has these six keys:

    run_id: UUID string
    metric_definition_version_id: UUID string
    numeric_value: finite number or null
    structured_value: JSON object/list or null
    unit: string or null
    evaluation_scope: JSON object or null

The payload is serialized with the existing canonical-json-v1 behavior and hashed
with sha256-cjson-v1. Measurement identity, creator, and creation time are excluded.
The Application boundary computes the hash; the domain independently validates the
same material before persistence.
