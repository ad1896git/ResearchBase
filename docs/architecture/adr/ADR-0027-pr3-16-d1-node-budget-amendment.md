# ADR-0027 — PR3-16 D1 paired bearing-evaluation amendment

Status: PROPOSED, pending commander final review and acceptance. No code slice is
authorized by this ADR. The detailed proposed contract and blockers are in
[the D1 contract](../../phase3/design/PR3-16-d1-amendment-contract.md).

## Decision proposed 2026-10-28

Replace the earlier open-ended producer/evaluator questions with one bounded operation:
compare already-produced candidate and baseline predictions against identical frozen
labels, sample IDs and split/group protocol. Compute classification accuracy and
imbalance diagnostics deterministically. This is an operational observation, not a
scientific Measurement or Claim, a training job, a provider invocation, Run execution,
or evidence of a new physical fault. A new-fault candidate requires independent
verification in a separately authorized track. Fixture results do not establish
empirical superiority. No PR3-17 ranking or selection is authorized.

A new versioned compound Application command reserves existing task budget and appends
one PROPOSED node atomically. A trusted core consumer evaluates outside the transaction
and settles in a separate attributed command. Prior stops deny; only a stop proven to
arise from this transaction consuming its own last unit permits this node, with a
durable task stop and no implicit session closure. Preserve sticky stops, UNKNOWN
charges, current entitlement after waits, and original receipt replay. ADR-0026 and
ADR-0029 remain controlling except for the specifically proposed guard amendment.

Existing `ArtifactVersion`, dataset snapshot, metric and Run input models are candidate
provenance owners, but the source does not establish a durable typed binding from a
search node/reservation and its settlement to all paired inputs, protocol and evaluator.
The contract identifies this as an activation blocker, not an invitation to store
unvalidated arbitrary JSON or create an unapproved canonical table. The deployment's
bounded resource/pricing profile and production capability composition are also not
present in source; activation requires measured evidence and an explicit owner before
any production claim. No dataset or performance result is supplied by this decision.

## Staging and compatibility

1. Concrete pure evaluator/value contract and tests, without activation.
2. Minimal forward PostgreSQL guards; admission still denied until Application wiring.
3. Atomic admission and attributed settlement with the concrete core consumer.
4. Real PostgreSQL regression/CI and independent acceptance. Commander separately
   authorizes each actual code slice after review.

Recheck the sole migration head before a forward migration after
`0082_experiment_search_core`; never edit 0078/0080/0081/0082. Preserve v1 material,
replay, guards and ACLs, all scientific hashes, and the current 10-node/3-depth/
11-event/zero-link read profile. Future writer extensions first require compatible
measured complete-response bounds. Before migration use, rollback removes only the
new forward objects; after use, preserve immutable history and use forward repair.
No deletion/refund of historical gaps or UNKNOWN outcomes is permitted.

The previous 2026-10-27 question-only draft is superseded by these selections; its
historical evidence is available in version control. This proposal is not acceptance,
implementation evidence, or permission to run a real bearing study.

## Separately reviewable Stage 1 scope

Stage 1 is only a pure in-memory paired evaluator and closed value contract. It may
be reviewed/authorized separately while this production amendment stays PROPOSED.
It performs no Artifact I/O, SQL/UoW, budget mutation, producer registration, node
admission, scientific Measurement/Claim persistence or Run execution. No deployment
pricing/vector/latency proof is inferred from its tests. O02 arithmetic and the
explicit Stage 1 bounds/undefined-value rules in the companion contract must be
closed before its source implementation; O01/O03/O04/O09 activation dependencies
remain blocking for subsequent production slices. Local probe fixtures establish
computation behavior only, never an empirical bearing diagnosis improvement.
