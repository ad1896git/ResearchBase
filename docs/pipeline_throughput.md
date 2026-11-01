# Opt-in throughput scheduler

`pipeline_wakeup` accepts an optional `throughput` object on a version-2
configuration. Existing configurations keep their existing behavior. This PR
prepares a candidate; installing it or changing a live queue is a separate action.
The scheduler changes engineering orchestration only, never scientific persistence.

A throughput policy contains absolute canonical `root`, `worktrees`, and
`source_checkout` paths; allowlisted `repository` and `base_ref`; frozen
`authorization` and `index` file specifications (`path`, `sha256`); fixed
`implementation_slots: 2`, `review_slots: 1`, `pg_slots: 1`; and `pg_environment`.
The policy's resource/path fields are immutable. Changes to owner evidence indices
create a parent-linked `policy-revisions` journal; active packets keep the original
revision and frozen inputs. Replaying a previous revision is rejected. An operator
updates the approved index reference, not a separate hand-written job per task.

The authorization document uses the existing version-1 BACKLOG task rows (`id`,
`authorized`, `risk`, `depends_on`, `goal`, `acceptance`). The index has exactly
`version`, `contracts`, `completed`, `templates`, and `publications` fields.
`contracts[ID]` contains a frozen `contract` file specification, a reusable template
key and frozen `gates`. A contract has `version: 1`, matching `backlog_id`,
`scope_kind` (`implementation` or `audit`), `frozen: true`, nonempty `allowed_paths`
and a frozen `specification` prose file. A gate has matching `backlog_id` and
`contract_sha256`, `version: 1` and `decision: PASS`. Reusable templates contain
`version`, bounded `implementation_prompt`, bounded `review_prompt` and `pg_argv`.
No LLM output is an authorization source. Architecture/governance/dependency files
remain denied even if a contract uses a broad path glob. Deletion is denied.

Dependencies require a frozen host/owner completion receipt with matching ID,
`version: 1`, `status: done`, `coverage: whole_backlog` and nonempty frozen `evidence`.
A progress string or a single sub-PR merge cannot complete an entire BACKLOG parent.
A later index can supply completion evidence, but unresolved local children block
its consumption. Owner-only M01/D01/F01/R02 and missing frozen contracts remain held.
An admitted-packet journal and prepared-registry bindings detect forgotten state,
removal and replacement instead of silently recreating work. Admission reasons,
actual dispatch statuses and held notifications are retained.

## Execution and recovery

Each stage has a separate worktree, control ledger and immutable generated prompt.
Implementation receives a host capability bounded to the original task, evidence
index, contract, template, checkout, head and prompt. Review has a distinct checkout
at the host candidate and runs with `writable=False`; its answer is saved by the
host outside that checkout. Review cannot inherit the author's writable scratch.
The fixed interpreter receives `PYTHONPATH=checkout/src:checkout`, so a shared
editable installation cannot silently test another checkout. Workers must not
install dependencies or create a local virtualenv; the original full archive
budget (64 MiB, 10,000 files) remains enforced, including attempt scratch.

Models leave HEAD unchanged. After a successful model receipt, the host validates
staged, unstaged and untracked source paths, rejects deletions/symlinks/hardlinks and
out-of-scope changes, then journals a distinct local candidate commit. Original
model answer and receipt keep their actual original commit. A durable request
precedes the host commit; uncertain pre-effect outcomes block, and post-commit
recovery reconciles the exact parent/tree/intent without another commit. Review
and PG consume that exact host head. No main push/PR publishing permission is added.
The final generated stage is `awaiting_publication`, an explicit E03 dependency.

The short global wakeup lease protects inventory/admission only. Kernel driver
and resource leases transfer to bounded child executors: two implementation/design,
one independent review, one heavy PG. CI GETs, model lifetime and PG processes do
not hold the global lease. Existing merges use the existing adapter under global,
merge and driver leases, reload configuration and recheck fresh head/base/approval.
An unknown child outcome or unjoined descendants durably quarantine dispatch before
resource release. Restart audits honor quarantine even for already blocked tasks;
a free kernel lock alone is not proof of child termination. No automatic retry of
an uncertain local commit, model launch or PG command occurs.

## Persistent CI probes

Already published allowlisted PRs can be observed read-only through
`PublishedCITarget`; this grants no remote write. Each finite timer probe releases
its leases. Pending CI persists the same intent, attempt and round, raw observation
hash, UTC start/deadline and last-probe heartbeat. Default total window is 9,000s,
with at most three windows and a durable timeout notice/retry receipt. Restart does
not reset the clock. Immutable task/target windows precede begin/resume, and separate
claims bind their bytes to the intent. Missing established timing blocks; pause
receipts retain their original retry date. The last-window cap is enforced before
every resume, including interrupted pause/block/resume saves. Query
timeout/429/5xx preserves the pending intent and fixed
deadline; unknown errors block. Terminal success needs two fresh observations;
exact head/base, actual base reference and the seven GitHub Actions checks remain
mandatory. Remote CI queueing is backpressure, not a reason to weaken checks.

## PostgreSQL boundary

Only a host stage may invoke a frozen argv beginning with the exact runtime Python,
`-m pytest` and explicit `tests/*.py` files; shell/options/unknown commands are denied.
Missing profile is a visible held state. The profile must provide
`RB_TEST_ADMIN_URL` (local TCP PostgreSQL18 admin database) and all four pins:
`RB_TEST_ADMIN_USER`, `RB_TEST_ADMIN_PORT`, `RB_TEST_ADMIN_DATA_DIRECTORY`,
`RB_TEST_ADMIN_SYSTEM_ID`. The host verifies actual server identity before creating
and eventually dropping its own random disposable database. Existing project
DBs are never migration/test targets. The unique PG lease surrounds this stage.
Raw output and JUnit are hashed in the receipt; exit zero alone is insufficient:
selected cases must exist with zero skips/failures/errors. XML and output budgets
are bounded, and tracked source changes are rejected.

This is cooperative resource scheduling for trusted task code, not a sandbox against
a malicious worker. Model network denial does not block every local Unix socket;
source tests themselves are executable code. No hostile DB isolation guarantee is
claimed. Main capabilities allow local scoped edits only; publication, labels,
settings, deployment and scientific authority do not follow from a model answer.
