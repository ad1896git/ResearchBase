# B01 first-slice implementation evidence — 2026-10-15

> Integration update (2026-10-15): the applied B01 migration is now
> [`0050_b01_resolution_admission.py`](../../../migrations/versions/0050_b01_resolution_admission.py),
> following `0049_b05_manuscript_review`. Only the filename, revision and
> down_revision changed; its executable DDL remains byte-identical. The current
> file SHA-256 is `101fc8c7a1408397234854c2f714e3da656c57c369f4bfa1b9d5e259a8614f69`.
> Commands, names and hashes below describe the original lane verification.

Owner authorization: the proposal status now records approval and first-slice implementation authorization on 2026-10-15. This evidence does not declare G1 or Phase 2 accepted. No commit, push or branch creation was performed. The initial implementation used focused checks. The owner subsequently authorized the full required check during review remediation; its result is recorded in the review section below.

## Implemented boundary

- Added frozen/slotted closed command, query and exact readback values, pure UUID/basis/DOI/title validation and the literal existing M2 hash payload.
- Added the shared Application service, typed narrow repository/UoW contracts, existing-relation adapter and composition construction. No CLI command or HTTP route was activated.
- New admissions require an exact frozen version, terminal verified search provenance, an ACTIVE linked source, exact normalized version title, and one same-source VERIFIED DOI with a retained matching verification event and accessible frozen CAS basis. Current correction/retraction follows the existing novelty source-lineage predicate.
- Exact reads/replays preserve the original version, actor, timestamp, basis and hash. They validate historical hashes/frozen references and present read entitlement without applying current admission usability or certifying fulltext availability.
- Writes use READ COMMITTED, the exact first-statement SHARE inventory, fixed advisory key, fresh database-clock authorization checks, one insert and forced deferred constraints. Connection startup options bound the initial lock wait. Only 40001/40P01 retry automatically, with at most three fresh UoWs. Primary-key races receive one fresh authorized exact reread; timeouts and uncertain commit outcomes are not blindly retried.
- Migration `0048_b01_resolution_admission`, directly after the inspected head `0047_pr2_18_novelty_prior_art`, adds only `b01_resolution_closure_at_commit`, calling existing `m2_check_closure()`. Downgrade drops that trigger only. Existing migrations, tables, hashes, M2 orchestration and coverage accounting remain intact.

## Reconciliation and substitutions

- Existing LiteratureSource status column is `lifecycle_status`; used for the guide's ACTIVE/MERGED/RETIRED identity checks.
- Used `metadata_observations.result`, the owning execution `provenance` reader and question validator, plus `_material_from_row(...).digest()` and protected source readers for the existing hash/closure contracts.
- Reused lock-free authority SQL through the existing novelty adapter rather than M2's locking authorization orchestration.
- General identifier-basis verification uses ArtifactStore locator/hash/size checks. The evidence document reader additionally imposes manual-document parser metadata and cannot read legitimate M2 JSON basis artifacts; those document-specific conditions were not substituted for identifier verification.
- Catalog inspection on PostgreSQL 18.6 confirmed tuple constraint `search_result_resolutions_search_result_record_id_source_id_key`, PK `search_result_resolutions_pkey`, and composite FK `search_result_resolutions_source_id_source_version_id_fkey`. Error handling uses these actual driver-reported constraint names.
- Updated only current-head expectation values, predecessor expectation values and appended migration inventory/allowlist entries in shared head-check files. Frozen historical migration bytes were not edited.

## Initial verification (historical, before review remediation)

All commands below used the prefix:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync
```

PostgreSQL tests used the configured real PostgreSQL 18.6 service and disposable migrated databases. No SQLite or live provider calls were used. Read-only sub-agents investigated reuse and reviewed the implementation; only the primary agent wrote files.

| Command suffix | Observed result |
| --- | --- |
| `ruff format --check .` | PASS: 547 files already formatted. |
| `ruff check .` | PASS: All checks passed. |
| `pyright` | PASS: 0 errors, 0 warnings, 0 informations. |
| `pytest tests/unit tests/architecture -o addopts='' -q -p no:cacheprovider` | 2203 passed, 1 failed, 39 warnings in 61.89s. |

The unit/architecture failure is `tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta`. Its `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` finds a pre-existing blank line at EOF in a committed PR2-20 `pyright-000.txt` artifact. The proposal's pre-implementation verification note already records that defect. A focused confirmation of that test also failed (1 failed, 1 warning in 7.93s). Current working-change `git diff --check` passes. At that initial checkpoint, no baseline allowance had been weakened and the historical artifact had not yet been repaired. The review remediation below supplies independent proof and the repair.

Final PostgreSQL results are recorded below.

Dependent regression command:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_pr2_19_search_evidence.py -o addopts='' -q -p no:cacheprovider
```

