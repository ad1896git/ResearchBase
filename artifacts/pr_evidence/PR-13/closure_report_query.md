# Closure report query

Claim and Run reports reuse the accepted PR-09/PR-12 `ProvenanceClosureValidator` inside the same
UoW. DTO fields are `complete`, `visited_count`, and ordered violations with code, object type/ID,
path, and message. The DRAFT/empty-evidence test proves the query does not manufacture completeness.
