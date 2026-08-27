# PR-01R Finding Disposition

IRR-P1-001  ACCEPTED → FIXED

The scanner now recurses, resolves package-relative imports, reconstructs package-level imports,
and flags obvious literal `import_module` / `__import__` calls. Its static limitation for dynamic
values is documented by the implementation scope and is not treated as a runtime import guarantee.

IRR-P2-001  ACCEPTED → FIXED

UUIDv7 tests now freeze timestamp placement, version/variant bits, controlled random field layout,
and the public generator's wall-clock timestamp window.

IRR-P2-002  PARTIALLY ACCEPTED → POLICY FROZEN

The reviewer identified a possible semantic-equivalence risk, but the frozen PR-01 supported
subset does not require coercing `1` and `1.0`, normalizing signed zero, or normalizing Unicode.
Current behavior is explicitly documented and frozen as `canonical-json-v1` with golden vectors.

IRR-P2-003  ACCEPTED IN PRINCIPLE → SCHEME IDENTIFIABLE

Stable machine-readable identifiers now distinguish raw-byte hashing and canonical-JSON hashing:
`sha256-bytes-v1` and `sha256-cjson-v1`. Later persisted material hashes must retain the scheme.

IRR-P2-004  ACCEPTED → FIXED

Malformed digest text and unsupported public-constructor input now have regression coverage.

IRR-P2-005  DOWNGRADED TO P3 → NO OVERENGINEERING

The frozen PR-01 contract requires bounded JSON-compatible diagnostic details, not recursive
immutability. The remediation adds a documentation boundary that details are diagnostic payload,
not canonical scientific state, and intentionally does not add a new immutable-container model.
