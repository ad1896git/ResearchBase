# Evidence guard matrix report

Every case below was rejected by the real PostgreSQL trigger and followed by a fresh engine connection plus a fresh application UoW read. The read asserted exact edge IDs, source IDs, relation types, qualification, edge count, support_set_hash, and Claim content_hash remained unchanged.

## FROZEN parent

| Source/operation | Attacked field | Expected | Actual |
|---|---|---|---|
| Measurement INSERT | new Measurement edge | reject | rejected; fresh exact two-edge set and hashes unchanged |
| StatisticalResult INSERT | new StatisticalResult edge | reject | rejected; fresh exact two-edge set and hashes unchanged |
| existing edge UPDATE | claim_version_id | reject | rejected; fresh exact two-edge set and hashes unchanged |
| Measurement edge UPDATE | measurement_id | reject | rejected; fresh exact two-edge set and hashes unchanged |
| StatisticalResult edge UPDATE | statistical_result_id | reject | rejected; fresh exact two-edge set and hashes unchanged |
| existing edge UPDATE | relation_type | reject | rejected; fresh exact two-edge set and hashes unchanged |
| existing edge UPDATE | qualification | reject | rejected; fresh exact two-edge set and hashes unchanged |
| existing edge DELETE | row deletion | reject | rejected; fresh exact two-edge set and hashes unchanged |

The FROZEN fixture contains one Measurement edge and one StatisticalResult edge, so both source types are covered in the same exact-state assertion.

## SUPERSEDED and ABANDONED parents

For each state, representative INSERT, UPDATE qualification, and DELETE attacks were individually rejected. After every case, a fresh read showed the original one-edge set, source ID, relation type, qualification, edge count, and unchanged nullable support/content hashes. Legitimate DRAFT link/unlink behavior remains covered by the existing application test.
