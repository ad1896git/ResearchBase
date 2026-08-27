# PR-06 schema summary

Migration: `migrations/versions/0005_dataset_snapshot.py`

`datasets` contains exactly: `id`, nullable `project_id`, `name`, `description`, `source_locator`, `lifecycle_status`, `created_by`, `created_at`, and `row_version`. The project and actor foreign keys use `ON DELETE RESTRICT`; lifecycle values use the existing `active`/`archived`/`retired` convention.

`dataset_snapshots` contains exactly: `id`, `dataset_id`, `manifest_hash`, `selection_definition`, `manifest_locator`, `content_hash`, `created_by`, and `created_at`. Dataset and actor foreign keys use `ON DELETE RESTRICT`. The table has `UNIQUE(dataset_id, content_hash)` and no `row_version`.

The schema test verifies table presence, exact column sets, RESTRICT foreign keys, and the composite uniqueness constraint against real PostgreSQL.
