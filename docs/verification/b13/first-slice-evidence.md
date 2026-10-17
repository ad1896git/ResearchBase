# B13 first-slice implementation evidence — 2026-10-17

Owner authorization is recorded in the proposal status and its implementation
substitution register. This evidence covers B13's concrete scientific release,
immutable receipt/history, explicit one-grant maintenance and entitled historical
reads. READY/package effects, consent, transport and external submission remain
unavailable pending B14. This is not B14 or Phase 2 acceptance.

## Implementation

- One forward migration, `0059_b13_grant_consumption`, follows the reconciled
  `0058_b12_prepare_submission` head. Existing migrations were not edited.
- The owning ScientificConclusionService records a local release through private
  in-UoW approval orchestration. Receipt, grant state and terminal event commit
  together. Receipt storage reuses the sealed request-review relation, with no
  duplicate review-membership owner.
- Consumption is SERIALIZABLE; maintenance is READ COMMITTED. Every writer first
  takes the literal N SHARE inventory, Publication SHARE ROW EXCLUSIVE and A
  SHARE inventory before queries/advisories/local settings. Timeouts are configured
  on the driver before BEGIN. Reads and replay are REPEATABLE READ, READ ONLY,
  with no explicit table, advisory or row locks.
- Database guards validate concrete result/hash/review/authority/terminal graphs,
  stamp observed times, prohibit mutable receipts and terminal rewrites, and
  refuse destructive populated downgrades. Explicit maintenance rechecks OWNER
  and cause/expiry precedence at final constraint evaluation. Automatic existing
  authority-loss/new-target/rejection STALE events retain their attribution.
- Saved replay verifies immutable history independently of today's admission
  gates and rechecks the current reader. Only original-actor replay may reuse a
  key; audit read is separate. Only SQLSTATE 40001/40P01 retry, in at most three
  fresh UoWs; timeouts, business conflicts and uncertain commits do not retry.

## Focused verification

All commands ran at the repository root with
`UV_CACHE_DIR=/tmp/rb-b13-uv` (the default user cache is not writable in this
sandbox). PostgreSQL reported `18.6 (Homebrew)` through `SHOW server_version`.

| Exact command after the cache prefix | Result |
| --- | --- |
| `uv run pytest tests/unit tests/architecture --tb=short` | 5,000 passed, 42 warnings in 58.28s |
| `uv run pytest tests/integration/phase2/test_b13_grant_schema.py tests/integration/phase2/test_b13_grant_consumption.py tests/integration/phase2/test_b13_grant_lifecycle.py tests/integration/phase2/test_b13_grant_replay.py tests/integration/phase2/test_b13_grant_concurrency.py --tb=short` | 77 passed, 234 warnings in 93.71s |
| `uv run pytest tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b12_prepare_schema.py -x --tb=short` | 26 passed, 92 warnings in 30.24s |
| `git diff --check` | Passed, no whitespace errors |

New coverage includes independent frozen R3 hash vectors and error mappings;
strict inputs, expiry equality and issuer/dependency precedence; atomic rollback
injection; normal-role SQL incomplete graphs; populated/empty migration handling;
corrupted receipt/decision/review/event history; historical replay after blockers,
write-role loss and uncertain commit; same-key/two-key races; both maintenance
commit orders; exact SQLSTATE retry classification with distinct sessions; fixed
inventory/isolation capture and lock-free replay; and real backend/PID/blocking
witnesses crossing grant expiry at inventory/scope/target/grant/actor-FK waits.

Read-only sub-agent source reviews checked the governing guide against the diff.
Their identified P1s (observed timestamps, final maintenance authorization,
complete replay events and issuer-loss precedence) were fixed and re-reviewed;
no remaining concrete P0/P1 was reported in those reviewed scopes. Test evidence
is the executed commands above, not the reviewers' source-only conclusions.

The requested full sharded check and dependent regression run are recorded below
when they finish. Earlier failed attempts are not counted as passing evidence.

## Dependent regression observation and rerun

