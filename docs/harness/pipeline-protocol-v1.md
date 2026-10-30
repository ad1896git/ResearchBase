# Engineering pipeline protocol v1 — offline first step

This PR is separate from the lane/legacy-lock safety patch. It implements only
state protocol, file locking, recovery and structured report validation. It does
not invoke Codex, publish/merge a PR, schedule workers, send notifications, access
Postgres or activate a replacement loop. No new dependencies or scientific schema.

## Minimal state

New, operator-owned `.pipeline/control/state.json` is the sole authoritative
current control state. The legacy `state.json` and historical lanes remain intact.
The caller chooses a sandboxed test control directory for offline validation.

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

`scripts/pipeline_result.schema.json` is suitable for `codex exec --output-schema`.
The runtime additionally validates exact fields, duplicates, evidence containment,
hashes, commit and attempt bindings, and host exit status. A model's `pass` alone
cannot turn a failing execution into success. Worker completion is not independent
code verification: subsequent verify/review/CI tasks and their evidence are still
mandatory before accepting a PR. Host execution receipts and remote observations
must come from the future trusted executor, not the model's response.

## Human merge confirmation

A PR reaches `awaiting_merge` only with the complete successful static+six-shard
matrix on its expected head. It blocks dependent tasks, not unrelated work. The
human adds `approved-merge`; the future read-only GitHub observer supplies the PR,
event cursor, actor and observed head/base. The controller never adds this label.
Approvers default to an empty set: the operator must explicitly configure the
human account. A label predating readiness, wrong actor/PR/head/base, removed
label, missing/failed/duplicate required check or observed head/base drift denies
merge. Drift invalidates the approval; reapplying an old event cannot restore it.
The future executor must recheck GitHub state immediately before an atomic
`--match-head-commit` merge. This offline library performs no merge itself.

## Executable acceptance matrix

Run `python -m pytest tests/pipeline` using the existing locked environment.

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

These tests actually kill subprocesses and perform a local Git push. PR creation
is a durable remote-service test double, not live GitHub evidence. No claim is made
that an unimplemented GitHub executor has passed integration testing. Before any
live cutover, the separately approved executor integration must repeat these
scenarios through its real adapters, verify worker sandbox isolation and bounded
shutdown, and demonstrate human label confirmation. This PR does not authorize
that later integration or the cutover.
