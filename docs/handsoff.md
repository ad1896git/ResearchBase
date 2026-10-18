# ResearchBase handoff notes

Written 2026-10-18 for whoever takes over Phase 2 development. It records the setup,
the working method, and the pitfalls we hit, so you don't hit them again.

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

Local environment: PostgreSQL 18 (Homebrew service `postgresql@18`), superuser
`researchbase/researchbase`, `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase`,
`RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres`.
Dependencies only through `uv` (`uv sync`, `uv run ...`). Since 2026-10-18 the server runs
with `max_locks_per_transaction=256` (set with `ALTER SYSTEM`, see pitfall 3.1).

## 2. How the work is run

- **Roles.** Codex CLI writes code, tests and evidence. Claude plans, reviews and accepts.
  The owner (eshine) approves contracts, schema changes, new features and pushes.
- **Per backlog item.** Codex drafts a contract → Claude reviews it twice (checking key
  technical claims against the real code) → owner approves → Codex implements →
  full check → Claude checks key code → merge onto the PR branch → push.
- **The loop.** `.pipeline/bin/codex_loop.py --repo <clone> --task <spec> --check "<cmd>" --commit`
  runs Codex, runs the check, gets a reviewer verdict and commits on PASS. Two Codex
  accounts (`~/.codex`, `~/.codex-b`) are tried in order when one hits its usage limit.
- **Round cap.** At most 2 Codex rounds per task. After that the director may take over
  once; if that fails too, stop and report. No endless retry loops.
- **Lanes.** Independent tasks run in parallel, each in its own clone
  (`.pipeline/work/laneNN`) and its own database (`researchbase_laneNN`), started with
  `bin/lane_run2.sh` (fresh clone) or `bin/lane_continue.sh` (reuse clone). Docs-only
  drafting uses `bin/queue_contracts.sh`.
- **Full check** = `pyright` + `ruff format --check` + `ruff check` + `git diff --check HEAD`
  + `bin/full_suite_sharded.sh 6` (about 9,750 tests in 6 shards, each with its own DB,
  about 30–37 minutes).
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

## 4. State on 2026-10-18

- On the PR branch and pushed: batches B–D, hardening, the B12/B13/B25/B27 work, the
  authorship read fix and approved drafts. Migration head on the branch: `0059`.
- Done in lanes, not yet merged: B14a (lane19), B15 (lane25), B18 (lane26), B26 (lane27),
  B29 measurement (lane28, no index built; the owner decides on DDL separately).
- In progress: B16 (lane25), B30 (lane26, director takeover rerun), B14r then B14 (lane19).
- Next: merge all lanes (renumber migrations, one head, full suite), push to PR #1. Then the
  rest of the backlog (B17, B19–B24, B28, B31, B32), and re-review the parked Phase 3
  drafts after Phase 2 is accepted.
