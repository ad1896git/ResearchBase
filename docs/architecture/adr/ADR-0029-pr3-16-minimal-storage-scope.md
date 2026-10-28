# ADR-0029 — PR3-16 minimal storage scope

Status: PROPOSED — 2026-10-27. No implementation authorization.

## Context and decision

The owner requests simplification after repeated design cycles. The unmerged
prototype at `30ef634` (including its ADR-0028 candidate) is superseded as an
implementation target by this proposal; preserve that branch and review history.
Frozen scientific invariants, accepted historical commands and ADR-0026 remain.
This amendment changes only the bounded PR3-16 choices stated below.

1. **One goal per task.** Session `objective_definition` is a required closed read
   projection `{source: "RESEARCH_TASK", research_task_id: UUID, text: string}`.
   Text is the exact owning `research_tasks.objective`, never caller-supplied session
   content. Existing same-task/project FKs bind the session to that source.
   Migration 0077's task guard (immutable-field tuple) already rejects objective
   changes; no independent session goal can drift from it.
   All sessions of a task share its goal; a different goal requires a new task.
   This deliberately refines Phase 3 §29's StructuredValue, rather than omitting it.
   No objective Artifact, snapshot columns, new hash scheme, Unicode range table,
   content-version negotiation or fresh-create v2 contract. Preserve draft V01/V02
   and all accepted vectors. Do not re-normalize or rehash the owning task text.
2. **Reuse authorization.** Use the existing CredentialVerifier/Application
   boundary, current read entitlement, committed replay before fresh-write checks,
   and fresh checks after waits/writes/forced constraints. Missing or unsupported
   trusted bounded no-I/O verifier denies. No new 30-second credential subsystem,
   generation registry or production-verifier claim in PR3-16. Keep the existing
   exact 18-table SHARE and project/command/task prefix. Explicit exception:
   rb_phase2_lock_project's inherited project-row lock precedes identity keys;
   Agent actor key precedes all subsequent task/step/identity rows; Human has only
   common keys. No AgentVersion/availability/execution prerequisite or copied
   gateway orchestration. Exclude own xmin from committed-receipt replay.
3. **Bound the deliverable.** Retain the four admitted tables and create/append
   command names, with no Run-link writer. Link/failure/prune/close, scoring and
   semantic duplicates remain separate unfulfilled obligations. D1's reviewed
   atomic amendment remains mandatory before production node activation; no fake
   producer/evaluator or safety/settlement widening. This partial storage scope
   is not complete PR3-16 or usable autonomous search.
4. **Bound current reads.** One read-only snapshot, complete requested history and
   existing sanitized integrity errors. Initial node/depth limits 10/3; parallel
   1 means existing task-wide outstanding-reservation occupancy, not historical
   siblings or concurrent readers. Current create/append event catalog permits
   at most 11 events per in-bound session and zero Run links. Use these explicit
   event/link response limits for this slice; reject overflow with sanitized
   VALIDATION_ERROR and no partial result. An extension or larger writer profile
   must ship compatible measured whole-response limits first. No pagination or
   silent truncation. Budget accounting/caps themselves are not changed.

## Compatibility, integrity, migration and verification

The sole goal source is the existing immutable task field. The returned projection
is operational intent, not scientific truth or a new canonical object. Existing
exact Hypothesis/ExperimentSpec references and scientific hashes remain unchanged.
Create/replay uses the original task/session IDs and v1 material; tree/lineage adds
its task-goal projection within the same snapshot. Replay never re-executes writes.
No legacy data is rewritten. No extra objective schema or Artifact I/O is needed.

Implement from the existing four-table design on main, with the bounded identity
key clarification above; do not copy the expanded 30ef634 objective/Unicode code.
Recheck the integration parent before allocating migration 0082. Preserve old guard
branches, named constraints/ACLs and immutable history; use forward repair after use.
Before implementation, one focused review must confirm this goal projection and
scope. Then S1 covers migration/storage constraints only; repository/services/reads
follow separately. Required real-PG18 tests cover exact catalog, valid/invalid
scope, no-op mutation rejection, effect cardinality, old-row preservation and one
forward head. Later behavior tests cover immutable goal projection, exact replay,
Human/Agent admission, fresh checks and response boundaries. Missing tests are NOT
RUN. A design review or documentation-only CI skip is never implementation PASS.
