# FK/RESTRICT report

`test_pr06_restrict_foreign_keys_block_referenced_deletes` uses real PostgreSQL and expected-failure transactions. It attempts:

- `DELETE FROM datasets` for a Dataset referenced by DatasetSnapshot — rejected;
- `DELETE FROM actors` for an Actor referenced by Dataset and Snapshot — rejected;
- `DELETE FROM projects` for a Project referenced by Dataset — rejected.

After each rollback, a fresh connection verifies the referenced row remains. The schema test independently verifies all PR-06 foreign keys use `RESTRICT`.
