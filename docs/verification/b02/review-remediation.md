# B02 review remediation — 2026-10-19

**B07 defect fixed. Required full check remains BLOCKED by the execution sandbox;
no full-suite PASS or shard result is claimed.**

## P1: deterministic B07 regression reproduced and fixed

The exact requested reproduction was run with the local disposable PostgreSQL
opt-in and workspace UV cache:

```sh
export UV_CACHE_DIR="$PWD/tmp/uv-cache"
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
uv run pytest tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade -x
```

Before the fix: **exit 1; 1 failed, 3 warnings in 1.01s**.
[Complete traceback](review-b07-before.txt). The failure was:

```text
tests/integration/phase2/test_b07_schema.py:35: AssertionError
Extra items in the left set:
'strategy_candidate_captures'
'strategy_question_admissions'
'strategy_hypothesis_admissions'
'strategy_candidate_sources'
```

The upgrade itself succeeded. The assertion comparing the tables added between
0051 and head still expected the pre-B02 set. This is a deterministic expectation
regression, not evidence of a shard collision. The previous 304-case selection
omitted this test; that selection did not establish a full-suite pass.

The fix adds exactly those four approved relations to the expected set in
[test_b07_schema.py:46](../../../tests/integration/phase2/test_b07_schema.py#L46).
The strict table-set equality, FK checks, deferred-trigger checks, downgrade to
0051, exact restoration of the original table set, and re-upgrade remain enabled.
No migration or production code was changed for this review remediation.

After the fix, the same exact command returned **exit 0; 1 passed, 5 warnings in
1.54s**. [Output](review-b07-after.txt).

The entire affected module was then run:

```sh
uv run pytest tests/integration/phase2/test_b07_schema.py -q -o addopts=''
```

**Exit 0; 19 passed, 62 warnings in 22.74s**.
[Output](review-b07-suite.txt).

## P2: director-ruling deliverables and requested grep output

Exact commands:

```sh
grep -n "APPROVED by owner\|Agent writers" docs/proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md
grep -rn "AGENT" tests/integration/phase2/test_b02_identity_boundary.py
```

Exact output ([retained copy](review-ruling-grep.txt)):

```text
3:**Status: APPROVED by owner 2026-10-19 — first slice authorized for implementation**
207:extraction from a sealed turn. B02 allows verified Human/Agent writers and an
569:Agent writers are deferred until an owning Agent identity/provisioning contract exists
575:Agent writers are deferred until an owning Agent identity/provisioning contract
tests/integration/phase2/test_b02_identity_boundary.py:16:@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
tests/integration/phase2/test_b02_identity_boundary.py:60:            if actor_type == "AGENT":
```

Concrete locations:

- Contract status: `docs/proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md:3`.
- §12.4 Agent deferral: same file, line 569; §12.5 deferral: line 575.
- Application denial: `tests/integration/phase2/test_b02_strategy_admission.py:137`,
  parametrized for HUMAN/AGENT at line 136. Line 160 asserts existing
  `ErrorCode.FORBIDDEN` for reads and both admissions; lines 161–163 assert no
  admission rows. The identity-boundary test above independently preserves the
  HUMAN-only binding-trigger evidence.
- Resolution: `docs/verification/b02/implementation-blocker.md:3` says
  **RESOLVED by director ruling**. The original contract chain, trigger evidence
  and reproduction results remain below the ruling.

## P2: normalization mappings and reused-UoW isolation

New tests: `tests/unit/phase2/test_b02_strategy_promotion_uow.py`.

- Line 45: P22B1, P22B2, named 23505 candidate/PK constraints, 40001, 40P01,
  timeout and FK mappings at commit, execute and cleanup boundaries. Tests assert
  exact error codes, retry/replay metadata, rollback, close and sanitized errors.
- Line 81: reuse the same UoW object across two entered contexts with distinct
  Sessions. All B02/B01/manuscript flags must be clear before the second command.
  Twelve previous/next-flow combinations assert the actual 40001 classification
  and its flow-specific metadata, including ordinary commands with no B02 metadata.
- Line 110: unrelated/missing unique-constraint metadata cannot become a candidate
  duplicate or request-replay race.

`SqlAlchemyUnitOfWork.__enter__` resets B02/B01/manuscript flags at
`src/researchbase/persistence/uow.py:518`–521. Every command uses a fresh entered
transaction. Switching command modes inside one already-entered transaction is
outside the one-command/one-UoW contract; no new mode-switching behavior is added.
The existing reset is sufficient for supported reuse, so production normalization
and its branch ordering remain unchanged.

```sh
uv run pytest tests/unit/phase2/test_b02_strategy_promotion_uow.py -q -o addopts=''
```

**Exit 0; 50 passed in 0.44s**. [Output](review-uow-errors.txt).

## Required full-check attempt and remaining environment blocker

With the exports above and inherited `DATABASE_URL` selecting the local
`researchbase_lane56` test database, this exact chain was executed:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

[Retained output](review-full-check.txt):

- Pyright: **0 errors, 0 warnings, 0 informations**.
- Ruff format: **751 files already formatted**.
- Ruff lint: **All checks passed!**
- `git diff --check HEAD`: exit 0. One trailing blank line in the previously
  retained Pyright log was removed; substantive prior evidence was preserved.
- Runner's 33-file changed-test pre-check: **491 passed, 980 warnings in 483.76s**.
- Then the runner could not acquire its shared filesystem mutex. It reported:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

The sandbox permits repository and temporary-file writes, but not the runner's
external `.pipeline/logs` directory or `.pipeline/test_durations.json` manifest.
Both paths also returned false from `os.access(path, os.W_OK)`. The runner's stale
mutex retry loop was interrupted with Ctrl-C; the exec session reported exit 1.
**No shard started, no full-suite aggregate exists for this attempt, and the
required chain is not PASS.** This is separate from the reproduced B07 assertion.
No harness/mutex bypass or harness modification was attempted.

A clean six-shard rerun still requires an execution environment that can write the
runner's configured shared mutex directory and duration manifest. No commit, push
or branch creation occurred. A final `git diff --check HEAD` after the report
returned exit 0.
