# ResearchBase handoff notes

Written 2026-10-18; refreshed 2026-10-20 from `.pipeline/RULES.md` for Phase 2 development.
It records the setup, the working method, and the pitfalls we hit, so you don't hit them again.

## 1. Where things are

| What | Where |
| --- | --- |
| Repository | https://github.com/ad1896git/ResearchBase, local clone `/Users/fengwang/Documents/ResearchBaseProject` |
| Working branch / PR | `codex/pr2-15-stabilization`, PR #1 against `main` |
| Binding rules | `AGENTS.md` (read order, phase discipline, DO NOT ADD SCHEMA, layering, verification) |
| Frozen design | `docs/architecture/` (never edit to make code pass) |
| Contracts per backlog item | `docs/proposals/Bxx_*_DRAFT.md` (status line says whether the owner approved it) |
| Phase 2 backlog B01–B32 | `PHASE3_Roadmap_DRAFT.md` (parked draft, in `.pipeline/work/lane3/docs/proposals/`) |
| Evidence | `docs/phase2/`, `pr_evidence/` |
| Automation (not in git) | `.pipeline/` (excluded via `.git/info/exclude`): `bin/` scripts, `tasks/` task specs, `logs/`, `runs/`, `work/<lane>` clones, `RULES.md` |

Local environment: PostgreSQL 18 (Homebrew service `postgresql@18`). Set
`DATABASE_URL` and `RB_TEST_ADMIN_URL` locally; keep credentials out of handoff notes.
Dependencies only through `uv` (`uv sync`, `uv run ...`). Since 2026-10-18 the server runs
with `max_locks_per_transaction=256` (set with `ALTER SYSTEM`, see pitfall 3.1).

## 2. How the work is run

- **Roles.** Codex CLI writes code, tests and evidence. Claude plans, reviews and accepts.
  The owner approves contracts, schema changes and new features. Claude personally
  performs independent reviews, including the Phase 2 exit review. The owner now
  authorizes push and Phase 2 acceptance after director PASS, with no open P0/P1,
  failing full check or unsupported PASS row.
- **Per backlog item.** Codex drafts a contract → Claude reviews it twice (checking key
  technical claims against the real code) → owner approves → Codex implements →
  full check → Claude checks key code → merge onto the PR branch → push.
- **The loop.** `.pipeline/bin/codex_loop.py --repo <clone> --task <spec> --check "<cmd>" --commit`
  runs Codex, runs the check, gets a reviewer verdict and commits on PASS. Account B
  comes first, then A on quota exhaustion; reserve A before allowing fallback.
- **Accounts.** A: light work, one task at a time. B: heavy work, parallel tasks.
  C (agy): parallel mechanical work, light model first; escalate only after failure.
  Review C more strictly: verify every code reference and schema/lock claim, search
  backticked identifiers in the code, and read its full diff. A reviewer PASS once
  missed invented identifiers. Track B/C results in `logs/worker_scoreboard.md`.
- **Round cap.** At most 2 Codex rounds per task. After that the director may take over
  once; if that fails too, stop and report. No endless retry loops.
- **Lanes.** Independent tasks run in parallel, each in its own clone
  (`.pipeline/work/laneNN`) and its own database (`researchbase_laneNN`), started with
  `bin/lane_run3.sh` (fresh clone) or `bin/lane_continue.sh` (reuse clone). After the
  SIGKILL incident, the owner launched lanes by hand in herdr panes. Later on
  2026-10-20, she also allowed director launches in detached tmux sessions; current
  wrappers are `bin/lane_run4.sh` and `bin/agy_lane4.sh`. Docs-only drafting uses
  `bin/queue_contracts.sh`.
- **Full check** = `pyright` + `ruff format --check` + `ruff check` + `git diff --check HEAD`
  + `bin/full_suite_sharded.sh 6` (over 12,000 tests in 6 shards, each with its own DB).
  Codex runs focused checks; the loop runs the full check and supplies the evidence.
  A sandbox failure to take a suite lock does not mean the loop check failed.
- **Merging lanes.** Cherry-pick the first lane, `git apply --3way` the others, then a
  Codex merge task whose check also requires no conflict markers and exactly one
  Alembic head.

## 3. Pitfalls and what to do instead

### 3.1 Test infrastructure

1. **Parallel full suites exhausted the PostgreSQL lock table.** With the default
   `max_locks_per_transaction=64`, two sharded suites at once (12 processes, writers taking
   SHARE locks on 45+ tables) produced "out of shared memory" and random failures in
   unrelated tests. Fix: the limit is now 256, and `full_suite_sharded.sh` allows at most
   two suites at a time (slot directories `.pipeline/logs/full_suite.lock*`).
2. **The full suite took about 105 minutes single-process.** Sharding by measured per-file
   durations (`.pipeline/test_durations.json`, from junit XML) brought it to about 30 minutes.
3. **Fail fast before queueing.** `full_suite_sharded.sh` first runs only the test files
   the lane changed; if they fail, it skips the long queued run.
4. **Known flaky tests under load:** `test_pr2_04_ownership_races.py`,
   `test_pr2_04_process_completion.py`, and some temporal/expiry tests with fixed 5–8 s
   windows. A single failure there is not proof of a regression. Rerun the test alone on
   the change and on its parent commit before deciding.
5. **Tests must not write into the repository.** The PR2-20 evidence tests used to create
   `pr_evidence/pr2-20/<hash>/` on every run (now fixed to use `tmp_path`). Any new evidence
   test should write under `tmp_path`.
6. **`git diff --check` is part of the suite** (`test_pr2_04_static_acceptance.py`).
   Trailing whitespace in a committed evidence `.txt` file fails the whole gate. Strip it
   before committing.
