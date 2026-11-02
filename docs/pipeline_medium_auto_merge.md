# Medium automatic merge: staged feature

This feature is HIGH risk and is not enabled merely by merging this PR. Its
released runtime, deployment review, fresh seven checks and owner approval are
still required. Existing version-1/2 policies retain their behavior. Version 3
adds `medium_auto` with `enabled`, absolute `journal`, and host-managed `reviews`.
No repository settings, labels, workflow checks or scientific authority change.

The host must create one empty journal (`version: 1`, `reservations: {}`) in the
protected control directory before enabling the feature. Missing, corrupt,
symlinked or oversized journals are not reinitialized. The same journal is used
across generations. Each pinned review specifies exact `head`, `base`, absolute
`file`, `sha256`, and distinct `author` / `reviewer` identities. Its JSON must
contain `verdict: PASS`, matching head/base and an empty findings list. These
pins are operator attestations of independence; model-produced text cannot add
pins or approve itself. Do not place the policy, reviews or journal inside a
writable candidate checkout.

For a medium task without a current trusted owner label, the executor reads the
complete PR inventory and both immutable Git trees, verifies regular blob modes
and Git content digests, and checks all old/new file contents. Only a closed
non-governing Markdown / inert example JSON / restricted Python AST profile is
recognized. No arbitrary imports, calls, class activation or dynamic identities
are admitted. Unknown consumers and classifications require a label; this is not
a semantic verifier for arbitrary Python. Tests are excluded from the 400-line
added-plus-deleted bound only when under `tests/` with a `.py` suffix. Their
contents and paths still undergo the same exclusions. Binary/missing patches,
renames/removals, governing material, migrations, credentials/privileges,
dependencies, D01 bindings, deployment and merge machinery are manual.

A valid label may use the original path when medium eligibility fails. Its
existing preflight restrictions, authorized actor, fresh base, independent
StateStore readiness proofs, seven trusted CI checks and retained source branch
remain mandatory. Neither path relabels medium as low. `AUTO-MERGE.OFF` blocks
all new timer requests, even approved labels; reconciliation of a request that
may already have happened remains read-only until its result is verified.

The first three distinct automatic merge identities reserve slots under one
shared process lock before publishing a request. A failed or ambiguous request
never automatically releases its slot. The automatic intent ID is derived from its immutable review, source and
readiness bindings, so a crash after reservation but before intent publication
reuses the same slot on recovery. A changed or abandoned binding may still hold
a slot; the host must inspect it, not delete/reset the journal. A fourth candidate waits for manual approval.
No expansion above three is implemented: owner confirmation and a separately
reviewed policy extension are required. This deliberately cannot infer consent
from successful notification delivery.

A requested medium intent with a lost response remains `awaiting_merge`, emits a
durable `merge_outcome_unknown` notification, and only queries its original PR
on later ticks. It never submits again. A verified squash produces a separate
immutable `<journal>.<reservation>.owner-review.json`, a durable
`pending_owner_review` journal entry, a deduplicated local notification, the
ordinary MERGE-LOG row and StateStore effect receipt. Each report is independently
recoverable before `done`. This is an owner audit inbox, not proof of delivery
or of owner review. Unknown/tampered evidence leaves the slot occupied and
requires operator investigation; unrelated engineering tasks may continue.

Local tests use simulated GitHub reads/writes, real temporary locks and files.
They are not real merge/canary acceptance. Deployment must separately establish
protected policy ownership, shared journal continuity, owner report delivery,
OFF behavior, one actual report after each of the first three successful merges,
and rollback procedures. Do not enable this candidate in the current runtime.