Result: **44 passed, 53 warnings in 214.96s**. Includes the retained retrieval-is-not-evidence test and the new persisted exact-resolution → identical SourceVersion → independently VERIFIED LiteratureEvidence → frozen ScientificConclusion test. No full G1 acceptance is inferred.

Head-expectation regression command:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta tests/integration/phase2/test_pr2_04_migration_coverage.py::test_historical_migration_bytes_match_frozen_accepted_tree tests/integration/phase2/test_revision_action.py::test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog tests/integration/phase2/test_pr2_15_decision_schema.py::test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py::test_pr2_03_fresh_install_adds_exact_four_tables_and_unique_head tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py::test_pr2_03_populated_downgrade_refuses_before_dropping_tables tests/integration/phase2/test_pr2_03_review_guards.py::test_remediation_child_upgrade_empty_downgrade_and_unique_head tests/integration/phase2/test_pr2_17_authorship_schema.py::test_install_upgrade_exact_catalog_and_one_head tests/integration/phase2/test_pr2_17_authorship_schema.py::test_nonempty_downgrade_refuses -o addopts='' -q -p no:cacheprovider
```

Result: **14 passed, 44 warnings in 12.78s**. Parameterization expands the ten named test functions into fourteen cases.

Read-only independent review against the guide, diff and available evidence found no open P0/P1 in this slice. This is engineering review, not owner acceptance or authorization of another backlog item.

After the broad focused run was started, two concurrency tests were strengthened without changing runtime code: source-only history is now inserted **before** the B01 append, and expiry evidence now includes real durable role expiry plus all required database timestamps. Their final reruns were:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_b01_resolution_concurrency.py::test_b01_append_after_source_only_stays_ambiguous -o addopts='' -q -p no:cacheprovider
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_b01_resolution_concurrency.py::test_fresh_authorization_and_identity_after_observed_initial_wait -o addopts='' -q -s -p no:cacheprovider
```

Results: **1 passed, 2 warnings in 9.13s** and **4 passed, 5 warnings in 30.08s**, respectively. The expiry witnesses are retained in [expiry-witness.txt](expiry-witness.txt): transaction/wait precede expiry, lock acquisition and the final authorization clock follow expiry, and no resolution commits. These are reruns of cases also present in the broad focused group, not additional distinct cases.


