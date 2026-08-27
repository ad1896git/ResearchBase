# Schema summary

`metric_definitions` and `metric_definition_versions` are the only new tables. Columns, nullability, `UNIQUE(metric_definition_id, version_number)`, positive version check, lifecycle check, current-version FK, and actor/project/parent `ON DELETE RESTRICT` FKs match the PR-08 pack. No content-hash uniqueness constraint is present.
