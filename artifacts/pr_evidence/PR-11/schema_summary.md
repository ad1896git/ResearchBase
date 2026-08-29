# Schema summary

Migration `0011_statistical_result` creates exactly:

- `statistical_results(id, project_id, analysis_type, result_payload,
  analysis_definition, content_hash, created_by, created_at)`;
- `statistical_result_inputs(statistical_result_id, measurement_id,
  input_role, ordinal)`.

The result table has a UUID primary key and RESTRICT foreign keys to `projects`
and `actors`. The input table has the composite primary key
`(statistical_result_id, measurement_id, input_role)`, RESTRICT foreign keys to
`statistical_results` and `measurements`, `input_role VARCHAR(32) DEFAULT
'input'`, and `ordinal INTEGER DEFAULT 0`.

The PostgreSQL schema test observed the exact column sets, named primary and
foreign-key constraints, defaults, trigger names, and absence of lifecycle
columns or a content-hash unique index. No `ON DELETE CASCADE` is present.
