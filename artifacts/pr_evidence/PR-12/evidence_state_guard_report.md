# Evidence state-guard report

Application link and unlink commands lock the ClaimVersion and require `DRAFT`; non-DRAFT mutations return stable application errors. PostgreSQL trigger `evidence_relations_draft_only` independently rejects INSERT, UPDATE, and DELETE for FROZEN, SUPERSEDED, and ABANDONED parents. Direct SQL attack tests passed for frozen and other finalized states.

The ClaimVersion trigger `claim_versions_finalized_immutable` protects finalized material and permits only the specified operational status transition. Direct SQL tests attempted each material field and passed.

## PR-12R reconciliation

The original FROZEN SQL test did not cover every required source/field combination, and SUPERSEDED/ABANDONED coverage was representative only in part. PR-12R expands direct PostgreSQL attacks to Measurement and StatisticalResult INSERTs, claim_version_id/measurement_id/statistical_result_id/relation_type/qualification UPDATEs, DELETE, and INSERT/UPDATE/DELETE representatives for both SUPERSEDED and ABANDONED. Each rejection is followed by a fresh connection and UoW read of the exact edge set and unchanged support/content hashes.
