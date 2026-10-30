# Engineering pipeline protocol v1 — offline first step

This PR is separate from the lane/legacy-lock safety patch. It implements only
state protocol, file locking, recovery and structured report validation. It does
not invoke Codex, publish/merge a PR, schedule workers, send notifications, access
Postgres or activate a replacement loop. No new dependencies or scientific schema.

## Minimal state

New, operator-owned `.pipeline/control/state.json` is the sole authoritative
current control state. The legacy `state.json` and historical lanes remain intact.
The caller chooses a sandboxed test control directory for offline validation.
Initialization requires explicit `create=True` and a genuinely new directory.
An immutable initialization marker distinguishes lost state from a new pipeline;
missing state in an established directory never silently starts an empty ledger.

Root fields: `version` (1), `revision`, `rounds_used`, `tasks` (keyed by task ID).
Each task has only `needs`, `status`, `attempt`, `intent`, `result`, `retry_at`,
`reason`, `merge`. An intent binds a unique ID, action kind, resource key, head and
base. A result references an immutable per-attempt host receipt. A merge binding
holds PR/head/base, a readiness event cursor and the approving event/actor.
No conversation, credentials, scientific facts or arbitrary job configuration is
stored here. Unknown fields/versions, duplicate keys and cyclic dependencies deny.

Statuses: `ready`, `running`, `retry_wait`, `awaiting_merge`, `blocked`, `failed`,
`budget_exhausted`, `done`. These are not interchangeable. A failed task is not
automatically retried. Deletion and architecture actions always become `blocked`
without an execution intent. Independent tasks whose dependencies are done remain
eligible when another task is blocked or awaiting merge.

`StateStore` holds a kernel file lock for its entire context. State updates validate
the previous revision, fsync the temporary snapshot, atomically replace the file,
then fsync its directory. Task attempts and receipts are never reset or overwritten.
Current state remains authoritative; receipt files are durable evidence, not a
second mutable ledger. The controller must not delete/recreate the control directory
or lock inode, and workers must have no write access to that directory.

## Recovery and report boundary

Persist an intent before an external action. A running resource is not reassigned
to a new task after restart. A durable completion written before a crash is checked
and applied without running the worker again. An interrupted/partial receipt or an
unknown remote outcome denies replay and requires reconciliation, not blind retry.
Publication recovery consumes a host observation of the existing branch/PR bound
to the expected key/head/base; there is deliberately no push/create operation here.
Generic model reports cannot complete publication. Every referenced receipt,
including failures, is revalidated on reopening. A quota wait needs a bound host
terminal receipt with reserved exit code75: the executor must establish that the
model was refused without executing work and all mutating descendants are stopped.
An absent/uncertain terminal receipt keeps the running claim and denies retry.

`scripts/pipeline_result.schema.json` is suitable for `codex exec --output-schema`.
The runtime additionally validates exact fields, duplicates, evidence containment,
hashes, commit and attempt bindings, and host exit status. A model's `pass` alone
cannot turn a failing execution into success. Worker completion is not independent
code verification: subsequent verify/review/CI tasks and their evidence are still
mandatory before accepting a PR. Host execution receipts and remote observations
must come from the future trusted executor, not the model's response.
Host receipts also bind the immutable intent key. Verification/review keys use
`pr:<number>` and must match the recorded publication's PR and head; successful
evidence for another PR with the same commit cannot be substituted.

## Human merge confirmation

A PR reaches `awaiting_merge` only with recorded publication, verification and
separate review task dependencies, all bound to this PR/head, plus the complete
successful static+six-shard matrix. The receipts are checked again before merge
eligibility. It blocks dependent tasks, not unrelated work. The
human adds `approved-merge`; the future read-only GitHub observer supplies the PR,
event cursor, actor and observed head/base. The controller never adds this label.
Approvers default to an empty set: the operator must explicitly configure the
human account. A label predating readiness, wrong actor/PR/head/base, removed
label, missing/failed/duplicate required check or observed head/base drift denies
merge. Drift invalidates the approval; reapplying an old event cannot restore it.
Label absence carries the observer's authoritative removal cursor; delayed older
approval events cannot undo a later removal. A readiness baseline alone is insufficient.
When the label is present, the observer must supply its currently effective
application event and actor, not just its presence or the last event cursor. That
pair must match the stored human approval. Removal and unauthorized re-addition
between polls therefore invalidate old approval; older events cannot overwrite a
newer approval. The protocol does not infer these facts from a label-name list.
The future executor must recheck GitHub state immediately before an atomic
`--match-head-commit` merge. This offline library performs no merge itself.

