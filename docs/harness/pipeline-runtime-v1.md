# Bounded engineering runtime adapters — second step

The publication executor and single-step runtime were merged in #40. The runtime
contains a short-session commander, sandbox worker, read-only CI waiter and explicit
single-step dispatch. The independently invoked outer cycle in
[pipeline-driver-v1.md](pipeline-driver-v1.md) now owns wait continuation, heartbeat,
retry and terminal-only exits. Neither CLI activates or installs the old loop.
No scientific implementation, canonical schema, runtime dependency or merge/label
authority is added. `.pipeline/bin` remains untouched.

## Commander and dispatch

`python -m scripts.pipeline_commander --control CONTROL --evidence EVIDENCE
--checkout SANDBOX` runs one new `codex exec --output-schema` session. It uses
read-only sandboxing, never `resume`, and never changes task state or rounds. The
host holds the protocol lock, validates exact output fields, revision and the
chosen task, and checks the authoritative state before accepting the proposal.
Only ready tasks with completed dependencies (or due protocol retries) and already
running read-only CI polls can be proposed. A running worker is never selected for
relaunch. `wait` and `stop` proposals must have an empty task ID.

`python -m scripts.pipeline_runtime --control CONTROL --evidence EVIDENCE
--checkout SANDBOX --jobs JOBS.json` performs one proposal plus at most one host
dispatch. `JOBS.json` maps task IDs to closed `{"kind":"worker","config":...}` or
`{"kind":"ci","config":...}` records. Unsupported kinds, including arbitrary
shell, publication, deletion and merge, are denied. Both adapters recheck the
proposal's revision under their own protocol lock, so another controller cannot
turn a stale proposal into a new execution. The caller invokes another step
explicitly; this module does not schedule or poll commander sessions in a loop.

## Worker

`python -m scripts.pipeline_worker --job JOB.json --control CONTROL
--evidence SANDBOX --timeout 180` runs an operator-defined task already in the
protocol state. `JOB.json` has exactly these fields:

```json
{
  "task_id": "historical-worker",
  "key": "historical-evidence-replay",
  "checkout": "/absolute/sandbox-clone",
  "prompt_file": "/absolute/task.txt",
  "head": "FULL_START_COMMIT_SHA",
  "base": "FULL_BASE_COMMIT_SHA"
}
```

The evidence root must be the checkout. Control and checkout cannot contain one
another. The checkout must have an explicit HTTPS sandbox origin and cannot be
the ResearchBase main repository. Worker jobs/prompts are bound before dispatch.
The intent is durable before `codex exec --sandbox workspace-write`; the sandbox
checkout is the sole configured writable workspace. Session flags explicitly clear
additional writable roots, exclude both /tmp and inherited TMPDIR, and disable
network access; --strict-config rejects unsupported settings. Control/checkout
overlap is rejected after resolving paths, so control cannot lie in an effective
writable root, even when control itself is in /tmp or TMPDIR. Jobs needing
temporary files must place them inside their checkout. The host, outside the model sandbox,
records the schema result, actual git HEAD, exit code and a per-attempt receipt.
The existing protocol verifies task/attempt/intent, scope, real evidence hashes
and host status. Model PASS cannot override a failed or timed-out process. A
timeout is a host failure even if a signal handler returns exit code zero.

Sessions run in their own process group, with a deadline no greater than 600 s.
The host applies bounded TERM/KILL cleanup to that group. A PermissionError when
probing/terminating a group is uncertainty, not proof that it stopped. This is
process-group cleanup, not a claim of containment for deliberately detached,
hostile same-user daemons. The adapter does not create quota-wait receipts or
automatically retry uncertain work. A parent crash with no terminal host receipt
keeps the running intent and requires operator reconciliation. A durable host
completion can be applied on restart without a second worker; a completed task
returns its validated result without launching another session.

Ambient user configuration is not loaded (`--ignore-user-config`); sessions are
fresh/ephemeral and use an allowlist of basic environment variables, excluding
GitHub and database credentials. Saved CLI authentication remains local and is
not copied. Agent instructions and reports are untrusted proposals, not canonical
scientific truth. This runtime is enabled only for explicit engineering sandbox
runs; no production material Harness dependency is enabled or repinned here.

## CI waiter

`python -m scripts.pipeline_ci --target TARGET.json --task TASK --control CONTROL
--evidence EVIDENCE --timeout 180` performs only GitHub reads. `TARGET.json` contains
`repository`, positive `pr`, `branch`, `head`, `base`, `base_commit`. Repository and
refs are configurable; the same main-repository denial and `pipeline-test/` branch
restriction apply. The seven required check names are the frozen protocol matrix:
`static`, `checks (0)` through `checks (5)`.

The observer binds PR number, repository, branch, exact head and base SHAs and open
state, then fetches all check-run pages. Missing/pending checks wait. Duplicate
names, wrong head or producer deny; skipped, neutral, cancelled and failed checks
never count as success. All seven must complete successfully; the observer then
rechecks the PR and checks before writing host evidence/completion. No check or
PR is modified. One absolute monotonic deadline starts at invocation entry and
covers ref-validation commands, all PR/check-run queries (including pagination),
confirmation and polling sleeps. Each command receives the smaller of the
remaining total budget and `--query-timeout` (default 10 seconds). Deadline checks
before/after observation and before completion reject late terminal results.
A query timeout returns `timeout` without retrying that query in the same call.
A zero total budget performs no query, state I/O or attempt allocation. Local
scheduling, subprocess reaping and filesystem overhead are not additional polling
budget and are measured separately; this is not a hard-real-time OS guarantee.
A bounded wait timeout preserves any established running intent and attempt;
resuming CI polling does not spend another round. Host errors or drift also leave
no PASS. Observation evidence is immutable and content-addressed; a crash after
evidence write but before completion can requery and reuse identical evidence
(or preserve it and write a new observation), with the same intent and attempt. No label, approval or merge authority is inferred from CI success.

## Validation and boundaries

Run `python -m pytest tests/pipeline`, repository Ruff/format checks, repository
Pyright and explicit Pyright over the pipeline scripts using the locked Python
3.12 environment. Operator evidence lives in
`.pipeline/logs/reviews/pipeline518/` (independent review and draft publication) and
`pipeline519/` (commander, worker, CI and final validation).

Live acceptance uses only historical evidence fixtures and the configured private
sandbox. It covers a schema-constrained read-only commander, an actual sandbox
worker denied a control-directory write, no duplicate worker on restart, a CI
wait timeout followed by the commander's continuation of the same intent, the
seven-check success matrix, and real failed CI. Test workflows exist only on
sandbox `pipeline-test/` branches, use no third-party actions, and do not change
repository settings. Test PRs are closed without merging; branches remain for
inspection. Previously accepted real SIGKILL publication evidence is preserved.

This completes the explicitly requested second-step adapters for isolated use.
Production scheduling/cutover, real model quota retry, hostile daemon containment,
notifications and human-label/merge integration remain outside this authorization.
Sandbox CI evidence never substitutes for exact-head main-repository PR CI.

Codex flag behavior was checked against local `codex-cli 0.164.0 --help` and
[official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
