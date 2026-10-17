# Batch C review remediation — 2026-10-17

Status: **exact full check PASS (exit 0)**. Git staging remains blocked by the
managed filesystem; no unmerged index entries are present.

## Owner decision and implementation

The owner's 2026-10-17 instruction to fix every P0/P1 authorizes applying the
previously proposed B10 compatibility patch. This supersedes byte-identical B10
SQL only for the conflicting finite Decision policy and existing shared basis
dispatch/restoration. B09 SQL remains unchanged. No scientific hash scheme or
slice behavior is broadened beyond the already authorized B07/B11 pairs.

Both unrequested workaround revisions, `0054a_batch_c_compatibility` and
`0057_batch_c_dispatch`, are removed. The only new migrations are B09/B10:

```text
0054_b11_ready_for_submission
  → 0055_b09_approval_tuples
  → 0056_b10_reconsideration (head)
```

B10 drops the actual B11 policy constraint, admits all four existing purposes
with their finite outcome pairs, retains B07/B11 typed dispatch and fixed search
path, and restores B11's policy/dispatch on downgrade. There are no placeholder
CHECKs, disabled scientific constraints, or new canonical schemas. The B08
populated test again runs its original rollback path across the entire head.

CI head check, static baseline, lineage allowlists, migration inventory and all
current head assertions now expect `0056_b10_reconsideration`.

## Exact commands and durable output

All commands run at the repository root with `UV_CACHE_DIR=.uv-cache` exported.
PostgreSQL is 18.6 (Homebrew). No commits, pushes, or branches are authorized.

```sh
uv run pytest -o addopts='' -q -s tests/integration/phase2/test_b08_schema.py::test_populated_b07_upgrade_open_downgrade_and_terminal_refusal tests/integration/phase2/test_batch_c_migration.py
```

Complete log: [focused PostgreSQL](review-focused-postgresql.txt). It includes
Alembic's `upgrade head` → `downgrade base` → `upgrade head` operations, populated
B07 upgrade/downgrade preservation, and the complete B11 schema comparison.
The comparison uses `pg_dump --schema-only --no-owner --no-privileges` before and
after `alembic downgrade 0054_b11_ready_for_submission`. It normalizes only the
random PostgreSQL psql restrict key, indentation/blank lines, and the pre-existing
B09 `END IF; RETURN NEW;` line split. The normalized schema hashes match:
`33b19ffccb5ecce1435edd656f4db54ea6bce38c715c9bcbfe2b9257d0e79844`.
All other DDL, constraints, functions, indexes and triggers are compared.
The [raw schema difference](b11-schema-presentation.diff) shows the only
presentation changes, confined to the existing `pr216_event_insert` function.

```sh
uv run pytest -o addopts='' -q tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/architecture/test_import_boundaries.py tests/test_architecture.py
```

Complete log: [history and architecture checks](review-history-checks.txt).

The separate final unit/architecture run is also retained:

```sh
uv run pytest -o addopts='' -q tests/unit tests/architecture tests/test_architecture.py
```

Result: **4870 passed, 42 warnings in 50.14s**; full log:
[unit and architecture](review-unit-architecture.txt).

The final focused PostgreSQL result is **3 passed, 13 warnings in 5.00s**.
The history/architecture subset is **35 passed, 3 warnings in 1.15s**.

Live command output is captured under ignored `tmp/batch-c-integration/`, then
copied to this evidence directory only after the process exits. An initial run
was interrupted after live repository log writes caused changing dirty-worktree
subjects in PR2-20 evidence rows. No evidence gate or test was relaxed to fix it.

The owner's full command (now explicitly authorized, superseding the earlier
instruction to leave it to the loop):

