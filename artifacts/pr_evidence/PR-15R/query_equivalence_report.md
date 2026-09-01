# Query Equivalence Report

| Route | Fixture cardinality | Direct vs HTTP |
|---|---:|---|
| Run provenance | 3 input/output members | complete JSON semantics equal |
| ClaimVersion trace | 2 evidence paths | complete JSON semantics equal |
| downstream impact | 4 impact targets | complete JSON semantics equal |

Equality includes nested closure, trace paths, relation type/qualification, roles/ordinals,
content hashes, and governance impact paths/targets. UTC `+00:00` and JSON `Z` are normalized as
equivalent UTC representations for direct DTO comparison.
