# ADR-0027 — PR3-16 D1 paired bearing-evaluation amendment

Status: PROPOSED for the production amendment. Separately scoped commander
authorizations below and in the companion contract do not activate production. The detailed proposed contract and blockers are in
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

Propose one immutable typed provenance tuple on the existing reservation: five
`ArtifactVersion` roles, one `DatasetSnapshot`, one `MetricDefinitionVersion`, and
one consumer-generation UUID for attribution only. Seven nullable RESTRICT FKs and
one nullable UUID distinguish all-null legacy reservations from complete v2 bindings.
Usage inherits the tuple through its existing reservation FK; legacy settlement must
not settle v2 reservations. Source Runs are omitted: evaluation consumes supplied
predictions and association would not prove their production. No new table or truth
owner is proposed. The companion contract specifies checks, material and catalog delta.

Admission validates typed identity, project, frozen state and stored canonical hashes
using DB metadata only, plus bounded no-I/O registered evaluator digest checks.
Stored metadata does not prove bytes were read. After admission commits, outside DB
locks and before parsing/evaluation, the consumer reads ArtifactStore bytes and
verifies their byte hashes. Deterministic mismatch settles FAILED with no score and
admitted counters retained; uncertain completion remains UNKNOWN. Metadata denial
before admission commits has zero effects. Stage 1 remains purely in memory.

Under the existing task lock, first v2 admission rejects legacy scored history in
the same step. Reciprocally, fresh legacy settlement rejects a nonnull score if that
step has any v2-owned reservation, including admitted/in-flight work. Recheck after
waits and at deferred completion so either ordering prevents mixed comparisons.
No-score legacy accounting remains available under existing rules, and legacy
settlement in steps without v2 reservations retains its behavior and v1 replay.

Production composition, registration/revocation and recovery coordination, and the
deployment resource/pricing profile still require concrete evidence and separate
acceptance before activation. No dataset or performance result is supplied here.

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

### Commander Stage 1 authorization — 2026-10-28

After independent cold review PASS/no P0/P1 at `1cf17316`, the commander accepts only
the separately scoped pure Stage 1 in-memory numerical/value contract and authorizes
its implementation plus unit/architecture tests. The review's P2 cross-reference is
corrected: end-to-end ArtifactStore/PG/resource proof belongs to Stage 3, not Stage 1.
The owner delegated this decision. ADR-0027's production amendment stays PROPOSED;
no Artifact I/O, canonical provenance binding, migration, capability registration,
budget mutation or node activation is authorized by this acceptance.


### Separately reviewable Stage 2 selection — 2026-10-28

The commander selects the exact disabled O09 catalog slice for separate review before code authorization; production remains PROPOSED. New v2 deadline_seconds equals reserved W and is reconstructed from that immutable field; exact transaction-epoch deadline must fit the existing earliest-reservation task origin cap, otherwise deny without clipping. Registered remaining-phase allowance is a later mandatory Application check, not guessed from W. Preserve the two independent existing reason owners: accounting task-event reason and node/search mutation reason may differ for v2 only, validated by a new early v2 dispatch; all legacy checks remain unchanged. No extra storage is needed and all eight frozen serializer/result examples retain their meaning. No enablement, new table, production grant or service wiring belongs to this slice. See the companion Stage2 section for exact named constraints and acceptance boundary.


### Commander disabled Stage 2 acceptance — 2026-10-28

Accept only the separately reviewed disabled schema/guard contract at8cbc9afb, after independent read-only PASS/noP0/P1. Authorize0083 forward migration, ORM binding columns and required PG18/regression/current-head checks under the exact companion manifest. Correct the prospective proof wording; no guard or new migration test has yet passed. Enablement stays literal false, no new production grants/services/registry; all unclosed production facts remain blocking and the full amendment stays PROPOSED.
