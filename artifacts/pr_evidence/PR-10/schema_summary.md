# Schema summary

Migration 0010_measurement creates exactly measurements with:

- id, run_id, metric_definition_version_id
- numeric_value, structured_value, unit, evaluation_scope
- content_hash, created_by, created_at

The value XOR check is ck_measurements_value_xor. The three foreign keys use
ON DELETE RESTRICT. No row version, lifecycle status, current pointer, update
timestamp, MeasurementVersion, unique content constraint, or later-phase table is
introduced. A PostgreSQL trigger rejects UPDATE and DELETE.