## Executable acceptance matrix

Run `python -m pytest tests/pipeline` using the existing locked environment.
Use the project's Python3.12 environment, not the legacy loop's system Python.

| Cutover condition | Executable coverage |
| --- | --- |
| Two starts yield one writer/runner | `test_concurrent_processes_have_only_one_owner`, `test_two_outer_loops_launch_only_one_autopilot`, `test_two_protocol_writers_cannot_enter_the_same_store` |
| Interrupted execution resumes safely | `test_crash_after_durable_result_recovers_without_rerunning`, `test_dead_driver_with_live_worker_refuses_restart`, `test_existing_running_resource_is_not_reassigned_after_restart` |
| Push/PR followed by crash does not create another PR | `test_push_and_pr_created_before_crash_are_reconciled_not_recreated`, `test_unknown_publication_is_not_blindly_retried` |
| Missing/wrong JSON never becomes PASS | `test_missing_or_malformed_output_never_becomes_pass`, `test_wrong_structured_fields_rejected`, `test_claimed_pass_does_not_override_host_failure_or_lose_history` |
| Wrong head/base cannot merge | `test_head_or_base_drift_invalidates_approval_permanently`, `test_no_merge_for_incomplete_wrong_or_failed_ci`, `test_receipt_for_another_commit_cannot_make_report_pass` |
| Quota waits do not spend more rounds | `test_quota_wait_does_not_consume_rounds_and_budget_exhaustion_is_distinct` |
| History and existing lanes are preserved | `test_claimed_pass_does_not_override_host_failure_or_lose_history`, safety tests for dirty/incomplete/conflicted lanes and interrupted Git operations |
| Awaiting human merge does not halt independent work | `test_awaiting_merge_does_not_block_independent_tasks` |
| Human-only actions and approval scope | `test_deletion_and_architecture_always_require_human_decision`, `test_stale_label_removal_and_reapplication`, `test_default_policy_and_unauthorized_actor_cannot_approve_merge` |

Additional executable restart/readiness negatives cover missing established state,
quota without terminal receipts, overlapping quota retries, missing/partial/altered
failed receipts, generic publication-report bypass, missing proof dependencies,
another PR with the same head, and evidence tampering after human approval.

These tests actually kill subprocesses and perform a local Git push. PR creation
is a durable remote-service test double, not live GitHub evidence. No claim is made
that an unimplemented GitHub executor has passed integration testing. Before any
live cutover, the separately approved executor integration must repeat these
scenarios through its real adapters, verify worker sandbox isolation and bounded
shutdown, and demonstrate human label confirmation. This PR does not authorize
that later integration or the cutover.

State validation rejects impossible status/intent/receipt combinations and requires
rounds_used to equal total attempts before dispatch or mutation. Restart corruption
is covered by `test_corrupt_execution_state_is_rejected_before_restart_dispatch`.
Quota scope fields and all seven required CI names are tested independently.

## Additive engineering driver states

The driver continuation contract in `pipeline-driver-v1.md` adds read-only CI
`retry_wait` with reason `ci_timeout` and immutable timeout/resume receipts. It is
not a quota wait and cannot call `begin` to obtain another attempt. Only `resume_ci`
may return it to running after its due time. Existing root/task fields and the
rounds_used=sum(attempts) invariant remain unchanged. Older readers reject the new
state, so this ledger must not be reopened by the old driver. Explicit driver
blocking may preserve an unresolved worker/CI intent or a failed completion receipt;
blocking never authorizes replay or rewrites the receipt. See the new invariant and
pause recovery tests in `test_pipeline_driver.py`.
