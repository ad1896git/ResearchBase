# Error Mapping Report

| Stable error code | Reachable in registry | CLI exit |
|---|---:|---:|
| `VALIDATION_ERROR` | yes | 2 |
| `NOT_FOUND` | yes | 3 |
| `INVALID_STATE_TRANSITION` | yes | 4 |
| `VERSION_NOT_FROZEN` | yes | 4 |
| `IMMUTABLE_RECORD` | yes | 4 |
| `CONCURRENT_MODIFICATION` | yes | 4 |
| `DUPLICATE_CONTENT` | yes | 4 |
| `FROZEN_REFERENCE_REQUIRED` | yes | 5 |
| `PROVENANCE_CLOSURE_VIOLATION` | yes | 5 |
| `REFERENTIAL_INTEGRITY_ERROR` | yes | 5 |

The mapper-unit matrix covers every current `ErrorCode`. Handled errors preserve their stable code and
request ID; unexpected exceptions use exit 70 and the generic message `unexpected internal error`. No expected
ResearchBaseError falls through to 70. Public stderr contains no raw SQLAlchemy, psycopg, SQL, or traceback.
