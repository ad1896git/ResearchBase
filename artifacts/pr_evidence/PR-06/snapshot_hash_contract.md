# Snapshot hash contract

The implementation computes:

```text
sha256_canonical_json({
    "manifest_hash": str(normalized_manifest_hash),
    "selection_definition": selection_definition,
})
```

The domain exposes the same two-field `material_payload()` and has no status, freeze, revise, or material mutation method. Unit tests prove the exact oracle, canonical key-order stability, material-field sensitivity, and single-variable stability for `id`, `dataset_id`, `manifest_locator`, `created_by`, and `created_at`.

The original package did not independently black-box the Application result or persisted row. PR-06R adds that proof in `black_box_hash_report.md` and records the correction here.
