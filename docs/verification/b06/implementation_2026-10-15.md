# B06 implementation and review remediation — 2026-10-15

> Integration update: the current migration is
> [`0051_b06_revision_action.py`](../../../migrations/versions/0051_b06_revision_action.py),
> parented on `0050_b01_resolution_admission`. Its executable DDL is unchanged.
> The names and counts below record the original lane's verification. See the
> [combined integration evidence](../b01-b04-b05-integration.md) for the final chain.

The approved issue-based first slice implements NEW_EXPERIMENT, ANALYSIS_CHANGE,
CLAIM_CHANGE, CONCLUSION_CHANGE and SOURCE_CHANGE for both admitted review targets.
Decision-bearing actions, NO_CHANGE, manuscript results and Issue effects remain
excluded. One forward migration, 0048_b06_revision_action, follows the unchanged
0047 head. Write admission/replay starts with the exact B inventory in READ
COMMITTED; exact reads use READ ONLY REPEATABLE READ without explicit locks.

## Current evidence scope and gate limitations

Restored every changed HEAD-owned PR2-20 evidence file directly from `git show
HEAD:path`, including the committed pyright report, and removed generated files.
No committed evidence was hand-edited in this remediation. The former whitespace
repair is withdrawn. `git diff HEAD -- pr_evidence` is empty.

On the latest review turn, `git status --short pr_evidence | wc -l` returns **0**
and `git diff HEAD -- pr_evidence` is empty. The loop cleared the former 86
deleted intent-to-add entries between turns; no evidence/index cleanup remains.
This was observed before any changes in this turn and checked again at handoff.

Restoring the committed evidence exposes the pre-existing static failure:
`git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff HEAD` returns **exit 2**
for line 4, a new blank EOF line in
`pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt`.
That command compares committed revisions only, proving this is inherited.
The B06 static test/baseline is not weakened and the evidence remains restored.
Consequently no full-gate PASS is claimed for this final tree.

### Clean HEAD reproduction requested by the reviewer

The exact command attempted in the main checkout was:

```sh
git stash -u && uv run pytest -o addopts='' -q tests/unit/phase2/test_pr2_04_static_acceptance.py
```

It returned exit 1 before pytest because the sandbox rejects `.git/index.lock`
with `Operation not permitted`. To run the test without changing the candidate,
created a temporary local copy under the repository's ignored `.pytest_cache/`:

```sh
git clone --shared --no-checkout . .pytest_cache/b06-clean-head
git -C .pytest_cache/b06-clean-head checkout --detach 6d978ed254405316bb8502ea5985e21e9b2162da
```

In that detached checkout, with the same uv environment documented below and
`PYTHONPATH="$PWD/src"`, executed the **exact stash-and-pytest command above**.
The stash saved only the temporary untracked `.venv` environment symlink;
the checkout contains no B06 changes. The result is **exit 1, 1 failed, 1 warning
in 6.98s**. The assertion at static-acceptance test line 81 received exit 2 from
`git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff`, with the same
committed `pyright-000.txt:4: new blank line at EOF` diagnostic.

The complete unedited command output is losslessly encoded as `output_lines` in
[clean-head-static-acceptance.json](clean-head-static-acceptance.json). Concatenating
those strings restores every byte of the captured text, including pytest
indentation; the JSON representation introduces no trailing-whitespace defect.
After the run, `git status --porcelain` in the detached checkout was empty and
`git rev-parse HEAD` returned `6d978ed254405316bb8502ea5985e21e9b2162da`.
This reproduces the test failure on the actual clean base, rather than inferring
it from a diff check. The committed evidence and the gate remain unchanged.

### Approved migration references and status line

