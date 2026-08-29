# Immutability report

There is no public StatisticalResult update command and no repository update,
delete, or save method. PostgreSQL trigger `statistical_results_immutable`
rejects UPDATE and DELETE for the parent row. The integration matrix attempted
direct updates to `project_id`, `analysis_type`, `result_payload`,
`analysis_definition`, `content_hash`, `created_by`, and `created_at`; every
attempt raised a PostgreSQL DBAPI error and the row remained unchanged.

PostgreSQL trigger `statistical_result_inputs_immutable` rejects input INSERT,
UPDATE, and DELETE after result creation. The application adapter can insert
edges only while the parent row was inserted in the same transaction. Direct
SQL INSERT, all three input-field UPDATE attacks, and DELETE were rejected;
the exact edge set remained unchanged.
