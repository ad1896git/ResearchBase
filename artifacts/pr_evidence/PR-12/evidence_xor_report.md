# Evidence XOR report

EvidenceRelation validates exactly one of `measurement_id` and `statistical_result_id` at the domain/application boundary and migration `0014_claim_evidence` repeats the invariant in `ck_evidence_relations_source_xor`. Invalid both-null, both-present, and invalid relation-type inputs produced stable application validation errors; direct PostgreSQL schema tests passed.

Allowed relation types are exactly `supports`, `contradicts`, `qualifies`, and `context`. The partial unique indexes enforce one same-source/same-relation edge per ClaimVersion while allowing the same source with a different relation type. The application and PostgreSQL schema suites passed these cases.
