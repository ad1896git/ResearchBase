# Error Mapping Report

`test_all_researchbase_error_codes_have_frozen_status_mapping` asserts exact set equality with the
10-member stable `ErrorCode` registry, envelope shape, status, and request ID.

| Code | HTTP | Proof |
|---|---:|---|
| VALIDATION_ERROR | 422 | transport integration + mapper unit |
| NOT_FOUND | 404 | PostgreSQL HTTP + mapper unit |
| INVALID_STATE_TRANSITION | 409 | PostgreSQL HTTP + mapper unit |
| VERSION_NOT_FROZEN | 409 | PostgreSQL HTTP + mapper unit |
| IMMUTABLE_RECORD | 409 | PostgreSQL HTTP + mapper unit |
| FROZEN_REFERENCE_REQUIRED | 409 | mapper unit; no fabricated state |
| CONCURRENT_MODIFICATION | 409 | PostgreSQL HTTP + mapper unit |
| DUPLICATE_CONTENT | 409 | mapper unit; accepted create paths may be idempotent |
| REFERENTIAL_INTEGRITY_ERROR | 409 | PostgreSQL HTTP + mapper unit |
| PROVENANCE_CLOSURE_VIOLATION | 409 | mapper unit; no fabricated state |

Expected stable codes falling through to 500: 0. Controlled unexpected errors return generic
`INTERNAL_ERROR`; persistence/driver/traceback text is absent.
