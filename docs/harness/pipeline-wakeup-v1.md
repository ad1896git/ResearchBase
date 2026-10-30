# Scheduled engineering wakeup — manual merge policy

This HC-2 engineering-only change provides the single launchd entry
`com.researchbase.pipeline-wakeup`, `StartInterval=300`, `RunAtLoad=true`.
It does not change scientific schemas, Application commands, dependencies or
production data. Rendering a plist does not install or load it. This PR does not
activate the timer, change either old service, or execute a queued task.

## Entry, admission and manual merge

Each wake reloads an operator-owned explicit registry of **prepared generations**.
A generation must already contain an initialized protocol ledger, frozen worker/CI
jobs and their SHA256, and an explicit checkout and evidence directory. This is
not a parser or importer for legacy `.pipeline/queue.json`, BACKLOG, arbitrary
shell commands, historical passed tasks or owner-deferred work. Current worker/CI
sandbox restrictions remain in force; registering a main-repository worker does
not bypass those restrictions. Preparing a new production task remains a separate
admission operation.

The registry is append-only: admitted IDs, paths, repository and jobs hash cannot
be removed or retargeted. A fresh task with different jobs requires a fresh
explicit generation. The runtime checkout must be clean and match the configured
full `source_head`; use the reviewed **merged tree commit**, not the pre-squash PR
commit. A mismatch stops with a blocked notification, not a fallback checkout.

Before running any generation, scan **all** generations for awaiting-merge PRs.
The observer uses GET-only `gh pr view` and paginated issue-event/check-run APIs,
repeats the observation, and requires it to remain identical. Readiness requires
an open non-draft same-repository PR, exact frozen head/base, a currently effective
`approved-merge` label application newer than the gate's baseline and made by an
explicit configured approver, durable publication/verification/review proofs,
and all seven unique GitHub Actions checks (`static`, `checks (0)`–`checks (5)`)
completed successfully on that head. Missing, duplicated, foreign-producer,
incomplete or changing evidence cannot produce `manual_merge_ready`. Removing or
unauthorized reapplying approval invalidates old approval; head/base drift blocks
the task. Local protocol approval records may change; remote labels/settings do not.

**All risk levels remain `awaiting_merge`; the operator manually merges.**
`manual_merge_ready` is a notification, not a merge executor. An already-merged or
closed PR triggers `manual_reconciliation`, without inventing a successful task
receipt or unblocking its dependents. Automatic squash, authorized actor checks
at execution time, and crash-safe merge reconciliation belong to BACKLOG M00.

Notifications are durable, content-addressed JSON files under the configured
root's `notifications/`; only new content is printed to stderr (launchd's error
log). This is local notification delivery, not email or a background chat service.
An empty queue produces no model session. Blocked/budget-exhausted generations
notify instead of restarting work. Registry/config validation failures exit 2
with a structured blocked message in stderr.

## Lock and recovery compatibility

A stable-inode nonblocking `wakeup.lock` serializes the entire scheduled wake,
including a long CI wait; another invocation returns `busy`. Every generation
also uses its existing `driver.lock`, and the ledger's short `control.lock` still
protects state transactions. No PID-based lock authority or lock-file deletion is
introduced. The read-only merge scan acquires the driver lock before the state
lock and releases it before `run_cycle` acquires ownership. A concurrently owned
generation is skipped; it is never relaunched. If another driver wins the gap
between scan and cycle admission, the dedicated `LockBusy` outcome marks only
that entry busy and the wake continues to later entries. Other safety errors
(including a changed lock inode) propagate as blocked failures, never as busy. launchd coalesces scheduled starts
while its job is running, so 300 seconds is the wake interval when idle, not a
promise of parallel invocations during a long cycle.

CI `running`/`retry_wait` resumes its same durable intent and retry markers, using
the existing deadline and heartbeat, without consuming another model round.
A completed worker interrupted before ledger commit can reconcile its saved
result or joined host receipt through `worker_once`; an unknown live outcome or
unjoined worker blocks and is never relaunched. No separate watchdog is needed.

Default `run_cycle` retains its strict terminal-only normal-exit invariant. The
scheduler explicitly binds `park_human_gates=true` in `driver-binding.json`:
only actual awaiting-merge tasks and ready dependency chains ending exclusively
at those gates may park, with a durable `parked` event and notification. No ready
independent task, running child, retry wait, failed/blocked task or budget stop can
be hidden by parking. The next wake rescans approvals. Existing bindings without
this mode cannot be silently reused or edited: prepare a new explicit generation;
binding drift fails closed. Parking does not mark work done or reset attempts.

## Configuration and deployment preparation

Example config (all paths absolute, canonical, operator-owned, outside workers):

```json
{
  "version": 1,
  "root": "/absolute/control/timer",
  "queue": "/absolute/control/timer-queue.json",
  "runtime": "/absolute/pinned-runtime",
  "python": "/absolute/pinned-runtime/.venv/bin/python3",
  "source_head": "FULL_REVIEWED_MERGED_COMMIT_SHA",
  "approvers": ["ad1896git"],
  "codex_home": "/Users/fengwang/.codex-b",
  "executable_dirs": ["/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
}
```

`python` preserves its venv executable symlink spelling so its sys.prefix remains
correct; the executable must exist and be executable, with a canonical parent. The repository environment and dependencies must already have
been prepared with the pinned uv lock. The plist sets PYTHONPATH, explicit
CODEX_HOME and the explicit macOS/Homebrew PATH; startup verifies gh/git/codex can actually
be resolved in that PATH; credentials are not embedded.
The configured root must exist before launchd opens its log files.

Initial queue can be `{"version":1,"entries":[]}`. Each appended entry has:

```json
{
  "id": "explicit-new-generation",
  "control": "/absolute/control/new-generation",
  "evidence": "/absolute/checkout/evidence",
  "checkout": "/absolute/checkout",
  "jobs": "/absolute/control/new-generation-jobs.json",
  "jobs_sha256": "SHA256_OF_EXACT_JOBS_FILE_BYTES",
  "repository": "ad1896git/researchbase-pipeline-sandbox"
}
```

Generate and validate a reviewable artifact only:

```sh
/absolute/python3 -m scripts.pipeline_wakeup --config /absolute/timer.json --render-plist /absolute/com.researchbase.pipeline-wakeup.plist
plutil -lint /absolute/com.researchbase.pipeline-wakeup.plist
```

After separate deployment authorization, deployment must confirm the old
`com.researchbase.autopilot` and `com.researchbase.watchdog` labels are disabled,
unloaded and have no running work; preserve their original files and snapshots.
Only the new label may then be installed/enabled/bootstraped. Do not keep a
second kickstart, cron, shell loop or watchdog entry. Stopping the new label and
restoring legacy scheduling must follow CUTOVER.md's drain/snapshot/rollback
procedure; never kill an active task to satisfy this check. No launchctl commands
are executed by this module or its renderer.

Main branch protection was observed absent on 2026-10-30. Seven checks in this
observer are a local gate, **not server-enforced branch protection**. BACKLOG M01
records the owner decision; this PR never changes repository settings.

## Verification

`uv run pytest tests/pipeline` covers approval actor/event freshness, drift,
removal, changing remote observations, paginated CI, wrong producers, duplicate
checks, missing checks, human-only parking, independent work, immutable queue
admission, digests and both levels of busy lock. Existing real subprocess CI
continuation and crash-recovery tests remain enabled. Plist tests parse the
rendered artifact and require one 300-second entry without a shell or KeepAlive.
