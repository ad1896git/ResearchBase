# Query Equivalence Report

| Route | Fixture cardinality | Direct vs HTTP |
|---|---:|---|
| Run provenance | 3 input/output members | complete JSON semantics equal |
| ClaimVersion trace | 1 small / 2 multipath paths | complete JSON semantics equal at both cardinalities |
| downstream impact | 1 small / 5 multipath paths | complete JSON semantics equal at both cardinalities |

Equality includes nested closure, trace paths, relation type/qualification, roles/ordinals,
content hashes, and governance impact paths/targets. UTC `+00:00` and JSON `Z` are normalized as
equivalent UTC representations for direct DTO comparison.
