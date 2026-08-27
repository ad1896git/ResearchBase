# Error model report

The real Application paths now cover:

- missing Dataset → `ResearchBaseError(ErrorCode.NOT_FOUND)` and no persisted snapshot;
- invalid manifest hash → `VALIDATION_ERROR`;
- unserializable selection definition → `VALIDATION_ERROR`;
- missing actor → stable `NOT_FOUND`;
- concurrent duplicate → existing snapshot returned, without raw `IntegrityError`.

These cases are covered by `tests/integration/test_pr06_application.py` and pass against PostgreSQL.
