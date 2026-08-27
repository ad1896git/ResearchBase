# Schema summary

Added exactly two tables:

- `experiment_specs`: project FK, optional hypothesis FK, current-version pointer, creator, UTC timestamp, optimistic `row_version`.
- `experiment_spec_versions`: parent FK, positive parent-local version number, constrained lifecycle status, six material fields, optional content hash, creator/timestamps, and optimistic `row_version`.

All foreign keys use `ON DELETE RESTRICT`. The current pointer is nullable during bootstrap and is constrained by a concrete FK after the version table exists. No business tables outside PR-05 were added.
