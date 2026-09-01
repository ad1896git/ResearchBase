# ImpactAssessment report

Assessment and the complete target set persist in one transaction. Reassessment creates a new row. PostgreSQL rejects assessment updates and ImpactTarget insert/update/delete after parent creation without unauthorized seal/status columns. Duplicate target identities are rejected; target hashes are resolver-derived. Independent oracle tests cover canonical ordering and material sensitivity.
