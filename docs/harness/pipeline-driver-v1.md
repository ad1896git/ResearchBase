# Engineering cycle driver — wait continuation contract

This change is authorized only for the engineering sandbox driver and its tests.
It does not activate a loop, install into `.pipeline/bin`, change scientific state,
introduce dependencies, or grant publication/merge/label authority. Existing
single-step `pipeline_runtime` callers remain supported. An operator explicitly
starts the new `python -m scripts.pipeline_driver` CLI with an established ledger,
independent sandbox checkout/evidence root and fixed jobs file. It does not
initialize, reset or import legacy tasks. Workers still deny the main repository.

## Failure being repaired

The first real cycle's temporary driver raised `unexpected outcome wait` at
`first-cycle.py:63`. The merged #40 runtime also performed only one step: its
non-dispatch branch returned `wait`/`stop` unchanged and its CLI then exited.
Neither supplied an autonomous outer wait/continuation lifecycle. The new owned
cycle, rather than a prompt change or a modified old loop, fills that gap.

## Decisions, ownership and exits

One stable `driver.lock` owns the cycle; existing `control.lock` protects each task
transaction. The fixed policy, jobs, checkout and evidence paths are bound in
`driver-binding.json`; restart drift blocks unfinished tasks. Commander decisions
are still fresh read-only proposals, with exact revision and eligibility checks.

* `dispatch`: only the configured worker or CI adapter. Failed execution blocks
  with its receipt preserved. No arbitrary shell, publication or merge dispatch.
* `wait`: host chooses the authoritative eligible CI, blocks in the CI waiter and
  writes periodic heartbeats. Already-running/paused CI is resumed by the host
  before asking the model again. CI completion leads directly to a fresh commander
  session for ready successors, without human input.
* `stop`: exits only when tasks are terminal; an early stop blocks unfinished tasks.
* Unknown/malformed decisions or adapter outcomes: persist `blocked`, preserve
  intents/receipts, notify and exit with a non-success CLI status.
* A wait with no configured eligible/resumable CI blocks for human reconciliation;
  it does not spin new model sessions or silently abandon work. A running non-CI
  task with unknown outcome blocks rather than relaunching a possible live worker.

The exit invariant is: after lifecycle ownership, every task must be `done`,
`blocked` or `budget_exhausted` before an ordinary/graceful driver exit. `failed`
becomes an explicitly blocked reconciliation case; it is not silently retried.
The driver handles SIGTERM/interrupt by blocking, not by claiming successful work.
SIGKILL, machine loss, corrupt/unwritable state or loss of ownership cannot be made
transactional by Python: they require operator recovery and never imply PASS.
Startup rejection before ownership is not an execution of a cycle.

The default budget is five execution attempts, enforced against the existing
protocol `rounds_used`; one initial CI claim counts as its first attempt. Waiting,
heartbeats, retry delays and resumed observation of the same intent consume no
additional attempts or model rounds. At the budget limit, unstarted work becomes
`budget_exhausted`; existing CI may finish its read-only observation first.

## CI wait time, heartbeat and retry

The default full CI window is **9000 seconds (150 minutes)**. It is deliberately
separate from the model-session limit (180 seconds), query cap (10 seconds) and
poll interval (2 seconds). Each waiter invocation uses one shared monotonic deadline,
including validation, every query, confirmation and sleeps. A per-query timeout
cannot be disguised as CI success. Configurable total waits are capped at 86400s.

Recent completed main-repository CI observations used for this default:

| Run | Observed wall duration, seconds |
| --- | ---: |
| 41014517541 | 4813 |
| 41014490269 | 5051 |
| 41000536785 | 4652 |
| 41000507560 | 3577 |
| 40991081275 | 4911 |

Durations are run createdAt→updatedAt, including queue/cleanup overhead, not claims
about CPU time. 9000s leaves 3949s above this sample maximum (~78% headroom).
Raw observation evidence is retained under `.pipeline/logs/reviews/pipeline-wait/`.

A heartbeat thread writes atomic `driver-heartbeat.json` plus append-only
`driver-heartbeats.jsonl` every five seconds, including while queries/model
subprocesses block. Phase and task identify `ci_wait` and `retry_wait`. Heartbeat
write failure is not ignored. Immutable `driver-events/` records decisions, real
CI pending/pass observations, outcomes and the final exit; no fixture replaces
GitHub in live acceptance.

A timeout persists the existing CI task as `retry_wait`, reason `ci_timeout`, with
retry_at and an immutable intent-bound `ci-retry-*.json` receipt. This is explicitly
different from a model quota receipt: it proves a bounded read-only observation
returned, not that a model process was refused. It cannot authorize worker replay.
The task result stays NULL until actual CI completion; no timeout writes a
per-attempt scientific/completion PASS. These additive v1 states fail closed under
older readers; never run an older driver against this new paused ledger.

The driver writes a durable local `notifications/` record and flushes a JSON notice
to stderr, remains alive with heartbeat during the retry delay (default 60s), then
resumes the same intent and attempt. It never exits normally in retry_wait. Three
CI timeout windows are permitted by default; exhaustion explicitly blocks and
notifies. These counts derive from durable receipts, including after restart.
A receipt→state interruption recovers the pause before polling; resume markers
separate an already-resumed receipt from a pending pause. Receipt/binding drift
fails closed. No external messaging integration or credentials are introduced.

## Acceptance

`tests/pipeline/test_pipeline_driver.py` includes an actual subprocess invariant:
while CI is pending and in retry_wait, the child remains alive and heartbeat and
notification evidence appears. On an IPC release, it completes the same CI intent,
automatically asks the commander for the dependent worker and exits only when done.
Other tests cover every action, premature stop, unsupported executor, malformed
commander output, timeout limit, pause/reopen/recovery/tampering, retained failed
receipts, policy drift and budget exhaustion. Unit observations are test doubles;
they are not counted as live GitHub proof.

Live acceptance must use a new `pipeline-test/` sandbox PR whose real integrity
checks include several minutes of actual CI waiting. Run the committed driver
unchanged, record pending→pass, heartbeats throughout, fresh successor commander
and actual sandbox worker receipt. Preserve branches and all evidence. Independent
review and exact-head main-repository CI are required before human merge labeling.
There is no cutover or old-loop installation in this PR.
