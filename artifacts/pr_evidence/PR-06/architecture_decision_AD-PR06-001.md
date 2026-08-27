# AD-PR06-001

DatasetSnapshot scientific material is exactly:

```json
{
  "manifest_hash": "<normalized 64-hex digest>",
  "selection_definition": "<canonical JSON-compatible structure>"
}
```

`content_hash` is `sha256-cjson-v1(canonical-json-v1(material))`. The implementation delegates to the accepted Foundation primitives and does not add a second serializer or hash stack.

Excluded fields are `id`, `dataset_id`, `manifest_locator`, `created_by`, and `created_at`. `dataset_id` remains part of the database idempotency boundary through `UNIQUE(dataset_id, content_hash)` but is not part of the bare scientific content hash.
