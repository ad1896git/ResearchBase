# Version contract report

`ClaimVersion` directly uses the shared PR-03 `VersionStatus`, `freeze_material`, and `require_transition` contract. The unit test `test_claim_version_is_directly_wired_to_shared_pr03_contract` adapts `ClaimVersion` to the reusable PR-03 harness; the harness passed.

Observed application coverage: create atomically creates Claim + version 1 + same-parent pointer; revise creates the next parent-local DRAFT; freeze records support-set hash, content hash, hash scheme, frozen time, and updates the same-parent pointer; history is deterministic and retains prior versions. PostgreSQL trigger coverage rejects finalized material mutation while allowing the defined FROZEN -> SUPERSEDED transition. Identity and DRAFT row-version stale writers return `CONCURRENT_MODIFICATION`.
