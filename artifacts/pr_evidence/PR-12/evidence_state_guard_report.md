# Evidence state-guard report

Application link and unlink commands lock the ClaimVersion and require `DRAFT`; non-DRAFT mutations return stable application errors. PostgreSQL trigger `evidence_relations_draft_only` independently rejects INSERT, UPDATE, and DELETE for FROZEN, SUPERSEDED, and ABANDONED parents. Direct SQL attack tests passed for frozen and other finalized states.

The ClaimVersion trigger `claim_versions_finalized_immutable` protects finalized material and permits only the specified operational status transition. Direct SQL tests attempted each material field and passed.
