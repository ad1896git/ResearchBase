# PR-07 schema summary

Migration `0006_artifact_version` creates exactly `artifacts` and `artifact_versions`.

`artifacts` has `id`, nullable `project_id`, bounded `artifact_type` and `name`, optional
description, nullable `current_version_id`, `created_by`, `created_at`, and `row_version`.
`artifact_versions` has the specified identity, parent-local version number, lifecycle
status, locator/media/size metadata, `content_hash CHAR(64)`, JSONB metadata, audit fields,
freeze timestamp, and row version.

Foreign keys are `RESTRICT`, including the circular current-version pointer. The database
also enforces positive version numbers, non-negative known byte sizes, allowed statuses,
unique `(artifact_id, version_number)`, and unique `(artifact_id, content_hash)`.