The appended `tests/test_architecture.py` allowlist entry for
`0048_b06_revision_action.py` permits references to the **existing**
`literature_evidence` and `scientific_conclusions` tables. They occur in inventory
B and in structural project/relevance SELECT queries (and the restored downgrade
guard); they are not new table definitions. The review's description that they
occur only in the inventory string is narrower than the actual migration.
The separate test
`tests/architecture/test_b06_revision_action.py::test_forward_migration_changes_guards_only_and_keeps_existing_history`
asserts that the entire 0048 file contains neither `CREATE TABLE` nor `ALTER TABLE`,
and prohibits destructive history writes. The reference allowlist does not exempt
0048 from those assertions.

`git diff HEAD -- docs/proposals/B06_RevisionAction_Full_Contract_DRAFT.md | head`
shows the requested status-line change. The exact current line (line 3) is:

```text
**Status: APPROVED by owner 2026-10-15 — first slice authorized for implementation**
```

Earlier full-suite runs reported 5753 passed/49 skipped after an evidence edit;
that result does not certify the restored final tree. The previous instruction to
run the exact full command was interpreted as overriding the original focused-run
restriction. This remediation follows the review's focused-suite requirement and
leaves another full-suite execution to the loop.

## Shared verifier substitution and long-chain regression

The guide §12.3 step 3 names `application/literature_evidence.py` and authorizes:
“Extract reusable pure/read verification where necessary”. B06 must verify full
historical snapshot closure without an arbitrary recursion cutoff. Reused the
existing `_snapshot` verifier, extracted `_snapshot_material`, and replaced only
recursive traversal with an iterative visited-set traversal. Hash material,
selected-snapshot validity semantics, owning write transactions and lock order
remain unchanged. This is an explicitly recorded shared-reader substitution,
not a new scientific contract or service boundary.

`tests/unit/phase2/test_revision_action.py::test_shared_snapshot_verifier_checks_history_beyond_recursion_limit`
exercises the actual shared verifier over `sys.getrecursionlimit() + 25` snapshots.
Its independent literal R2 dictionaries verify the exact head hash and traversal
of every predecessor/relation. Historical stale evidence does not poison a valid
selected snapshot; selected evidence dispute and target invalidation change the
current validity without changing material hashes. Corrupting the oldest saved
hash fails with PROVENANCE_CLOSURE_VIOLATION, proving history is not truncated.

The existing owning suite `tests/integration/phase2/test_m3_evidence.py` was
explicitly included in the recorded **108 passed** adjacent-service run below.
Its following tests exercise the shared snapshot verifier:

- `test_pg_manual_evidence_replay_and_restart`: exact hash, replay and fresh read.
- `test_pg_snapshot_sequence_empty_correction_and_sealed_rows`: predecessor
  traversal, an empty replacement snapshot and immutable relations.
- `test_pg_authority_replay_integrity_and_derived_staleness`: disputed support,
  altered/missing document rejection and derived STALE validity.
- `test_pg_claim_link_uses_unchanged_phase1_closure`: exact Claim snapshot binding.
- `test_pg_upstream_retraction_stales_historical_support`: retraction changes
  validity without changing the saved snapshot hash.
- `test_pg_independence_missing_approval_related_and_conflicts`: support review
  independence and contextual snapshots.

The B06 PostgreSQL regression
`test_replacement_snapshot_keeps_ancestor_retraction_as_history` also verifies a
replacement snapshot/conclusion after prior-source retraction. This change is
**support-snapshot predecessor traversal**, not source-lineage traversal:
`previous_snapshot_id` is distinct from SourceVersion's
`predecessor_source_version_id`.

### Naming and location substitution record

Recorded physical substitutions: `literature_support_snapshots`;
`conclusion_version_id` on conclusion inputs; `version_kind` for source kind;
`enable_revision_action_snapshot_reads()` for protected readers; Experiment types
in `domain/experiment.py`; trace SQL in `persistence/publication_repository.py`.

## Observed owning-writer commit orders

Guide §12.2 permits existing target-first Review/Decision/novelty protocols because
B06 takes no scientific row lock while holding B. §12.4 requires actual owning
races and PostgreSQL witnesses; no weaker “no deadlock” criterion is substituted.

