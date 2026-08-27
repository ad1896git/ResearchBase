# PR-02 Transaction Report

All scenarios ran against the real PostgreSQL service with a synchronous SQLAlchemy Session.
Every post-condition opened a new `SqlAlchemyUnitOfWork`, which creates a new Session.

## Results

- `test_commit_persists_cross_repository_records`: PASS. Actor and Project were committed in one
  UoW and both were read from a new UoW.
- `test_explicit_rollback_discards_records`: PASS. Actor and Project were added in one UoW,
  explicitly rolled back, and both were absent from a new UoW.
- `test_exception_rolls_back_all_repositories`: PASS. An exception before commit removed both
  records; both absence checks used a new UoW.
- `test_atomic_multi_repository_rollback_on_failure`: PASS. A failure after Actor and Project
  writes left neither record visible from a new UoW.
- `test_project_created_by_foreign_key_is_enforced_by_postgresql`: PASS.
- `test_workspace_foreign_keys_are_enforced_by_postgresql[actor]`: PASS with a valid Project and
  nonexistent Workspace `created_by` Actor.
- `test_workspace_foreign_keys_are_enforced_by_postgresql[project]`: PASS with a valid Actor and
  nonexistent Project.
- `test_external_key_unique_constraint_is_enforced_by_postgresql`: PASS; the database unique
  violation is retained as the cause of the stable application error.

The complete PostgreSQL integration suite passed with `16 passed, 80 deselected`; the full suite
passed with `96 passed`.