7. **Head expectations.** Many migration tests and `.github/workflows/ci.yml` pin the
   current Alembic head. Every new migration must update those values (values only).
8. **Migration numbers collide across lanes** (for example, B14a and B15 both created
   `0060`). The merge step must renumber and re-chain so there is exactly one head.
9. **`pytest_plugins` must not name another test module.** Collection order can make
   shared fixtures disappear. B20/B22 were fixed through `tests/unit/phase2/conftest.py`;
   the wider cleanup is underway. Use shared fixture modules/conftest and check both
   collection orders.
10. **Don't ask Codex to re-run huge touched sets.** On 2026-10-20, t177 ran about 125
    integration modules twice alongside sharded checks for over 85 minutes. For wide
    mechanical changes, use a small sample plus `pytest --collect-only`; leave full
    coverage to the loop.

### 3.2 Database and locking design

1. **Reads never lock.** Read-only paths use one `REPEATABLE READ, READ ONLY` snapshot as
   the first SQL statement and no `LOCK TABLE`, advisory or `FOR SHARE/UPDATE` locks.
   Violations were found and fixed in B01, PR2-18 and the authorship reads (`_get` in
   `src/researchbase/application/authorship.py`).
2. **Writes** take `LOCK TABLE <inventory> IN SHARE MODE` as the FIRST statement in a
   READ COMMITTED unit of work. Nothing (no SELECT, no `SET LOCAL`) may come before it.
   Grant consumption (B13/B14) runs SERIALIZABLE; follow each contract's guide exactly.
3. **Publication coordination** uses `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`
   (B13). B16 moves `decide_approval` onto that prefix for all purposes; B14r follows
   whichever prefix the branch uses.
4. **XID wraparound.** Old code compared `xmin::text::bigint` with
   `pg_current_xact_id()::text::bigint`; that breaks after the first wraparound. Use
   `xmin = pg_current_xact_id()::xid` (migration 0057).
5. **Never edit an existing migration**; add a forward one. No `ON DELETE CASCADE` on
   scientific data. Populated downgrades must refuse rather than drop history.

### 3.3 Planning and contracts

1. **Missing prerequisites stop implementation.** B14 (Publication INTERNAL_REVIEW→READY)
   needed two things nobody had planned: the DRAFTING→INTERNAL_REVIEW entry (B14a) and a
   way to issue the READY_FOR_SUBMISSION approval (B14r). Codex was right to stop both
   times. Before approving a contract, trace every state and grant it consumes back to an
   existing command.
2. **Codex's claims must be checked.** Drafts sometimes cite functions or say "no
   migration" while their DDL section adds one. Verify key claims against the code.
3. **Contracts must agree with each other.** B14r first pinned a lock prefix that the
   approved B16 contract changes; this was caught only by reading both together.
4. **Task-template wording can contradict a contract.** The implementation template said
   "writes in READ COMMITTED", which conflicted with B14's SERIALIZABLE consumption.
   The template now says "follow the guide exactly".

### 3.4 Pipeline mechanics

1. **Don't edit a shell script in place while lanes run it.** `sh` reads scripts by
   offset; rewriting the same file (Python `open('w')`, many editors) corrupts running
   copies. Write a new file and `mv` it over. macOS `sed -i` is safe.
2. **`pgrep -f pytest` also matches the loop** (its `--check` contains "pytest"). Match by
   working directory instead. Never wait on `pgrep -f <pattern>` when the waiting script's
   own command line contains that pattern (it waits forever on itself).
3. **Environment variables:** `VAR=x cmd1 && cmd2` only reaches `cmd1`. Export them in
   the script.
4. **Reviewer hangs:** `claude -p` reviews can stall; the loop uses a 15-minute timeout
   with retries and puts code first in the diff it sends (evidence files are large).
5. **Claude's background waiters die when its session is recycled.** The watchdog only
   detects stuck Codex runs, not a sleeping director. The director now re-checks with
   `bin/status.sh` every 20 minutes using a session cron; recreate it in a new session.
6. **Fast mode** for Codex roughly doubled quota use for little speed gain; it is off by default.
7. **Keep the Mac awake** for long runs (`caffeinate -ims -w <pid>`).
8. **2026-10-20 SIGKILL incident.** Two lanes hung at Codex startup with empty output
   and no session, then both exited -9 in the same second. The kill source was not
   proven; quota, watchdog and task content were not supported causes. A foreground
   probe and the owner's herdr relaunch worked. Use the approved pane/tmux launch path,
   inspect startup evidence, and confirm the old process tree is dead before relaunch.
9. **Kill exact PIDs.** `pkill -f` with a test filename also kills other lanes' shards.
10. **`status.sh` suites count was fixed.** It counted `codex_loop` because its `--check`
    argument ended in `full_suite_sharded.sh 6`; that was not a running suite.

## 4. State on 2026-10-20

- Batch I, M1-S1/S2 and B31-S1/S2/S3 are merged and pushed to PR #1. Migration head:
  `0075` (`0075_m1_reconsideration`). The integrated check passed: 12,461 passed,
  66 skipped.
- B31-S4 exit work is in progress: its first loop check passed (12,469 passed,
  66 skipped); follow-ups must commit cited evidence and record owner-accepted gaps
  without turning them into PASS. The repo-wide fixture cleanup is also underway.
- Known gaps: B28 real PaperQA2, positive G2 AGENT admission (AQ-S3-08), and the
  owner-deferred Linux benchmark host. Local macOS timings remain informational.
- Next: finish follow-ups, then the director's independent Phase 2 exit review.
  After clean gates, push, accept Phase 2 and merge PR #1 under the owner's standing
  authorization. Revisit parked Phase 3 drafts after Phase 2 acceptance.
