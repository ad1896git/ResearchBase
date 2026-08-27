# Black-box hash report

`test_application_snapshot_hash_matches_independent_material_oracle` calls the real `ApplicationService.create_dataset_snapshot`.

Input vector:

```text
manifest_hash = "Ab" * 32
selection_definition = {"split": "train", "where": {"status": "ready"}}
```

The test independently constructs `{"manifest_hash": manifest_hash.lower(), "selection_definition": selection_definition}` and computes the expected value with public `sha256_canonical_json` (canonical-json-v1). The returned Application hash and fresh-connection persisted `content_hash` both equal that independent expected hash, and `content_hash != manifest_hash`.

The same test module proves through Application calls that changing only selection changes `content_hash`, and changing only manifest hash changes `content_hash`.