```sh
! git grep -nE '^(<<<<<<<|>>>>>>>) ' -- . ':!.pipeline' && test $(uv run alembic heads | wc -l) -eq 1 && uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Complete, untruncated output: [full check](review-full-check.txt), **328 lines**.
Result: **9091 passed, 50 skipped, 5659 warnings in 6545.23s (1:49:05)**.
`CHECK_EXIT_CODE=0`. Skipped cases remain skips. Pyright: **0 errors, 0 warnings,
0 informations**; Ruff format: **606 files already formatted**; Ruff lint:
**All checks passed!**. The exact command's merge-marker and single-head predicates
also exited successfully. Head output: [review-heads.txt](review-heads.txt).
The final empty round trip and populated migration checks are included in this
full result, in addition to their focused logs above.

## SQL source comparison

Source lane: `.pipeline/work/lane13/migrations/versions/`.
Source B09 file SHA256:
`36af06527ecb53921e551b3d93e77532a3dcce13689566e66c1df0623a314bbf`.
Source B10 file SHA256:
`c9872071168e54ef4114e7ff9a82e939d617342b870f8f053b28fb9feeed8654`.

The comparisons extract the actual `UPGRADE_SQL` and `DOWNGRADE_SQL` string values
with Python AST/literal evaluation; metadata/comments are excluded.
[B09 source SQL diff](b09-source-lane-sql.diff) is **empty (0 lines/bytes)**.
[B10 source SQL diff](b10-source-lane-sql.diff) shows only the owner-authorized
compatibility changes. It is deliberately not described as empty or byte-identical.
The applied compatibility patch is retained as `proposed-b10-compatibility.diff`
with zero-context hunks so the evidence introduces no trailing-whitespace debt.

## Git index

`git ls-files -u` and `git diff --name-only --diff-filter=U` currently return no
unmerged paths. However, `git add -A -- . ':!.pipeline'` still fails with
`Unable to create .git/index.lock: Operation not permitted` because the managed
filesystem grants `.git` read-only access. The owner has been asked to run that
command from their terminal; no elevated tool execution is available under the
current approval policy. The final retry returned exit **128**, with the same denial:
[git-add output](review-git-add.txt). [Git status](review-git-status.txt) records
all remaining modifications and staged-deletion/unstaged-addition pairs.
[Unmerged index paths](review-unmerged-paths.txt) is empty (0 bytes), independently
confirmed by `git diff --name-only --diff-filter=U`. These `DA` pairs are not
unmerged index stages, but they still need the owner's `git add` to record the
final content. A completely clean committed worktree is not claimed. No commit,
push, or branch was created, honoring the task's explicit restriction.

Earlier failed attempts and their exact commands remain in
[previous-attempt-evidence.md](previous-attempt-evidence.md); they are not current
acceptance evidence.

Full-check log SHA256: `49a10acc68cafde1fa1187513f15d7cb117c79b35f3aae4f683ddbff273b6814`.

Reproduce the SQL-value diffs (read-only; source lane files remain within this repository):

```sh
uv run python - <<'PYSQL'
import ast
import difflib
from pathlib import Path

def constants(path):
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"UPGRADE_SQL", "DOWNGRADE_SQL"}
    }

for old, new in (
    ("0052_b09_approval_tuples", "0055_b09_approval_tuples"),
    ("0053_b10_reconsideration", "0056_b10_reconsideration"),
):
    before = constants(Path(".pipeline/work/lane13/migrations/versions") / f"{old}.py")
    after = constants(Path("migrations/versions") / f"{new}.py")
    diff = "".join(
        "".join(difflib.unified_diff(
            before[key].splitlines(True), after[key].splitlines(True),
            fromfile=f"source-lane:{key}", tofile=f"integrated:{key}", n=0,
        ))
        for key in ("UPGRADE_SQL", "DOWNGRADE_SQL")
    )
    print(new, "SQL diff bytes:", len(diff.encode()))
    print(diff, end="")
PYSQL
```

Observed: B09 **0 bytes**; B10 **9282 bytes** in the retained zero-context diff. The B10 exception is
owner-authorized and is not described as byte-identical.
