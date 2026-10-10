# C03 recovery-gate compatibility blocker

Implementation verdict: **C03_REMEDIATION_BLOCKED**.

Exact P1-A parent: `f1faf2c8fa996c2b4b1516670c9d326181fd8dc2`. Original F2: `86658eb83bb0552da36510368d70fe5c049ec086`. New isolated branch: `recovery/f2-p1-c03`; worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/f2-p1-c03`. Final evidence-only commit SHA is in C03_CHECKPOINT.md; this is not a corrected product candidate.

The human authorization C03-AUTH-001..004 resolves attribution/migration policy. Its §10 also explicitly says: “Modify the P01 fix except to resolve a directly demonstrated compatibility conflict, in which case STOP for authorization.” A directly demonstrated recovery-gate conflict requires that stop here. No product/migration/P01 source was changed.

## Directly demonstrated compatibility conflict

The existing host preflight runs `scripts/pr2_04_recovery_bindings.py` at shell line49.

- `validate_migration_prefix()` line26 allows exactly the sealed prefix plus0025; line41 requires unique0025 head. A virtual0026 directory entry is rejected before its contents are read.
- `validate_production_scope()` line50 requires current src bytes to equal F2-B's hash map exactly. Virtually adding the authorized `executed_by=requested_by` initialization is rejected.
- These are actual unmodified functions executed with virtual read-only filesystem inputs. No synthetic migration is created; no hash seal is edited; no historical object is impersonated. This proves source-level incompatibility, not PostgreSQL behavior.
- Existing R8A topology validator additionally permits exactly0025 beyond its prefix and expects0025 head. Its rejection test is valid for the old candidate; it needs explicit0026 compatibility handling in a corrected candidate.

Although0026 itself is authorized, completing the C03 correction with these preflights requires extending their production-delta/topology policy. Silently widening or replacing the frozen B/C seals could hide unrelated drift and would contradict the explicit stop instruction.

## Concrete continuation scope needing authorization

Authorize an explicit C03-only extension to `scripts/pr2_04_recovery_bindings.py` and the associated migration-topology validators/tests in `scripts/pr2_04_host_acceptance_tests.py` / `tests/unit/phase2/test_pr2_04_r8a_host_topology.py`. Any directly required P01 runner/static compatibility edits must be explicitly included. Preserve archived B/C content hashes, verify old migrations byte-for-byte, admit only the named0026 child and reviewed C03 production delta, and retain unavailable-history NOT_RUN and all fail-closed negative cases. Do not replace old seals with an unconstrained new current-tree seal or permit arbitrary newer migrations/source changes. Final exact modified-path scope must remain documented.

No new architecture reinterpretation is requested; the frozen executed_by semantics and conservative historical handling already have authorization. No implementation repair strategy was attempted. Stop occurred at the demonstrated gate-compatibility boundary.

## Evidence digests

- `PREFLIGHT.json`: `4c4a191ce0bc51b70b43244df6909dcfb1b43ff1bfa72d3b209bd738ca59a4ee`
- `baseline-regressions.log`: `3fc8500b9c8d601556f9bb2c258b4f3ec068b9ebac3dc0eee020327f59426795`
- `compatibility.log`: `067fd56328081d9ea45df11ff046e24ba2c04db98acbf4fa6a4657b5cd33fa96`
- `parent-red.log`: `62b690ffb1a6ad5c5eaa995e1e71bd697433b1cede6238cd8e358f7fa1de5183`
- `test_gate_compatibility.py`: `0f2d26ac8578a9423e06c58e6bec92d0cc830d7aefd8ffa740e12513518f567e`
- `test_parent_contract_red.py`: `50c78b43ed6f8d9966746e84a0f0bf7edf56b164c5422ac13fc1fc61aa11dab2`
- `test_runs.json`: `ca843cdb98f11403dda315c4d05871df7a19004eeb149a1972cffa885c77d7d1`