Final B01 PostgreSQL group:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_b01_resolution_admission.py tests/integration/phase2/test_b01_resolution_schema.py tests/integration/phase2/test_b01_resolution_replay.py tests/integration/phase2/test_b01_resolution_concurrency.py -o addopts='' -q -p no:cacheprovider
```

Result: **66 passed, 69 warnings in 481.60s**. The strengthened source-only and four wait/expiry cases were subsequently verified with the exact rerun commands above. Existing Alembic configuration deprecation and pytest fixture-module rewrite warnings remain warnings, not failed tests.

Final static verification after the last test changes: `ruff format --check .` reports **547 files already formatted**; `ruff check .` reports **All checks passed**; `pyright` reports **0 errors, 0 warnings, 0 informations**. `git diff --check` exits 0. The new migration's inventory digest is `49ef3a3efe2b2ffac15c5d5b0c083b56169114707bd5fc9b7022d4b6b443c8bd` and matches the appended inventory entry. No accepted migration was modified. At that initial checkpoint the whitespace failure remained open and no gate success was declared; the later repair and final required check are recorded below.

The initial slice stopped after focused evidence; no later backlog work or whole-suite execution had been performed at that checkpoint. The owner subsequently requested the review remediation and full check below.


## Review remediation

The earlier unit/architecture result above was red, not PASS. The initial evidence did not independently establish the origin of that failure. The following clean-HEAD reproduction now supplies that proof, and the historical whitespace defect was repaired without weakening the test or changing its baseline commit.

### Clean-HEAD reproduction of P1

HEAD: `6d978ed254405316bb8502ea5985e21e9b2162da`. The normal `git worktree add --detach` operation was rejected because this workspace's Git metadata is read-only. An independent checkout was instead created by copying the 9.5 MB local Git metadata to `/private/tmp/rb-b01-clean-head/.git` and checking out HEAD detached there. No original repository branch or index was changed. The existing environment was reused through an ignored `.venv` symlink. Before execution, `git -C /private/tmp/rb-b01-clean-head status --porcelain` returned no output. This checkout retained the original `tests/fixtures/phase2_static_baseline.json`, including migration head 0047, and contained no B01 changes.

Command, executed with working directory `/private/tmp/rb-b01-clean-head`:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest -o addopts='' -q -p no:cacheprovider tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Result: exit 1; **1 failed, 1 warning in 5.98s**. [Exact clean-HEAD pytest output](clean-head-static-acceptance.json) records the same assertion and diagnostic:

```text
pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt:4: new blank line at EOF.
```

The independent clean checkout's `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` also exited 2 with precisely that diagnostic. In the B01 checkout, the repair removes exactly one final newline byte from that historical text log. All substantive recorded Pyright output remains intact. No test exemption, baseline commit change, dependency change or accepted migration edit was introduced. `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` now exits 0.

### Generated PR2-20 artifacts (P2)

The 86 generated files in `pr_evidence/pr2-20/a38f03e1974bf422aa603af2c688835691b9c64e1c1af7cea981963199397a9f/` were intent-to-add entries, not staged content: `git diff --cached --name-only` returned no output. `git reset -- <directory>` was rejected because `.git/index.lock` cannot be written in this environment. Their bytes were archived at `/private/tmp/rb-b01-generated-archive/` and removed from the candidate working tree. `git diff HEAD --name-only -- <directory>` returns no output. Read-only intent-to-add index entries may still appear as zero-byte deletions in plain `git status`/`git diff`; none are additions or deletions relative to HEAD.

These files are PR2-20 test products, not B01 deliverables. The generators are `save_observation`, `save_query`, `save_migration`, and `persist_manifest` in `tests/integration/phase2/pr2_20_support.py`, called by `test_pr2_20_migrations.py`, `test_pr2_20_catalog_plans.py`, `test_pr2_20_governance_races.py`, and `test_pr2_20_security.py`; `tests/e2e/test_pr2_20_benchmark.py` also generates benchmark/profile output. Their test helpers and output behavior were not altered. Newly generated untracked outputs from the authorized full rerun will likewise be archived outside the candidate change.

### Reproducible migration inventory hash (P2)

```sh
shasum -a 256 migrations/versions/0048_b01_resolution_admission.py
```

Observed output:

```text
49ef3a3efe2b2ffac15c5d5b0c083b56169114707bd5fc9b7022d4b6b443c8bd  migrations/versions/0048_b01_resolution_admission.py
```

This is exactly the digest appended in `docs/phase2/migration_inventory_phase2.md`. The file remains unchanged by remediation.

### Service maintenance and concurrency evidence (P2)

Extracted `_same_material` and used it for both normal replay and unique-race recovery. Added explicit UoW, principal, UUID, bool, set, row and return annotations to all service helpers. Existing replay tests exercise both paths; no runtime policy or transaction ordering changed. The earlier sections retain the exact four `tests/integration/phase2/test_b01_resolution_*.py` suite paths, full commands, 66/44/14-case results, and the exact 1+4 strengthened concurrency commands and results. The retained expiry witnesses contain database timestamps and zero-row denial evidence.

### Required full check

The owner explicitly authorized this full-suite check during review, superseding the earlier focused-only instruction:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

`UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache` is the sole environment wrapper needed for uv's writable cache. Result: **PASS, exit 0**. Pyright: **0 errors, 0 warnings, 0 informations**. Ruff format: **547 files already formatted**. Ruff lint: **All checks passed**. Pytest: **5812 passed, 49 skipped, 3565 warnings in 5777.71s (1:36:17)**. [Exact command, environment, exit code and full output](required-full-check.json).


The isolated repaired static acceptance test was also run in the B01 checkout:

```sh
UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest -o addopts='' -q -p no:cacheprovider tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Result: **1 passed, 1 warning in 5.76s**. The full required run subsequently included this same test and passed.

After the full check, all newly generated PR2-20 subject directories absent from HEAD were archived outside the candidate working tree. The exact subject IDs and file counts are retained in `required-full-check.json`. These are disposable test products, not B01 deliverables. The only remaining `pr_evidence/pr2-20` change relative to HEAD is the intentional one-byte historical whitespace repair described above. Git index metadata remains read-only; there is no staged content, and the old intent-to-add entries do not introduce generated files into the HEAD-relative candidate diff.

The required check is green. No commit, push, branch creation, later-slice implementation or test exemption was performed.
