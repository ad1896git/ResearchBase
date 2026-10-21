# Read-only review

Two sub-agents investigated the approved plan and existing tests, then reviewed the new files without editing them. The primary agent was the only writer. Both rechecks reported no remaining P0/P1 in their reviewed scope.

| Finding | Resolution and passing evidence |
| --- | --- |
| P1: correction concurrency could pass sequentially | Pause leading freeze, observe following backend's PostgreSQL advisory wait, release in finally, assert one frozen successor and committed current pointer. `test_concurrent_corrections_cannot_fork_current_lineage` passes. |
| P1: retry transaction IDs alone did not prove fresh reads | Instrument fresh Decision reviews in each transaction; require three distinct transactions/read observations for serialization/deadlock exhaustion. Equivalent discussion authority-read exhaustion is covered. All four cases pass. |
| P1: pre-admission review/target hash corruption did not cover a saved Decision | Add committed Decision content_hash/basis_set_hash corruption, fresh exact replay, exact closure rejection and unchanged row counts. Both cases pass. |
| P1: invalid new lineage admission lacked durable assertions | Assert owning error codes and fresh unchanged counts separately after rejected conclusion and snapshot admission, with preserved historical hashes/bytes. All direct/Claim-snapshot correction/retraction cases pass. |
| P3: commands were only globally closed | Add per-scenario command allowlists and cross-scenario rejection tests. |

The unfrozen-predecessor probe supplies a well-formed placeholder hash because draft SourceVersion rows have no frozen content hash. It tests a DRAFT predecessor's rejection; no successful frozen binding is fabricated. Current HUMAN-only discussion policy remains enforced, including denial of an otherwise provisioned Agent actor.

Review does not claim missing-contract acceptance or full PR2-19 gate success. Execution evidence is the final focused runs in this directory.
