# Manifest hash contract

`create_dataset_snapshot` accepts a supplied `manifest_hash` and validates it through the accepted `ContentHash` contract. Values are normalized to lower-case 64-character SHA-256 hexadecimal text. Empty, whitespace, malformed, and non-text values are translated at the Application boundary to `ResearchBaseError(ErrorCode.VALIDATION_ERROR)`.

PR-06 does not parse, download, or store manifest files. `manifest_hash` is distinct from the derived snapshot `content_hash`.

Covered by `tests/integration/test_pr06_application.py::test_snapshot_rejects_invalid_manifest_hash` and the domain material oracle in `tests/unit/domain/test_pr06_dataset.py`.
