# Immutability trigger report

For one persisted DatasetSnapshot, `test_snapshot_trigger_rejects_update_of_every_field` runs isolated transactions and fresh reads for all seven fields:

| Field | Direct UPDATE | Fresh-read unchanged |
|---|---|---|
| `dataset_id` | rejected | yes |
| `manifest_hash` | rejected | yes |
| `selection_definition` | rejected | yes |
| `manifest_locator` | rejected | yes |
| `content_hash` | rejected | yes |
| `created_by` | rejected | yes |
| `created_at` | rejected | yes |

The existing PostgreSQL immutable-row trigger was not changed semantically by PR-06R.
