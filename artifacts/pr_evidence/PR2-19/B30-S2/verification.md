# B30-S2 and B13 focused verification — 2026-10-19

AQ-S2-01 authorizes B13 forward migration 0069, with no new schema. Its only
behavioral change adds P14B1 to b13_stale's business-denial allowlist. The migration
docstring lists the audited fact and integrity SQLSTATEs of B14a/B14/B17 and the
B12 PREPARE maintenance path. Downgrade restores the literal 0067 function body;
a read-only Python comparison verified both the exact predecessor and the
single-entry upgrade delta. Existing migration bytes are unchanged.

READY and PREPARE owner regressions create subsequent OPEN/BLOCKING Issues
through Application commands and verify committed STALE status and terminal
events. Five integrity/native SQLSTATE probes still raise and roll back. The
unchanged test_f9_terminal_grants_cannot_create_effect[stale-ready] passes.
The S2 G7/F1/F5/F9 tests from the interrupted slice are retained and verified.

AQ-S2-02 remains **BLOCKED: no owning Application command to schedule role
expiry**. Both question decisions and the subcase inventory are updated.
Credential/grant expiry coverage remains; Application role closure is revocation
evidence. Full PR2-19 and Phase 2 gates remain BLOCKED. Head expectations advance
to 0069 by value only. No dependency or new product-command changes.

Commands below use the repository uv environment and the configured
RB_TEST_ADMIN_URL for disposable real PostgreSQL databases. Raw passing output
is retained once per test group. Superseded, empty, stripped and duplicate logs
and the historical verbose G7 trace are removed.

```sh
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run pyright
git diff HEAD --check
```

Results: exit 0 each; all lint checks passed; **738 files already formatted**;
**0 errors, 0 warnings, 0 informations** from Pyright; clean diff whitespace.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture --tb=short
```

Result: exit 0, **5,645 passed, 53 warnings in 102.62s**.
Raw output: [unit-architecture.txt](unit-architecture.txt).
An earlier run in this continuation returned **1 failed, 5,644 passed, 53 warnings
in 85.26s**: the evidence-subject check observed mixed worktree digests while
tracked logs were updating. Active output was moved to ignored .uv-cache and the
complete command rerun with the tracked tree stable. No test or assertion was
changed to resolve that failure. The earlier failure is not counted as PASS.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b13_grant_lifecycle.py tests/integration/phase2/test_b13_grant_schema.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py --tb=short
```

Result: exit 0, **145 passed, 546 warnings in 336.85s**.
Raw output: [focused.txt](focused.txt). Includes maintenance events, integrity
propagation, exact PostgreSQL downgrade, the unchanged stale-ready oracle,
credential/grant expiry across observed waits, and the blocked subcase inventory.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py --tb=short
```

Result: exit 0, **81 passed, 264 warnings in 230.10s**.
Raw output: [s2-remaining.txt](s2-remaining.txt). Covers G7 READY/package closure,
F1 current downstream projections, F5 current blockers, and F9 release controls.

No skips or xfails were reported in these passing runs. Warnings are existing
Alembic path_separator deprecations and SQLAlchemy connection/isolation warnings.
The original focused verification above did not run the whole suite. The
reviewer follow-up below records the subsequently requested full-check attempt.
No commit, push or branch creation was performed.


## Reviewer follow-up — required check remains BLOCKED by sandbox

The rejected loop check is not PASS: its quick pre-check returned **1 failed,
481 passed, 1,414 warnings in 724.48s**, stopping at
`test_normal_sql_review_writer_overlaps_revision_without_lock_inversion[review_first]`.
The full suite did not run in that check. The only working-tree change to
`test_revision_action.py` is the migration-head expectation, 0068 to 0069;
its concurrency test body is unchanged.

Repeated reproduction command, run three times per subject:

```sh
uv run pytest tests/integration/phase2/test_revision_action.py -k lock_inversion --tb=short
```

HEAD was exported with `git archive HEAD` into ignored `.uv-cache/reviewer-head`
without creating a branch or changing the working tree. Its subject is
`312ae55734a25ffaef705f152cc926032022bc1e`. HEAD runs use that directory as cwd,
`PYTHONPATH=src`, and `UV_CACHE_DIR=../head-uv-cache`; working-tree runs use the
repository cwd and `UV_CACHE_DIR=.uv-cache`.

| Subject/run | Exact pytest result | Exit |
| --- | --- | --- |
| HEAD 1 | 2 passed, 51 deselected, 6 warnings in 2.32s | 0 |
| HEAD 2 | 2 passed, 51 deselected, 6 warnings in 2.73s | 0 |
| HEAD 3 | 2 passed, 51 deselected, 6 warnings in 2.20s | 0 |
| Working tree 1 | 2 passed, 51 deselected, 6 warnings in 2.64s | 0 |
| Working tree 2 | 2 passed, 51 deselected, 6 warnings in 2.23s | 0 |
| Working tree 3 | 2 passed, 51 deselected, 6 warnings in 2.33s | 0 |

Complete output: [reviewer-focused.txt](reviewer-focused.txt). The original
failure was **not reproduced**; these passing HEAD runs do not prove that it is
a pre-existing flake, and no such claim is made. No lock-ordering implementation
or concurrency assertion was changed.

The migration now asserts that replacement changes the predecessor SQL and
that the resulting SQL includes `SQLSTATE 'P14B1'`. New owner tests prove both
CORRECTED and RETRACTED sources produce **P16T1 at b13_release_gate**, followed by
explicit maintenance persisting STALE/GRANT_STALE and one terminal event. The
integrity test now covers READY via b14a_admission and PREPARE via
b12_approval_gate, the actual PREPARE maintenance path (not b17_admission).

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b14_publication_ready.py -k 'integrity_errors or source_validity' --tb=short
```

Result: exit 0, **12 passed, 28 deselected, 48 warnings in 18.91s**. Full output
is included in reviewer-focused.txt. The subsequent quick pre-check also runs
all these cases after the import-order correction.

Requested full check, with only the uv cache environment redirected into the
writable repository:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Static results: **0 errors, 0 warnings, 0 informations**; **738 files already
formatted**; **All checks passed!**; clean diff whitespace. The 30-file quick
pre-check then passed: **596 passed, 1,457 warnings in 873.55s**. This includes
the previously failing lock-inversion case. Complete pre-check output:
[reviewer-quick.txt](reviewer-quick.txt).

**The six-shard full suite did not start.** The script's fixed shared scheduler
directory, `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs`, is
outside this session's writable roots. It repeatedly failed to create/remove
`full_suite.lock` / `full_suite.lock2` with **Operation not permitted**. The
blocked scheduler was interrupted through its tool session (exit **130**).
Complete command output: [reviewer-check.txt](reviewer-check.txt). No harness
script, shared lock, scheduler rule or governing file was changed to bypass it.
The required command is **not green**; full-suite verification remains pending
an execution environment that can use the shared scheduler directory.

Earlier attempts in this follow-up also stopped before tests: default uv cache
access was denied (exit 2), then Ruff caught one missing import-group separator
(exit 1). The cache was redirected and Ruff fixed the separator before the
recorded successful static checks and 596-test pre-check. Neither attempt is
counted as passing.