The normal-role Review overlap test now runs both `review_first` and
`action_first`. Its writer holds the exact reviewed conclusion row FOR UPDATE.
A third connection demonstrably waits on that row (`pg_blocking_pids`,
`pg_stat_activity`, transactionid lock witness) while RevisionAction proceeds.
Both commit sequences are asserted and both saved records are read through a
fresh connection. Review writes outside B and therefore need no fabricated
inventory wait.

The Claim overlap now executes the actual owning `freeze_claim_version` command
on an evidence-linked draft, in both orders. Writer-first observes RevisionAction
waiting at its FIRST inventory statement on the owning writer. Action-first holds
the writer's parent row while RevisionAction inserts, then releases the writer:
its real UPDATE claims waits on RevisionAction's inventory SHARE, witnessed by
PostgreSQL. RevisionAction commits without waiting back on the parent row; the
writer then commits. Both orderings and frozen/action history are verified.
The source/evidence owning-writer and validity/role witnesses remain covered.

## Focused verification

Runtime uses the lane source and the existing locked shared environment:

```sh
export PYTHONPATH="$PWD/src"
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export UV_CACHE_DIR=/tmp/b06-uv-cache
export UV_NO_SYNC=1
```

Commands and counts below are observed runs, not inferred from collection. No
branch, commit or push was created in the candidate checkout. The detached
temporary base copy used the specifically requested stash command for reproduction.
PostgreSQL is the existing real 18.x server.

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check .
```

Exit 0: **0 errors, 0 warnings, 0 informations**; **540 files already formatted**;
**All checks passed**.

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider tests/unit/phase2/test_revision_action.py tests/unit/phase2/test_pr2_15_uow_errors.py
```

Exit 0: **63 passed in 0.69s** (40 RevisionAction, 23 UoW error cases).

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider tests/architecture/test_b06_revision_action.py tests/architecture/test_basic_approval.py tests/architecture/test_import_boundaries.py tests/test_architecture.py
```

Exit 0: **31 passed, 1 warning in 0.73s** (3 new B06, 3 Basic Approval,
13 import-boundary and 12 architecture cases).

```sh
uv run pytest -o addopts='' -q tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit 1: **1 failed, 1 warning in 5.83s**, solely the inherited committed EOF
whitespace described above. The cause is existing evidence, not a B06 source
regression. This failure is explicitly not reported as PASS.

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b06_revision_concurrency.py
```

Exit 0: **96 passed, 298 warnings in 79.41s (0:01:19)**, no skips.
The three suites account for **53**, **34** and **9** cases respectively.
The two strengthened parametrized races add one case each; the long-chain unit
regression adds one. The new B06 architecture module contributes 3 cases.

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_18_concurrency.py
```

Exit 0: **108 passed, 260 warnings in 103.73s (0:01:43)**, no skips.

Latest review-evidence rerun, after documenting findings 3–6:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check .
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider tests/architecture/test_b06_revision_action.py tests/test_architecture.py tests/unit/phase2/test_revision_action.py::test_shared_snapshot_verifier_checks_history_beyond_recursion_limit tests/integration/phase2/test_m3_evidence.py
```

Both commands returned exit 0. Static: **0 errors, 0 warnings, 0 informations**,
**540 files already formatted**, **All checks passed**. Targeted tests:
**29 passed, 16 warnings in 5.82s**, no skips. The exact clean-HEAD static-test
failure is separately recorded above and is not part of this passing subset.

Final disposition: implementation and strengthened focused regressions pass.
The evidence status count is **0** and its HEAD diff is empty. The full gate is
**not PASS** because the committed inherited EOF whitespace is preserved as
requested. The exact static test now demonstrably fails on clean base HEAD too;
its complete output is attached above. No B06 failure is hidden by modifying
committed evidence or relaxing the gate.
