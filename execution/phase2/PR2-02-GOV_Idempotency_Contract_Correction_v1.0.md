# PR2-02-GOV — Idempotency Contract Correction v1.0

**Status:** Normative correction to the accepted PR2-02-GOV execution pack. It corrects the command/event uniqueness statement only; it does not reopen or change accepted governance behavior or migration history. This correction is a prerequisite to PR2-02 design review and implementation.

## Authority and scope

This correction is later and more specific than PR2-02-GOV execution pack v1.0 §Schema item 7's event uniqueness sentence. That sentence's `(deployment_id, actor_id, event_kind, request_id)` tuple is superseded and is not the command idempotency namespace. The migration and implementation were inspected to establish the correction below. No historical migration or accepted evidence is rewritten.

## Canonical command request identity

The canonical command idempotency key is the ordered tuple:

```text
(deployment_id, actor_id, project_id, command_name, request_id)
```

`request_id` alone is not globally unique. `(deployment_id, actor_id, request_id)` is not a complete command identity. Reuse of the same request ID by the same actor and deployment in another project or under another command name is allowed and denotes a distinct command.

For a matching key, the canonical normalized request hash determines replay:

- key absent: execute the command once and persist its receipt atomically with the protected effect;
- key present and hash equal: exact replay; return or identify the prior result under the existing authentication/read-entitlement rules and do not repeat the effect;
- key present and hash differs: return `IDEMPOTENCY_CONFLICT`; do not mutate or replace the receipt.

## Event identity and deduplication

`source_merge_governance_events.id` is the immutable event identity and primary key. A request ID is not an event identity. Command request identity and event identity are separate concepts.

The existing `uq_source_merge_event_request` unique constraint is on the event table and uses `(deployment_id, actor_id, project_id, command_name, request_id)`. Its actual Application use was inspected: event-only command paths query this tuple and compare the stored request hash to resolve exact replay versus conflict. Accordingly, this event-backed row is the command receipt for those event-only paths; its uniqueness serves command idempotency. Proposal and approval commands also have their own durable rows and command-key constraints. Event UUIDs continue to identify individual event records.

The current event-only paths emit at most one event for the persisted event command key. When a command has separately recorded causal effects, the implementation uses its existing typed command/result record and the event command names established by the application. Do not add an event-kind uniqueness constraint or migration unless a reviewed command contract permits multiple same-key event kinds and requires that distinction. Any such schema change must be additive and must preserve event IDs and history.

The prior pack's four-column tuple `(deployment_id, actor_id, event_kind, request_id)` is not the canonical command key. It is not present as the event table's unique constraint in migrations 0021/0021a.

## Existing constraint audit

| Constraint | Table | Columns | Semantic purpose | Matches this correction |
|---|---|---|---|---|
| `uq_source_merge_proposal_request` | `source_merge_proposals` | `(deployment_id, proposed_in_project_id, proposed_by_actor_id, command_name, request_id)` | Proposal/supersession command receipt identity | Yes; same membership, with repository column names reordered |
| `uq_source_merge_decision_request` | `source_merge_approvals` | `(deployment_id, project_id, approver_actor_id, command_name, request_id)` | Approval/rejection command receipt identity | Yes; `approver_actor_id` is the command actor |
| `uq_source_merge_event_request` | `source_merge_governance_events` | `(deployment_id, actor_id, project_id, command_name, request_id)` | Event-backed receipt identity for event-only commands; also prevents a duplicate row for that event command | Yes |
| `uq_source_merge_project_decision` | `source_merge_approvals` | `(proposal_id, project_id)` | At most one immutable decision per project/proposal | Not a command-key constraint |

Migration 0021 already has the canonical five-member command key on these command receipt constraints. Migration 0021a adds lifecycle guards and does not change these constraints. No corrective migration is required. Do not rewrite 0021 or 0021a.

## Required PR2-02 application

Every PR2-02 command receipt uses the same canonical five-member key. Merge consumption uses `(deployment_id, actor_id, project_id, command_name='CONSUME_SOURCE_MERGE_PROPOSAL', request_id)`. On exact replay it returns the prior completed merge result after existing authentication and current read-entitlement checks, without re-consuming the proposal, adding another `SourceMergeRecord`, repeating alias or identifier effects, or duplicating a protected causal event. A changed request hash under the same key conflicts.

The PR2-02 acceptance matrix must prove same request ID reuse across projects and across command names is distinct; exact same-key/same-hash replay is single-effect; same-key/changed-hash conflicts; concurrent identical requests produce one execution; and event replay does not duplicate protected causal effects.
