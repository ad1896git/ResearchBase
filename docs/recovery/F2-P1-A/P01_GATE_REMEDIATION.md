# P01 gate remediation

Status: **CONFIRMED_FIXED**

This is an implementation candidate for independent review, not independent closure. Base candidate: `86658eb83bb0552da36510368d70fe5c049ec086`. Resulting exact SHA is in external `P1_A_CHECKPOINT.md`.

## Reproduction and cause

The actual historical object ea216c9babea322808b3885f563d276b571575ab is unavailable. `git diff --check <historical> HEAD` exits128. Its changed-Python selection also exits128 with empty stdout. The original shell ignores that selection exit, sends empty bytes to its Python consumer and records formatter_changed_scope PASS. The original shell independently records historical ancestry PASS without executing an ancestry check. Later diff-check fails, so this was a false subgate result, not proof of a whole-host false PASS.

A direct test executes only the formatter block extracted from the exact F2 Git blob with a failing Git prerequisite: original block reports PASS; repaired block reports FAIL. No host certification or database setup is invoked. Initial tests failed before implementation; final focused checks pass (external test-results report/log).

## Executable changes

- `scripts/pr2_04_recovery_static_gates.py` is the shared fail-closed consumer for lineage, formatter selection and whitespace comparison. Both base and candidate must resolve to commit objects and actual ancestor comparison must succeed before results are derived. Failed selection raises, never becomes an empty scope. NUL-separated extant added/copied/modified/renamed Python paths are passed to Ruff as separate arguments; deletes have no current bytes to format. A verified empty diff is distinguished from failed selection. Formatter/tool failure propagates nonzero. CLI command/prerequisite errors exit2 without a PASS record.
- `scripts/researchbase_host_pr2_04_verification.sh`: replaces the unconditional ancestry record, unchecked selector/formatter block and missing-object diff-check with shared gates; captures helper exits; records separate historical and recovery lineage. Summary no longer labels an unavailable historical SHA as accepted_baseline (`null`); it states the actual recovery comparison baseline and original_history_recovered=false. Fixed live checkout/branch now identifies this remediation worktree, preserving existing dry-run-only override protections.
- `tests/unit/phase2/test_pr2_04_static_acceptance.py`: uses the same recovery lineage/diff/formatter commands and records their output. Existing whole-repository Ruff/Pyright, raw formatter and FORMAT-BASELINE-01 delta obligations remain. This formal acceptance node itself is NOT_RUN in P1-A.
- `tests/unit/phase2/test_pr2_04_recovery_static_gates.py`: focused negative/positive controls, real Git missing-object/nonancestor cases, direct old/new shell formatter reproduction, shell lineage labels and CLI failures.

## Recovery-specific semantics and limits

1. Missing original ea216/fbe67/cdc50 objects remain unavailable; no search/reconstruction or impersonation occurs. Historical lineage is NOT_RUN when its object prerequisite cannot execute. If it ever becomes available, only its actual ancestry command can produce its own PASS/FAIL.
2. Existing actual B=`dd7dece1b7403a39d662c8fd16d50e4f75201e6d` production seal and C=`bf0a8a14037e21ea8ad086c6b1ab01239d36c650` migration seal remain unchanged and separately verified. They prove recovery content equality, not historical final-tree identity or scientific correctness.
3. Formatter/diff comparison now explicitly uses actual trusted base `14143dc09983ce1765b3b39fda536691193fd868` to actual candidate HEAD. This broader scope includes all reconstructed source changes and later remediation, rather than hiding reconstruction formatting behind a narrow D-only comparison. It is named RECOVERY_TRUSTED_BASE_TO_CANDIDATE. Original FORMAT-BASELINE-01 debt policy is retained.
4. In the shell, historical NOT_RUN contributes to OVERALL failure using existing record() behavior. No whole-host acceptance PASS is possible merely because the alternative content checks succeed. A future independent decision on sufficiency of recovery alternatives is separate; this task does not grant acceptance or relax the historical requirement to PASS.

Full formatter scope, whole-repository static acceptance, full regression, F3, PostgreSQL host certification and evidence sealing remain NOT_RUN. Changed-file checks cover only this remediation's three Python files. Reconstructed formatting debt, all other review findings and declared inventory/host limitations remain outside scope. No production dependencies or product/migration source changed. One repair strategy succeeded; no second strategy was needed.
