# B22 first-slice implementation evidence

Owner authorization: 2026-10-18. The proposal's status line is updated as requested;
ADR-0017 is the accepted field/hash amendment. This is bounded implementation
verification, not a Phase exit or whole-suite acceptance claim.

## Scope and compatibility

- Added one forward revision, `0065_b22_prior_art_correction`, after the observed
  head `0064_b14_publication_ready`. No historical migration was edited. No new
  table, dependency, mutable current pointer or downstream scientific/governance
  behavior was added.
- Prior-art roots retain byte-identical v1 material. Corrections use ADR-0017 v2,
  exact same-pair predecessors and independently admitted new evidence. Historical
  ancestry is verified iteratively, oldest first, without readmitting old evidence.
- Writes retain the unchanged N inventory and READ COMMITTED first-statement SHARE
  protocol, request advisory lock and Claim coordination before predecessor locks.
  Exact reads and selection use one lock-free, read-only REPEATABLE READ snapshot.
  Other consumers' transaction protocols, including SERIALIZABLE consumption, are
  unchanged.
- Selection returns EMPTY/UNIQUE/AMBIGUOUS with all independent chain terminals,
  including unusable terminals; it never falls back or arbitrates among roots.
  The 10,000-record bound fails explicitly, without partial results.
- Migration preflight pins the accepted shared `pr218_*` definitions, including
  0057's sealing correction. B22 adds only its own guards and columns; downgrade
  preserves v1 records and refuses populated correction history.

## Existing equivalents and inventory changes

No semantic or module-path substitution was needed. The new revision number was
resolved from the actual head. Existing CLI `--material-json` remains available;
`--supersedes-prior-art-relation-id` supplements it and rejects contradictory
JSON/flag values. Existing response generation, verified principals, error
mappings and service composition were reused. Route inventories have one appended
selection entry; migration inventories/head assertions have only appended entries
or updated expected values. Frozen architecture and sibling migration files were
not changed.

## Verification

Server: **PostgreSQL 18.6 (Homebrew)**. Integration fixtures use disposable real
PostgreSQL databases and normal SQL roles. Concurrency cases use independent
backends, observed blocking and database-clock expiry. Race coverage is provided by
these `tests/integration/phase2/test_b22_prior_art_concurrency.py` node IDs (all
parametrizations): `::test_first_sql_lock_inventory_and_order`,
`::test_two_corrections_one_winner_with_observed_claim_wait`,
`::test_read_snapshot_unrelated_actor_and_concurrent_correction`,
`::test_database_clock_expiry_across_correction_waits` and
`::test_revocation_during_initial_share_wait`; and, for the shared B19 Claim lock,
`tests/integration/phase2/test_b19_close_prior_art_concurrency.py::test_b22_b19_both_claim_lock_orders`.
The initial authoring pass
ran focused checks only; the subsequent owner-requested full check and review
follow-up are recorded below.

All `uv` commands below used `UV_CACHE_DIR=/tmp/researchbase-uv-cache` because the
sandbox cannot write the default user cache. This does not change dependencies.

