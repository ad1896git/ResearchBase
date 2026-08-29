# History and exact-reference report

Create/freeze/revise integration coverage passed. Revising a frozen ClaimVersion creates a new DRAFT without copying or retargeting old EvidenceRelations. The old frozen version retains its exact evidence set, support_set_hash, and content_hash; the new version starts with its own empty evidence set. Closure and query tests use persisted historical IDs and do not resolve current/latest provenance.
