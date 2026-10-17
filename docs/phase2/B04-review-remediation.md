# B04 review remediation — 2026-10-15

Implementation remains the approved first slice. No branch, commit or push was created.

## 1. Static-check failure: clean-HEAD reproduction and fixes

[Exact clean-HEAD transcript](b04-evidence/clean-head-static-acceptance.txt): HEAD `6d978ed254405316bb8502ea5985e21e9b2162da` was exported with `git archive HEAD` into an ignored disposable directory inside this repository. A separate Git index, `GIT_WORK_TREE` and `GIT_DIR` made subprocess Git checks inspect that archive without changing the working index, HEAD or any branch. Before testing, `git status --porcelain` printed nothing and `git diff --exit-code HEAD` exited 0. The archived static baseline still had migration head `0047_pr2_18_novelty_prior_art` and the original pinned baseline commit.

The exact target test failed at line 81 with the same `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` diagnostic: `pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt:4: new blank line at EOF`. Result: **1 failed, 1 warning in 6.15s**, exit 1. This supplies the proof absent from the original summary.

Removing that pre-existing trailing blank line exposed additional B04-local whitespace defects: a blank EOF line in the B04 Pyright transcript and four whitespace-only lines inside the new migration's SQL literals. Those are fixed too. No assertion was removed, no baseline commit or debt allowance changed, and the static baseline diff remains solely the migration-head value update. The appended B04 migration inventory digest was refreshed after whitespace cleanup; no historical migration was edited. The previously failing static-acceptance test passes in the focused remediation run.

## 2. Timeout and legacy snapshot scope

Guide §12.2 explicitly requires: “Install an initial 10s lock timeout/30s statement timeout on the connection before transaction start (engine connection options), so the first SHARE wait is bounded too”. `SET LOCAL` after SHARE cannot bound that initial wait.

The original shared-engine implementation was too broad. Connection timeouts now require the explicit `create_database_engine(..., b04_write_timeouts=True)` option for B04 write factories. Ordinary services and read-engine callers retain their server defaults. `test_connection_timeouts_are_opt_in_for_b04_writes` prevents accidental global application; `test_first_share_wait_is_bounded_and_authority_is_fresh[False]` exercises the opted-in connection against a real blocked first SHARE. The credential-expiry variant also remains covered. Configuring this option is required when composing a B04 write factory.

`SqlAlchemyPublicationRepository.begin_scientific_trace_snapshot()` is restored to its original REPEATABLE READ-only statement. B04 uses its own `prepare_read()` protocol, which sets REPEATABLE READ and READ ONLY before authorization. No legacy helper's behavior is broadened.

## 3. DRAFT nonblocking read evidence

`test_exact_reads_do_not_block_unrelated_insert` is now parameterized over both `DRAFT` and `FROZEN`, with populated Claim, citation and artifact placements. In particular it covers:

- `test_exact_reads_do_not_block_unrelated_insert[citation-DRAFT]`
- `test_exact_reads_do_not_block_unrelated_insert[claim-DRAFT]`
- `test_exact_reads_do_not_block_unrelated_insert[artifact-DRAFT]`

All three execute their normal typed trace builders and protected target reads. A separate connection commits an unrelated INSERT while the reader remains held after authorization's first query; the inserted row remains invisible in the reader's established snapshot. Tests assert REPEATABLE READ, READ ONLY and absence of explicit table, row or advisory lock modes. Exact-version and combined-trace variants run under both states too. The blank lines immediately before the final authorization checks were removed.

## 4. Requested full inventory/approval diff

[Attached readable inventory and approval diff](b04-evidence/review-contract-inventory.diff) and [exact command output encoded losslessly as JSON](b04-evidence/review-contract-inventory.json) record:

```bash
git diff HEAD -- docs/phase2/migration_inventory_phase2.md docs/proposals/B04_Manuscript_Freeze_Contract_DRAFT.md
```

The readable transcript trims blank context padding, including its terminal blank context line. The JSON `stdout` preserves the exact untruncated output, including every context line and its padding. No changed lines are omitted. The proposal changes only its status line to `APPROVED by owner 2026-10-15 — first slice authorized for implementation`. The inventory is byte-identical to HEAD followed by exactly one appended B04 row; this was checked programmatically. Its checksum covers the final new migration.

## 5. Explicit existing equivalents and substitutions

There were **no file naming or location substitutions**: all new module/test paths match the guide, and migration `0048_b04_manuscript_freeze` follows the actual `0047` head. Existing implementation equivalents are explicitly recorded:

- Publication read/write role sets reuse `PublicationService` module constants `_READERS` and `_WRITERS`. B04 preserves those roles; it uses its own nonlocking authority query instead of the locking `PublicationService._authorize` method.
- `SqlAlchemyPublicationRepository.document` retains its original locking default. The new `protected_reads=True` mode omits `FOR SHARE` only when B04 has established its SHARE-protected write inventory or REPEATABLE READ/READ ONLY read snapshot. Source and placement target readers use the same mode.
- The existing `enable_revision_action_snapshot_reads()` hook installs protected Source/Literature/Conclusion adapters, extended to include the Publication adapter. Its DRAFT behavior is now exercised by the three named populated nonblocking tests above.
- The existing conclusion readback names derived validity `validity`; B04 maps it into `ManuscriptVersionReadback.current_validity`.
- Existing placement/combined-trace constructors accept an additive optional ArtifactStore argument for formal frozen verification while retaining draft call signatures.
- B04 connection-timeout setup uses the existing database engine constructor with an opt-in parameter rather than applying guide §12.2's connection options to unrelated services.

These are implementation reuse choices, not changes to scientific semantics, lock inventories, architecture or authorization policy.

## Verification

Focused remediation command (environment: `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache`, `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres`):

```bash
uv run pytest tests/unit/phase2/test_b04_manuscript_contract.py tests/unit/phase2/test_pr2_04_static_acceptance.py tests/integration/phase2/test_b04_manuscript_races.py -o addopts='' -q -rfE -p no:cacheprovider
```

Observed: **67 passed, 73 warnings in 36.66s**. [Exact output](b04-evidence/review-focused.txt).

The exact review-requested full command completed with **exit code 0**:

```bash
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Observed results:

- Pyright: **0 errors, 0 warnings, 0 informations**.
- Ruff format: **546 files already formatted**.
- Ruff lint: **All checks passed**.
- Full pytest: **5,837 passed, 49 skipped, 3,739 warnings in 5,376.01s (1:29:36)**; no failures or errors.
- `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff`: exit 0 after the fixes.

[Complete full-check output](b04-evidence/review-full-check.txt) includes the bootstrap, exact command, full untruncated pytest output and `CHECK_EXIT_CODE=0`. The check used the UV cache and local PostgreSQL admin selector above, plus `DATABASE_URL` pointing at a newly created disposable database migrated to head before the command. The disposable database was removed after completion. The 49 optional benchmark/live-test skips match the prior loop's 49 skips; they are reported as skips, not passes. A preliminary run with `DATABASE_URL` unset was interrupted and is not counted as passing evidence.

The original red result and the clean-HEAD reproduction remain preserved as failures in their respective transcripts. The current full check is green; this does not declare a separate scientific/Phase 2 acceptance gate.
