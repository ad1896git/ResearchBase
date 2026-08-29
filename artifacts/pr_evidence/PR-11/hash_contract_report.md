# Hash contract report

AD-PR11-001 material is exactly the following three-key object:

```json
{"analysis_type": ..., "result_payload": ..., "analysis_definition": ...}
```

It is serialized with the existing `canonical-json-v1` implementation and
hashed with `sha256-cjson-v1`. Identity, project, creator, creation time, input
IDs, input roles, and ordinals are excluded.

The independent unit and integration oracles use standard-library
`json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(',', ':'),
allow_nan=False)` followed by SHA-256; they do not call the production builder.
Tests proved each material field changes the digest independently, object key
order does not, and excluded metadata does not. Unserializable material is
translated to `ResearchBaseError` with `VALIDATION_ERROR`.

Two distinct results with the same intrinsic material were stored with the
same hash and different IDs; no unauthorized `UNIQUE(content_hash)` exists.
