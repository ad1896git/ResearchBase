# PR-12 schema summary

Migration `0014_claim_evidence` creates exactly three tables:

- `claims`: `id`, `project_id`, `current_version_id`, `created_by`, `created_at`, `row_version`.
- `claim_versions`: `id`, `claim_id`, `version_number`, `status`, `statement`, `scope`, `qualification`, `support_set_hash`, `content_hash`, `created_by`, `created_at`, `frozen_at`, `row_version`.
- `evidence_relations`: `id`, `claim_version_id`, `measurement_id`, `statistical_result_id`, `relation_type`, `qualification`, `created_by`, `created_at`.

Observed schema tests passed for the exact columns, `version_number > 0`, the `VersionStatus` CHECK, the relation-type CHECK, the Measurement/StatisticalResult XOR CHECK, `UNIQUE(claim_id, version_number)`, both partial unique indexes (`uq_evidence_measurement`, `uq_evidence_stat`), and the current-version foreign key. Foreign keys are hard typed and `ON DELETE RESTRICT`; no unauthorized content-hash or evidence cardinality uniqueness was added.
