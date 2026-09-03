# Error Equivalence Report

The stable registry contains ten current ResearchBase error codes. The acceptance explicitly asserts the complete
HTTP and CLI maps:

| Code | HTTP | CLI |
|---|---:|---:|
| `VALIDATION_ERROR` | 422 | 2 |
| `NOT_FOUND` | 404 | 3 |
| `INVALID_STATE_TRANSITION` | 409 | 4 |
| `VERSION_NOT_FROZEN` | 409 | 4 |
| `IMMUTABLE_RECORD` | 409 | 4 |
| `CONCURRENT_MODIFICATION` | 409 | 4 |
| `DUPLICATE_CONTENT` | 409 | 4 |
| `FROZEN_REFERENCE_REQUIRED` | 409 | 5 |
| `PROVENANCE_CLOSURE_VIOLATION` | 409 | 5 |
| `REFERENTIAL_INTEGRITY_ERROR` | 409 | 5 |

Representative application, HTTP, and CLI tests prove reachability and normalized public output. No expected
ResearchBase error falls through to exit 70; exit 70 is reserved for unexpected internal adapter errors.