The following focused dependent run completed with **288 passed, 1 failed,
1 skipped, 937 warnings in 413.95s**. It is not reported as PASS:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv uv run pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_b11_readiness_decision.py tests/integration/phase2/test_b12_prepare_schema.py --tb=short
```

The failing existing test was
`test_decision_first_real_writer_wait_preserves_original_basis[issue]`: its
lock observer asserted `active` but saw `idle in transaction` while joining
PostgreSQL statistics and live lock information. Its isolated rerun passed
(1 passed, 3 warnings in 1.23s), and its entire owning suite then passed without
implementation or test changes:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv uv run pytest tests/integration/phase2/test_pr2_15_decision.py --tb=short
```

Result: **36 passed, 108 warnings in 43.68s**. The observer was subsequently repaired to keep polling until the same sampled
row has state `active`, instead of failing when statistics briefly report an
idle state alongside a live lock wait. Its backend/PID/blocking assertions and
bounded deadline remain intact. The final full sharded check is separate below.

## Final migration inventory and lock-observer regressions

The first sharded attempt was stopped after it exposed B07's current-head table
inventory omitting `approval_grant_consumptions`. Appending that registered table
preserves the test's exact inventory assertion. The complete B07 schema suite
then passed:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv uv run pytest tests/integration/phase2/test_b07_schema.py --tb=short
```

Result: **19 passed, 62 warnings in 18.80s**.

After the lock-observer correction, both affected owning suites passed:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv uv run pytest tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_15_decision.py --tb=short
```

Result: **45 passed, 137 warnings in 47.02s**.

## Final authority-wait regression

A subsequent source review found late issuer/caller expiry mapping errors. The
late database and Application gates now distinguish caller loss (`FORBIDDEN`),
issuer loss (`GRANT_STALE`) and grant expiry (`GRANT_INVALID`), with expiry
precedence. Three real actor-FK wait cases verify these outcomes and that denial
leaves no receipt or hidden maintenance event. Their focused command was:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv uv run pytest tests/integration/phase2/test_b13_grant_concurrency.py::test_authority_expiry_during_late_fk_wait_denies_without_hidden_maintenance -x --tb=short
```

Result: **3 passed, 9 warnings in 8.64s**. Both read-only reviewers rechecked
these mappings and reported no remaining P0/P1 in that narrow scope. The final
unit/architecture and all five B13 PostgreSQL suites were rerun after these fixes;
the final counts appear in the focused-verification table above.

The final focused static checks were `uv run pyright` (**0 errors, 0 warnings,
0 informations**), `uv run ruff format --check .` (**626 files already
formatted**) and `uv run ruff check .` (**All checks passed!**).

Earlier sharded attempts were interrupted to correct the inventory and late
mapping findings. None is reported as a passing full-suite run. The exact
requested check is rerun below, retaining its actual exit status.


## Exact requested check — final result

The following exact check chain ran with only the writable uv cache prefix:

```sh
UV_CACHE_DIR=/tmp/rb-b13-uv sh -c 'uv run pyright && uv run ruff format --check . && uv run ruff check . && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6'
```

**Actual command exit status: 0.** Static results: pyright **0 errors, 0 warnings,
0 informations**; Ruff format **626 files already formatted**; Ruff check
**All checks passed!** Pyright also printed an available-version notice.

| Shard | Final pytest summary |
| --- | --- |
| 0 | 630 passed, 630 warnings in 1725.22s (0:28:45) |
| 1 | 929 passed, 776 warnings in 1135.95s (0:18:55) |
| 2 | 1,345 passed, 1,042 warnings in 1143.40s (0:19:03) |
| 3 | 1,707 passed, 48 skipped, 1,059 warnings in 1155.81s (0:19:15) |
| 4 | 3,787 passed, 2 skipped, 1,600 warnings in 1060.97s (0:17:40) |
| 5 | 951 passed, 982 warnings in 1130.17s (0:18:50) |

The script's combined summary was **9,349 passed, 6,089 warnings, 50 skipped**.
There were no failed tests or setup errors. After reporting these results, the
script's optional duration-cache update raised `PermissionError` for
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/test_durations.json`,
which is outside this repository and the writable sandbox. The script still
returned its test-derived status **0**. No external file or runner script was
modified to bypass that restriction.

Only this evidence documentation was updated after the passing check; no source,
migration or test changes followed it. Final `git diff --check` passed.