| Exact command | Observed result |
| --- | --- |
| `uv run alembic heads` | `0065_b22_prior_art_correction (head)` |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 708 files already formatted |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations |
| `git diff --check` | Exit 0, no output |
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py` | 5,509 passed, 49 warnings, no skips |
| `uv run pytest tests/unit/phase2/test_b22_*.py tests/architecture/test_b22_*.py` | 50 passed, no skips |
| `uv run pytest tests/integration/phase2/test_b22_*.py` | 51 passed, 56 warnings, no skips |
| `uv run pytest tests/integration/phase2/test_pr2_18_*.py` | 83 passed, 87 warnings, no skips |
| `uv run pytest tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py` | 11 passed, 11 warnings, no skips |
| `uv run pytest tests/unit/phase2/test_b22_*.py tests/architecture/test_b22_*.py tests/unit/test_pr15_http.py tests/unit/test_pr15r_route_contract.py` | 61 passed, no skips |

The warnings above are the existing Alembic `path_separator` deprecation. Pyright
also prints an available-version notice, which is not a diagnostic.

The inherited PostgreSQL suites whose migration-head expectations changed also
passed: **238 passed, 626 warnings, no skips**, with this exact command:

```sh
uv run pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py
```

That run's warnings include the existing Alembic deprecation and 16 existing
SQLAlchemy warnings from `internal_review_repository.py:124` about an already
established connection ignoring isolation options. No new B22 read/write path
uses that repository or changes its isolation behavior.

## Review and corrections

Read-only investigation/review was delegated; the primary agent was the only
writer. Review found one P1: missing shared-guard migration preflight. It was fixed
and covered by a test that changes a guard at the parent revision, requires failed
upgrade and verifies no schema/revision advancement. Re-review found no remaining
confirmed P0/P1/P2 findings.

Earlier exploratory runs exposed stale head/route inventory expectations, test
role-event setup errors, fixture discovery and test formatting issues. These were
corrected; only actual passing reruns are listed as passing above. No initial
failure, unrun check or assumption is counted as PASS.

## Reviewer follow-up

The reviewer's full check exited 1 with **10,619 passed, 53 skipped, 1 failed**:
`test_pr2_02_source_version_migration.py::test_source_version_authority_rechecks_after_confirmed_lock_wait[create]`.
That result is a failed check and supersedes any assumption of full-suite success.
The saved check output includes a FORBIDDEN log but no failure traceback; the test
intentionally expects FORBIDDEN after expiry, so that log alone does not establish
the failure's cause. No timing-flake or baseline-flake claim is made without a
reproduction.

The pre-change baseline is commit
`c2ab96f` (`Accept ADR-0017 novelty material v2 (owner-approved 2026-10-18)`).
It was extracted with `git archive HEAD` into an isolated temporary directory
inside this repository and used its own `uv sync --frozen` environment. No branch,
commit or shared working-tree replacement was made. The source-version test,
Application service and repository are byte-identical in baseline and candidate.
`tests/conftest.py`, `tests/integration/phase2/conftest.py` and
`tests/integration/phase2/pr2_18_fixtures.py` also have no changes against HEAD.
Both use the same PostgreSQL server and the exact focused pytest arguments.

### P2 confirmations

The complete files omitted from the reviewer's truncated diff are available as
[schema tests](../../../tests/integration/phase2/test_b22_prior_art_schema.py),
[selection tests](../../../tests/integration/phase2/test_b22_prior_art_selection.py),
[hash vectors](../../../tests/unit/phase2/test_b22_prior_art_hash_vectors.py),
[proposal](../../proposals/B22_PriorArt_Correction_Selection_Contract_DRAFT.md), and
[migration inventory](../../phase2/migration_inventory_phase2.md).

- The proposal's status value is exactly:
  `APPROVED by owner 2026-10-18 — first slice authorized for implementation`.
  The only surrounding markup is the existing bold `Status:` label.
- Naming/location equivalents and CLI handling are recorded in “Existing
  equivalents and inventory changes” above. No semantic substitution was needed.
- The two read authorizations are required by B22 **§7**, which specifies advancing
  trusted time at entry and exit, and **§12.2**, whose selection row explicitly says
  “after final clock/read authorization.” The final clock checks credential/role
  expiry against the same database snapshot; it does not refresh that snapshot.
- Existing B18
  `test_pr2_18_prior_art.py::test_unverified_and_wrong_exact_source_atomic` rejects
  a first-time root using unverified evidence, and `test_six_comparisons` admits
  independently HUMAN-VERIFIED first roots. Those tests do not isolate the
  otherwise-VERIFIED-but-not-independent case. Added
  `test_b22_prior_art_correction.py::test_first_root_requires_independent_verification`
  explicitly isolates that case and asserts closure denial with zero parent and
  child inserts. Replay and exact-history verification retain their separate policy.

### Reproduction results

Exact command in the candidate and isolated baseline working directories:

```sh
uv run pytest tests/integration/phase2/test_pr2_02_source_version_migration.py -k rechecks_after_confirmed_lock_wait -p no:randomly
```

| Tree | Run | Result |
| --- | --- | --- |
| Candidate | 1 | 4 passed, 8 deselected, 4 warnings (30.30s) |
| Candidate | 2 | 4 passed, 8 deselected, 4 warnings (26.45s) |
| Candidate | 3 | 4 passed, 8 deselected, 4 warnings (26.45s) |
| Baseline c2ab96f | 1 | 4 passed, 8 deselected, 4 warnings (25.66s) |
| Baseline c2ab96f | 2 | 4 passed, 8 deselected, 4 warnings (25.85s) |
| Baseline c2ab96f | 3 | 4 passed, 8 deselected, 4 warnings (25.29s) |

Both trees passed 12/12 selected cases over three runs. The original failure was
not reproduced; these results do **not** establish that the baseline is flaky.
Candidate runs used the previously documented cache path; baseline used a separate
`UV_CACHE_DIR=/tmp/researchbase-b22-baseline-uv-cache`. Both used frozen uv.lock
dependencies. The temporary baseline was removed before static/full checking.

Additional root-admission verification:

```sh
uv run pytest tests/integration/phase2/test_b22_prior_art_correction.py tests/integration/phase2/test_pr2_18_prior_art.py
```

Result: **23 passed, 23 warnings**, no skips (35.44s).

### Required full-check attempt: blocked by sandbox

The requested chain was invoked unchanged, with the documented UV cache override:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The four static commands passed: Pyright 0 errors/0 warnings/0 informations,
708 files formatted, Ruff passed, and `git diff --check HEAD` exited 0.
The sharded runner entered its 30-file quick pre-check. Its required shared lock
location `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs` is outside
the session's writable roots. A unique temporary-directory creation probe failed
with **PermissionError: Operation not permitted**. The runner also writes its
shared duration inventory outside this repository. The runner was not modified,
and sandbox restrictions were not bypassed.

The attempt was interrupted after confirming this restriction, rather than leave
its lock-acquisition loop waiting indefinitely. Interrupted pytest teardown emitted
a `tmp_path` stash KeyError, and the runner reported `quick pre-check failed; full
suite not run`. No completed test result or exit-0 full check is claimed for that
attempt. Its exact quick pre-check was then launched separately without alteration
to obtain an uninterrupted result.

The original full-suite P1 remains **OPEN / full rerun blocked by environment**.
It requires the exact check to run in an environment permitted to write the
runner's shared lock and duration paths. Candidate/baseline focused passes do not
replace that required full check. Raw focused outputs, identical-file digests,
the attempted runner output and exact quick-precheck command are retained in
[review-followup](review-followup/).

Uninterrupted runner quick-precheck result: **388 passed, 689 warnings, no skips**
in 437.79s, exit **0**. It used the runner's exact 30-file list and arguments,
recorded in [quick-precheck-command.txt](review-followup/quick-precheck-command.txt),
with [complete output](review-followup/quick-precheck.log).
This is the runner's quick pre-check only, not its full six-shard suite.

Final status: static checks and all six requested focused repetitions passed;
all P2 confirmations are documented and the independent-root admission case has
explicit regression coverage. **No exit-0 full check has been obtained.** The
full-suite P1 remains open due to the verified runner-path sandbox restriction.
