# Consent Withdrawal, Grant Resolution and Offboarding (B16) Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B16 extends [B15](B15_Package_Preparation_Contract_DRAFT.md) with direct-author
withdrawal, alternating consent successors and PREPARED regrant. Withdrawal and
staling of all unused preparation grants for the exact manuscript commit together.
An authenticated author can withdraw their own consent after project role or
membership removal without regaining project access. This is a proposed narrow
Application permission, not a new identity credential or representative authority.

Read §§1–4 first, §10 for terms, §11 for pinned choices and §12 for construction.
B09 and B13 exist; B15 is a draft dependency, not implemented package persistence.
Approval of this contract does not authorize its implementation.

Build only after separate authorization:

1. Reconcile accepted B15 and migration head. Extend its consent guards in a new
   forward migration; retain its four tables, immutable context and NULL hashes.
2. Implement the exact resolver (§3.1), consent hash/chain verification and narrow
   self-withdrawal permission. No new canonical object or persistence mechanism.
3. Implement SHARE-first writes and the participating-writer protocol (§12.2).
   Extend B13's terminal guards only for a proven same-transaction withdrawal.
4. Extend B15's Application service and lock-free readers. Regrant requires current
   project entitlement and valid fixed context; withdrawal does not.
5. Run focused tests (§12.4), retain exact evidence and stop at §12.5.

Five review rules:

1. A grant never substitutes for current direct HUMAN consent. Actor comes from
   VerifiedPrincipal; OWNER, corresponding author and Agent cannot consent for another.
2. Append one same-chain successor of the current head, never edit history.
   Withdrawal needs a GRANTED head; regrant needs WITHDRAWN and PREPARED.
3. Resolve by exact package→manuscript/project→request→decision→grant FKs. Include
   every ACTIVE unconsumed grant, even if its validity time has elapsed.
4. Protect empty resolver ranges against grant INSERTs. Sorted row locks alone
   are insufficient; no grant-table SHARE lock followed by an UPDATE upgrade.
5. Every read/replay uses one REPEATABLE READ snapshot with no explicit table,
   advisory or row locks, including nested authorization and provenance helpers.

## 1. Purpose, authority and inspected baseline

| Authority | Binding rule |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 13, 31; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Facts precede authority; immutable formal history; authorship differs from membership and approval. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 28 | Registered AuthorConsent, package and grant events; concrete FKs, common Application boundary, additive compatibility. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§23–24, PR2-17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 4; [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md) | PreparedSubmissionVersion is local preparation history, not SubmissionVersion or external send. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), AuthorConsent and hash lifecycle; [Identity R2 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md) | Literal consent material; required identity proof; no membership-to-authorship substitution. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1, 3; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Evidence for both states; alternating immutable chain; atomic related-grant staling; no frozen reactivation; fresh post-wait DB authorization. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21; [authorship contract](PR2-17_Submission_Authorship_Contract_DRAFT.md), §§3, 11.1, 12.1 | Application-only canonical writes; exact resolver; offboarding is an explicitly missing contract. |
| [B09](B09_Approval_Tuples_Contract_DRAFT.md), [B13](B13_Grant_Consumption_Contract_DRAFT.md), [B15](B15_Package_Preparation_Contract_DRAFT.md) | Finite approval tuples; one-way grants/events; fixed PREPARED package and direct evidence-backed roots. |

Inspected 2026-10-18:

- Migration head is [0059](../../migrations/versions/0059_b13_grant_consumption.py).
  No B15 package/consent tables exist. Reserve no migration number here.
- [approval.py](../../src/researchbase/application/approval.py) and
  [approval_repository.py](../../src/researchbase/persistence/approval_repository.py)
  own issuance, lifecycle, receipts, scope advisory locks and sorted grant locks.
  B13 disables manuscript consumption/effect bindings; its reserved package UUID
  is constrained NULL. B16 does not enable those branches.
- B13 `b13_validate_event`/`b13_complete` require OWNER and give expiry precedence
  for explicit lifecycle commands. Calling that public lifecycle service for each
  grant cannot implement direct-author atomic withdrawal, particularly for expired
  ACTIVE rows. §12.1 specifies the bounded guard extension instead.
- [decision_repository.py](../../src/researchbase/persistence/decision_repository.py),
  [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py)
  and B15 supply SHARE-first READ COMMITTED/protected-read patterns;
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) supplies deferred
  final-graph checks, and [0057](../../migrations/versions/0057_xid_wraparound_guards.py)
  supplies native XID sealing. No new lock service, journal or mutable head is needed.

## 2. Scope, dependency boundaries and non-goals

Implement only after B15 is accepted and implemented. Retain B15 preparation,
root consent, OWNER package withdrawal, occurrence projection and readback. Extend
`record_author_consent` to WITHDRAWN successors and GRANTED regrants. Add one narrow
own-consent read query for offboarded authors. The surface remains Application-only;
no API route or CLI command is introduced in this slice.

B16 does not turn offboarding into automatic author withdrawal. Membership removal
changes authority, not authorship or scientific history. An issuing approver's
role removal still uses B09/B13's separate same-transaction grant-staling rules.
No account-recovery, anonymous/public withdrawal, representative authority,
credential bypass, deletion request or external notification is introduced.

The present state domain remains PREPARED/WITHDRAWN. FROZEN/SUPERSEDED behavior
in §3 is a binding requirement for a later freeze integration, not permission to
loosen B15's state/hash CHECKs, add receipts or fabricate frozen-package fixtures.

## 3. Invariants and conservative judgments

1. **Fixed context.** Package, exact manuscript, sealed same-Publication snapshot,
   authors and non-consent occurrences remain B15 material. Consent never moves
   between packages. A chain key is `(package_id, actor_id, PREPARED_PACKAGE)`.
2. **One head.** Root GRANTED has NULL prior. Successor cites the exact current
   head, matches all chain keys and alternates GRANTED/WITHDRAWN. No timestamp
   cutoff, latest-by-time selection, fork, merge, self-link or copied root.
3. **Withdrawal is termination.** Permit on any existing package that has this
   author's GRANTED head, including OWNER-withdrawn packages and inactive Projects.
   Require identity, local chain/context integrity and retained frozen evidence;
   do not rerun manuscript validity, stage, project membership or ArtifactStore
   availability as a scientific admission gate. Current upstream STALE/INVALID
   cannot prevent revocation of permission. Corrupt local chain/hash fails closed.
4. **Evidence.** Both states retain an exact nonnull frozen ArtifactVersion FK/hash.
   Regrant follows B15 evidence access and byte/hash checks. For withdrawal the
   caller may reuse evidence already bound by their own chain; that exact-reference
   verification needs no byte download or project access. New evidence requires
   current B15 entitlement and byte verification. Evidence retention is not a new
   signature: the live direct HUMAN command supplies the withdrawal intent.
5. **Regrant.** PREPARED only, live HUMAN snapshot author with current project read
   entitlement, ACTIVE Project and valid fixed B15 closure/evidence. No writer role
   required. WITHDRAWN package never reactivates. A regrant cannot revive terminal
   grants; fresh approval is separate. B15 preview uses current heads, not roots.
6. **Frozen compatibility.** A later integrated freeze locks the same package and
   all heads in sorted Actor-ID order. Withdrawal after freeze leaves status,
   hashes, manifest-bound consents and frozen_at unchanged and derives STALE.
   Regrant cannot repair a frozen binding; new package, consent and approval are
   required. Do not materialize a second package-validity owner.

### 3.1 Exact package/manuscript grant resolver

Use the approved authorship contract §11.1 query literally, bound parameters only:

```sql
SELECT g.id
FROM prepared_submission_versions p
JOIN publications pub ON pub.id = p.publication_id
JOIN approval_requests r
  ON r.manuscript_version_id = p.manuscript_version_id
 AND r.project_id = pub.project_id
 AND r.approval_purpose = 'PREPARE_SUBMISSION'
JOIN approval_decisions d ON d.approval_request_id = r.id
JOIN approval_grants g ON g.approval_decision_id = d.id
WHERE p.id = $1 AND pub.project_id = $2
  AND g.project_id = pub.project_id AND g.purpose = 'PREPARE_SUBMISSION'
  AND g.status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM approval_grant_consumptions c WHERE c.grant_id = g.id)
ORDER BY g.id;
```

`$1` is package UUID; `$2` is project UUID. No Publication-only, snapshot-only,
requester-only, JSON locator or consumption result join. All packages sharing the
exact manuscript share this grant scope. Different manuscript versions, Projects,
READY grants and internal-release grants are excluded. Include ACTIVE rows past
valid_until; consent withdrawal records STALE, not EXPIRED, for this explicit cause.
Already terminal grants/receipts remain untouched.

Verify exact immutable request/decision/grant/event structure before effects.
ACTIVE plus an existing consumption is corruption, not a reason silently to skip
that row; separately check that contradiction in the same exact manuscript scope.
Capture the entire ordered result under §12.2 protection, lock each row in that
order, reread and append one ACTIVE→STALE event per selected row. No cap, LIMIT or
partial batch: one withdrawal covers the whole scope or rolls back.

The resolver is a cut at the serialized withdrawal. A new grant committed first
is included; a grant issued later is a distinct authorization subject to all
current approval gates and future package-specific consumption consent checks.
B16 does not invent a permanent manuscript veto or package association on grants.
Issuance alone cannot restore withdrawn consent or make a terminal grant ACTIVE.

## 4. Proposed commands, closed DTOs and historical readback

Extend B15's `PreparedSubmissionService.record_author_consent` and its existing
`RecordAuthorConsentCommand`; do not introduce another consent write owner.
Root GRANTED remains unchanged. WITHDRAWN requires nonnull prior GRANTED head;
GRANTED with nonnull prior is regrant from WITHDRAWN. §11 pins fields.

`get_own_author_consent(GetOwnAuthorConsentQuery)` returns only the caller's exact
consent metadata and current own head, after direct HUMAN/chain ownership proof.
It works after role/membership removal and discloses no package contents, other
actors, grants, manuscript, evidence bytes or project listing. General B15 history,
preview and exact-consent reads retain their project-entitlement requirement.

Withdrawal/replay requires a live VerifiedPrincipal, unretired HUMAN actor and
live actor-subject binding/credential matching that actor, with no proxy. No
current membership or project role is required. Possession of package/consent
UUIDs alone proves nothing. Resolve the prior consent's actor and package/project
privately and compare to the principal before returning data. For this narrow
path, absent or foreign/unowned routing IDs uniformly return FORBIDDEN. Missing
principal is AUTHENTICATION_REQUIRED; revoked credentials/retired actor deny.
Regrant and general reads use B15's entitled NOT_FOUND/foreign-project policy.

Same UUID, actor, package/project, state, scope, exact evidence and prior ID return
the saved consent after current authorization for that operation. Withdrawal
replay uses the narrow self permission even after role removal. Root/regrant
replay retains current project read entitlement. Changed material is
IDEMPOTENCY_CONFLICT after permission checks. A different UUID naming an old head
is CONCURRENT_MODIFICATION, even if a later record has the requested state.
Completed replay never reruns first-use gates or adds events. New grants created
after the original withdrawal are not swept by replay. A writer noticing a saved
UUID closes its UoW and uses the lock-free replay snapshot.

## 5. Schema and literal hash proposal — no migration

Extend B15 `author_consents`; add no table, mutable head, offboarding token,
withdrawal receipt, JSON policy or package-to-grant relation. Evidence and prior
are concrete RESTRICT FKs. B13's grant events are the grant history.

Keep Hash R2 15 AuthorConsent material exactly: type/material_version=1,
`prepared_submission` ID-only reference, `actor` ID-only reference, `consent_state`,
`consent_scope`, exact `evidence_artifact`, exact `prior_consent` or explicit NULL.
Canonical-json-v1 UTF-8/NFC, lowercase UUID/digest and sha256-cjson-v1; captured_at
and operational metadata are excluded. Recursively verify prior hashes without
replacing saved exact material with a current head. Package's ID-only consent
reference remains acyclic. No new material version or Phase 1 hash changes.

## 6. Error contract — existing categories only

Use §11.2; no AUTHOR_CONSENT_* or SUBMISSION_PACKAGE_INVALID codes are added.
Invalid DTO, absent entitlement, old head, immutable mutation and corrupt saved
provenance remain separate errors. Sanitize all narrow-path denials. No error
returns a list of affected grants to an offboarded author.

## 7. Transactions, concurrency and failure recovery

One command equals one synchronous PostgreSQL transaction. Writes use READ
COMMITTED with §12.2's literal SHARE inventory as FIRST SQL, before SET LOCAL,
authorization, clock or advisory/row locks. Acquire final table modes directly.
All snapshots and chain reads after blocking waits are freshly reread under the
held locks; no stale pre-lock admission or SERIALIZABLE snapshot-refresh claim.

Check live credential/binding/identity at fresh `clock_timestamp()` immediately
before effects and after `SET CONSTRAINTS ALL IMMEDIATE`. Regrant also rechecks
membership/role/stage/closure at that time. Further waits repeat the checks.
Never use now(), transaction_timestamp(), caller time or a retained pre-wait clock
for expiry. No external call occurs while holding grant locks; ArtifactStore
verification, when required, follows the existing local store boundary.

Retry only SQLSTATE 40001/40P01, exactly three total fresh UoWs, no delay. Third
conflict is CONCURRENT_MODIFICATION. Do not retry business denials, 23505, timeouts,
unknown commit or lost connection as success. Unknown outcome requires exact
entitled read/replay. Failure between consent, grant updates, events or deferred
checks rolls everything back, with no independently committed lifecycle call.

Read, preview, own read and completed replay configure REPEATABLE READ READ ONLY
before SELECT; all nested verification uses plain reads in that UoW. No explicit
table/advisory/row locks, repair, staling or retry that writes. Snapshot entitlement
plus advancing-clock expiry cannot exclude revocation committed after the snapshot
began; report no stronger read guarantee.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes test files/cases. Use accepted Application fixtures and real
PostgreSQL 18.x, independent engines/backend PIDs, pg_locks evidence and explicit
barriers. Sleeps alone do not prove serialization. No SQLite or forged frozen
packages; freeze integration tests stay deferred until that slice exists.

## 9. Acceptance criteria and evidence boundary

Acceptance requires exact resolver exclusions, empty-range/new-grant race proof,
all-or-nothing withdrawal/events, narrow offboarded self access, mandatory evidence,
immutable alternating chain and PREPARED regrant without grant revival. Preserve
B15 occurrence/context, null hashes, OWNER withdrawal and lock-free read guarantees.
Normal-role SQL must satisfy the same graph/lock guards; no trigger disabling.
No B16 draft, preview or focused regression result establishes full PR2-17,
Human Gate, package freeze, external send or Phase 2 completion.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Consent head | Unique immutable chain row with no successor; not max timestamp. |
| Withdrawal | Direct author's GRANTED→WITHDRAWN append; not OWNER package withdrawal. |
| Regrant | WITHDRAWN→GRANTED append on the same PREPARED package. |
| Offboarded author | Snapshot author with removed/expired project membership or roles; authorship remains historical. |
| Narrow self permission | Live direct HUMAN may withdraw/read own consent metadata, without project access. |
| Related grant | Exact §3.1 manuscript/project PREPARE_SUBMISSION ACTIVE unconsumed grant. |
| Phantom | Newly inserted matching request/decision/grant missed by row-only locking. |
| STALE | Terminal grant status or derived package validity, distinct owners and meanings. |
| SHARE / SRE | PostgreSQL SHARE / SHARE ROW EXCLUSIVE table modes. |
| Deferred constraint trigger | Final graph validation at commit or forced constraints, following 0042. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Decision | Adopted proposal |
| --- | --- |
| B15 extension | Enable successors only; retain four tables, immutable context, PREPARED/WITHDRAWN package states and NULL package hashes. |
| Offboarding | Direct self-withdrawal and own metadata read survive role/membership removal; live identity proof remains mandatory. No general project access. |
| Evidence | Both states nonnull frozen evidence. Withdrawal can reuse own retained chain evidence without bytes or current project entitlement; new evidence uses B15 checks. |
| Staling | All exact-scope ACTIVE unconsumed grants, including expired ACTIVE; one event each, attributed to withdrawing author. No terminal edits. |
| New grants | Serialize issuance against resolver cut; later issuance never repairs consent and must pass full independent gates. No new persistent veto. |
| Regrant | PREPARED plus current B15 entitlement/admission; never terminal grant revival or frozen-binding repair. |
| Surface | Application-only; transport mappings pinned for future adapters. |

### 11.2 Pinned error mappings

Pairs match [api/errors.py](../../src/researchbase/api/errors.py) `_STATUS` and
[cli/errors.py](../../src/researchbase/cli/errors.py) `CLI_EXIT_CODES`.

| ErrorCode | HTTP | CLI | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/enum/Unicode/limit failure. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing verified principal. |
| FORBIDDEN | 403 | 3 | Identity, proxy, scope, own-path routing or entitlement denial. |
| NOT_FOUND | 404 | 3 | Authorized general-path exact ID absent; never own-path enumeration. |
| VERSION_NOT_FROZEN | 409 | 4 | Existing required evidence/context is unfrozen. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required frozen reference unavailable; regrant evidence bytes unavailable. |
| INVALID_STATE_TRANSITION | 409 | 4 | Same-state successor, root WITHDRAWN or regrant on terminal package. |
| IMMUTABLE_RECORD | 409 | 4 | UPDATE/DELETE of consent, event or sealed material. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same UUID with differing normalized material. |
| CONCURRENT_MODIFICATION | 409 | 4 | Old head/successor uniqueness race, exhausted retryable SQLSTATE. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK failure. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt hashes/chain/parent, receipt contradiction or incomplete staling. |
| APPROVAL_GATE_FAILED | 409 | 4 | Missing preheld protocol or existing approval gate denial. |
| GRANT_INVALID | 409 | 4 | Existing lifecycle/consumption invalid-grant category; not withdrawal denial for expiry. |
| GRANT_STALE | 409 | 4 | Existing consumption current-consent denial; no read-side event write. |

Unexpected fallback remains HTTP 500 / CLI 1, sanitized INTERNAL_ERROR. No arbitrary
exception or unknown database failure becomes successful replay.

### 11.3 DTO fields, Python types, limits and enums

Use frozen slotted dataclasses and closed adapters. UUID requires `type(x) is UUID`;
integers exclude bool; all fields required, including nullable prior. Preserve B15
NFC/NUL/surrogate rules, lowercase 64-hex hashes and aware UTC DB instants. No
caller actor, timestamp, hash, manifest, status update, grant list or proxy field.

```python
ConsentState = Literal['GRANTED', 'WITHDRAWN']
ConsentScope = Literal['PREPARED_PACKAGE']
RecordAuthorConsentCommand:  # B15 extension, no defaults
    id: UUID
    project_id: UUID
    prepared_submission_version_id: UUID
    consent_state: ConsentState
    consent_scope: ConsentScope
    evidence_artifact_version_id: UUID
    prior_consent_id: UUID | None
GetOwnAuthorConsentQuery:
    project_id: UUID
    prepared_submission_version_id: UUID
    id: UUID
OwnAuthorConsentReadback:
    consent: AuthorConsentReadback
    current_head: AuthorConsentReadback
```

`AuthorConsentReadback` retains B15's exact fields/types, except state uses the
above enum and `prior_consent: ExactReference | None` replaces None. ExactReference
for prior is AuthorConsent UUID/hash; evidence is ArtifactVersion UUID/hash.
Own read returns only these two same-actor/package records, not expanded references.
Writes return `AuthorConsentReadback`, with no affected-grant metadata. General
B15 readbacks now expose all consents ordered by snapshot author ordinal then
chain traversal from root; preview selects the current GRANTED head per author.
Missing/withdrawn heads both contribute to `missing_author_ids`/CONSENT_MISSING;
no candidate digest until every author is currently GRANTED. No new stored state.

B15's ≤100 authors, ≤1000 contributions, ≤10000 occurrences including reserved
consent slots and 1..2 package events remain unchanged. Chains have no arbitrary
lifetime append cap: withdrawal must not be blocked by history length. Traverse
iteratively with cycle detection; never truncate returned history or hash closure.
Grant resolution is also uncapped and atomic; operational timeout rolls back the
whole command. Existing B15 reason bounds apply only to OWNER package withdrawal;
consent command has no new reason field or unhashed narrative.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch with types and constraint names

One forward migration under `migrations/versions/` after accepted B15/current head.
Do not edit 0042, 0057, 0059 or B15's migration. No new table or runtime dependency.

```sql
ALTER TABLE author_consents DROP CONSTRAINT ck_b15_consent_root;
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_state
 CHECK (consent_state IN ('GRANTED','WITHDRAWN'));
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_scope
 CHECK (consent_scope='PREPARED_PACKAGE');
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_root
 CHECK (prior_consent_id IS NOT NULL OR consent_state='GRANTED');
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_not_self
 CHECK (prior_consent_id IS NULL OR prior_consent_id<>id);
```

Retain B15 types: `id`, package/actor/evidence/prior/created_by UUID;
state VARCHAR(16), scope VARCHAR(24), captured_at/created_at TIMESTAMPTZ,
content_hash CHAR(64), hash_scheme VARCHAR(32). Only prior is nullable. Retain
`pk_author_consents`, all B15 RESTRICT FKs, `ck_b15_consent_actor/hash/time`,
`uq_b15_consent_package(package,id)`, partial `uq_author_consents_root` and
`uq_author_consents_successor`, and `ix_b15_consent_history`. Existing indexes
cover predecessor/head lookup; add no head column or redundant index.

| Named guard / timing | Required change/enforcement |
| --- | --- |
| `b15_consent_guard` replacement, BEFORE INSERT | Require §12.2 preheld inventory/modes and READ COMMITTED. Lock manuscript→Publication→package; validate snapshot author/HUMAN/evidence structure. Root keeps B15 gate. Successor has same package/actor/scope as prior, prior is current head, opposite state. WITHDRAWN permitted on OWNER-withdrawn package; regrant only PREPARED. No UPDATE/DELETE exception. |
| `b16_consent_chain`, DEFERRABLE INITIALLY DEFERRED AFTER INSERT on author_consents | Validate single GRANTED root, alternating connected acyclic chain, same keys, exact prior/evidence hashes and unique head. New row actor=created_by, capture time=creation time. Use native `xmin=pg_current_xact_id()::xid` to identify new withdrawal causes. |
| `b16_withdrawal_staling`, deferred AFTER INSERT on author_consents and AFTER INSERT/UPDATE on approval_grants and AFTER INSERT on approval_grant_events | For each new WITHDRAWN row, exact resolver scope has no ACTIVE unconsumed remainder; every newly staled grant has exactly one matching event and no receipt. Validate all affected graph rows after all writes, not a statement-order approximation. |
| B13 `b13_validate_event` and `b13_complete` replacements | Add only the consent-cause branch below; keep all old lifecycle, issuer-offboarding, issuance, receipt and one-terminal-event checks for every other case. |
| `b16_prepare_grant_guard`, BEFORE INSERT on approval_grants | PREPARE_SUBMISSION grants require preheld Publication SRE, existing purpose scope coordination and exact durable request/decision/manuscript/project closure. No trigger taking table locks after the INSERT statement has begun. Missing preheld protection denies. Other finite tuples retain existing guards. |

For the new consent-cause branch, event is ACTIVE→STALE, no consumption; reason
is exactly `author consent withdrawn:<canonical consent UUID>` (fixed prefix plus
36 characters); actor equals that newly inserted WITHDRAWN row's actor; occurred_at
equals its captured_at. Resolve that row through concrete package/manuscript FKs,
not by trusting parsed text alone. The row must be new in this native transaction,
hash-valid, same-chain, attributable to a live direct HUMAN. Event UUID uses the
existing server UUID generator. B13 terminal update/event implementation must
support this branch atomically, including its event-first validation sequence.

This branch replaces OWNER and pre-expiry requirements **only for this proved
withdrawal cause**, including at deferred completion. No global skip, configurable
session flag, trigger-depth-only authorization or SECURITY DEFINER bypass. It
must not call B13's unavailable manuscript consumption gate. SQL checks structure
and live binding; Application additionally verifies the trusted credential subject.
A retained event reason identifies the consent for replay/audit, not a new locator
or scientific source of truth. Keep B13 one-terminal unique index and receipt XOR.

Map guard failures using existing UoW normalization: immutable P17F1→IMMUTABLE_RECORD;
corrupt final graph P17F2→PROVENANCE_CLOSURE_VIOLATION; authority P16A1→FORBIDDEN;
preheld protocol failure P16G1→APPROVAL_GATE_FAILED (HTTP 409 / CLI 4, unchanged).
23503→REFERENTIAL_INTEGRITY_ERROR; malformed 23502/23514→VALIDATION_ERROR;
23505 successor/root→CONCURRENT_MODIFICATION after entitled replay comparison.
Give new named guard failures explicit existing-category normalization, not a new
ErrorCode. Empty downgrade restores B15 functions/checks; refuse populated B16
successors/events rather than deleting history. Upgrade preserves all B15 roots.

### 12.2 Exact lock order and transactions

Define literal `B16_SNAPSHOT_TABLES` in the repository, not a dynamic schema scan
or private import. These are B15's inputs minus publications (which needs SRE):

```text
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions
measurements metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects review_issue_events review_issues
run_artifact_inputs run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions scientific_conclusions
source_versions statistical_result_inputs statistical_results
```

Every B16 consent write: (1) one literal `LOCK TABLE <inventory in lexical order>
IN SHARE MODE` as FIRST SQL in fresh READ COMMITTED UoW; (2) `LOCK TABLE publications
IN SHARE ROW EXCLUSIVE MODE`; (3) `LOCK TABLE approval_decisions,
approval_request_reviews,approval_requests IN SHARE MODE`; (4) SET LOCAL
lock_timeout='10s', statement_timeout='30s'. No SHARE on consent/package/grant/event
output tables and no table-mode upgrade. The global Publication SRE is the existing
B13 coordination mechanism: it excludes B09's preheld Publication SHARE before
B09 can issue a grant, and excludes B13 maintenance before either reaches scopes.

| Command | Exact subsequent operations |
| --- | --- |
| record_author_consent, all states | Advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, bound key `b15:consent:{id}`; privately route package/project; scope advisory `pr216:scope:{project_id}:PREPARE_SUBMISSION`; exact manuscript FOR UPDATE; Publication FOR UPDATE; package FOR UPDATE; this actor's chain rows FOR UPDATE ordered UUID; reread saved UUID, head and local graph. After any wait repeat identity/authorization at fresh DB time. Saved UUID exits to read replay. Root/regrant uses full B15 admission; withdrawal uses narrow self permission and local chain verification. |
| WITHDRAWN continuation | Run §3.1 resolver under held table/parent/scope protection; grant rows FOR UPDATE in returned UUID order; plain read/reverify request, decision, event and receipt graph; rerun resolver/contradiction check after waits. Fresh identity check; insert consent with DB capture time; terminalize every selected grant/event with that cause/time. Force deferred constraints; final fresh identity/binding check; commit. No package status/row_version/event mutation. |
| GRANTED continuation | Root or alternating PREPARED regrant only; reverify B15 context/evidence and current entitlement. Fresh clock; insert consent/hash; force constraints; final fresh admission; commit. No grant status/event writes. |
| own read / general read / preview / completed replay | Fresh REPEATABLE READ READ ONLY; no explicit locks. Authorize narrow own path or B15 project read path; plain exact parent/chain/hash reads and diagnostics within snapshot; final fresh credential/entitlement clock check; return only authorized DTO. No lifecycle maintenance. |

All new helpers are in-UoW, with no nested public S1 `_get`, B13 lifecycle service,
locking authorization helper or independent transaction. Head selection is an
anti-successor query under package exclusion, never ORDER BY captured_at LIMIT 1.

| Participating writer | Required compatibility |
| --- | --- |
| B09 request/decide, including new grants | Existing B09 first-SHARE includes publications, so it commits before B16 acquires SRE or waits until after B16 commits. For decide_approval use existing B09 inventory excluding publications as FIRST SHARE, then direct Publication SRE before request/scope/target locks; choose this prefix unconditionally before the DB lookup of request purpose. Request creation may retain B09 prefix. Preserve all other gates and sorted affected-grant locks. Never upgrade held Publication SHARE. New guard enforces the issuance prefix even for normal-role SQL. |
| B13 lifecycle/consumption | Existing base SHARE→Publication SRE→approval SHARE prefix serializes before scope/target/grant locks. Retain current release behavior and disabled manuscript branches. Integrate consent-cause guard, not public OWNER maintenance calls. |
| B15 preparation, roots and OWNER package withdrawal | Existing Publication SHARE excludes B16 SRE; migrate root writes to B16 consent prefix when extending the service. B15 package withdrawal still does not stale manuscript grants or append author withdrawal. |
| Membership/role/credential and scientific writers | Input SHARE excludes changes and INSERT phantoms. Scheduled expiry still needs advancing-clock checks. Preserve B09 issuer-role-loss staling; test both orders and bounded deadlock recovery for older target-first writers. |
| Later freeze/consumption | Must adopt compatible preheld prefix and manuscript→Publication→package→sorted author chains→sorted grants order, verify current heads, and reject withdrawn packages. Requires separately approved effect/receipt contract; do not enable now. |

Grant insertion phantoms are excluded by Publication table coordination, including
when there are zero matching grants or requests. A writer acquiring SRE must do
so before selecting the affected range; a trigger merely locking known grant rows
is insufficient. Normal-role SQL must prehold the modes before its statement.
All protocols use existing advisory namespaces; B16 adds no advisory lock service.

### 12.3 Ordered build steps and module paths

1. Reconcile B15 at `migrations/versions/`; add §12.1 forward revision and named
   guard replacements. Do not loosen B15 manifest sealing, package state/hash
   checks or 0059 result tuple. Verify upgrade/downgrade and retained root hashes.
2. Extend B15's planned `src/researchbase/domain/prepared_submission.py` with pure
   alternating-chain validation and exact prior hash material, reusing
   `src/researchbase/domain/authorship.py` references and foundation hashing.
   No ORM/transport imports or new scientific fact owner.
3. Extend B15's planned `src/researchbase/application/prepared_submission.py` with
   closed §11.3 DTOs, narrow direct-self permission and own read. Extend typed
   ports in `src/researchbase/application/ports.py`; keep one consent service.
4. Extend B15's planned `src/researchbase/persistence/prepared_submission_repository.py`
   with literal inventory/prefix, resolver, contradiction check, plain snapshot
   reads and sorted chain locks. Extend `src/researchbase/persistence/approval_repository.py`
   for in-UoW consent-cause terminalization and PREPARE issuance prefix. Update
   `src/researchbase/application/approval.py` issuance sequencing only as required
   above; preserve all existing finite tuple/independence/rejection gates.
5. Wire typed repository/UoW members and named normalization in
   `src/researchbase/persistence/uow.py`. Use existing credential verification
   and plain protected identity reads; do not alter project entitlement globally.
   No API/CLI wiring, dependency or credential schema changes.
6. Implement §12.4, retain exact evidence and stop. These B15 module paths are
   planned dependency files, not claims of present code. If accepted B15 uses
   different paths, reconcile the contract before implementation.

### 12.4 Test artifacts and required cases

Create `tests/integration/phase2/b16_fixtures.py` using B15's accepted Application
builders and `phase2_database_url`. Migrate disposable PostgreSQL 18.x to head;
retain direct HUMAN author credentials after membership removal, unrelated Project,
two exact manuscripts and multiple packages sharing one manuscript. Build grants
through accepted B09/B12 commands; never forge READY or disable seals. Where grant
creation requires another unimplemented dependency, mark that test blocked until
it exists rather than bypassing it. Two independent engines/PIDs for races.

| File to create | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b16_consent_contract.py` | Closed DTOs, strict UUIDs, no actor/proxy/time fields, two states/one scope; root/alternating chain; old head, fork/cycle/self/wrong-chain; permission split and metadata disclosure; iterative long chains. |
| `tests/unit/phase2/test_b16_consent_hash_vectors.py` | Independent literal R2 vectors: root NULL prior, withdrawal exact prior hash, regrant, reused evidence, Unicode; tampered prior/evidence changes digest; timestamps excluded; B15/Phase 1 vectors unchanged. |
| `tests/integration/phase2/test_b16_consent.py` | Root→withdraw→regrant; full exact-scope staling including expired ACTIVE; exclusion of other project/manuscript/purpose/terminal/consumed grants; ACTIVE-receipt corruption denies; zero grants; same-manuscript multiple packages; preview uses heads; package status/NULL hashes unchanged; no package/event mutation from author withdrawal. |
| `tests/integration/phase2/test_b16_offboarding.py` | Remove last role, end membership, scheduled expiry and inactive Project: direct own withdrawal/read still works with live credential; reuse own retained evidence without bytes; new evidence requires B15 access; nonauthor/Agent/proxy/retired actor/revoked binding/credential denial; absent/foreign IDs same sanitized denial; general history/preview remains forbidden; no other-author/grant/bytes disclosure. |
| `tests/integration/phase2/test_b16_replay.py` | Same UUID after restart/role loss/upstream invalidity; changed actor/material conflict only after permission; old-head new UUID loses; root/regrant replay requires read entitlement; replay does not stale later grants or create events; unknown commit recovered by exact ID. |
| `tests/integration/phase2/test_b16_schema.py` | Catalog names/types/FKs/indexes, populated root upgrade preserving hashes, empty downgrade/populated refusal; normal-role SQL fork/same-state/forged cause/missing preheld protection, empty deferred graph, missing/extra/wrong event and ACTIVE remainder denial; evidence NOT NULL; immutable UPDATE/DELETE; preserved B13 OWNER/expiry/receipt guards outside consent-cause branch. |
| `tests/integration/phase2/test_b16_concurrency.py` | Grant INSERT vs withdrawal both commit orders, including initially empty request/grant ranges; issuance waits on Publication coordination before snapshot; two successors/withdraw-regrant/OWNER-withdraw races; resolver waits then fresh reread; grant maintenance both orders; authority revocation and scheduled credential expiry across each wait; SQLSTATE 40001/40P01 three attempts and no business/timeout retry; failure after consent/each grant/event/deferred check leaves zero partial changes. |
| `tests/architecture/test_b16_boundaries.py` | Common Application boundary, no new schema/JSON semantic owner/head/token, no role bypass for general reads, lock-free nested reads/replay, first-SHARE SQL and no upgrades, no external send/receipt/effect enabling; future adapters use exact pinned errors. |

After implementation run these tests plus B09, B12 preparation approvals, B13
lifecycle/schema/concurrency and B15 regressions. Static commands:
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`;
unit/architecture: `uv run pytest tests/unit tests/architecture --tb=short`.
Use focused PostgreSQL file lists and report actual commands, counts and server
version. The owner's loop runs the whole suite; do not run it here.

### 12.5 Not in this slice

- Package freeze/supersession, READY transitions, manuscript consumption receipts,
  B13 result branch enabling, frozen-state fixtures or full PR2-17 acceptance.
- Public/representative withdrawal, legal signature/PKI, account recovery, retired
  identity reactivation, consent delegation or automatic withdrawal at offboarding.
- New top-level schema, persisted head/current pointer, package-grant association,
  permanent manuscript veto, event bus, scheduler, queue or background staling.
- API/CLI exposure, general project read access after offboarding, evidence download,
  bulk author discovery, external send, SubmissionVersion/Record or ExternalEffect.

## 13. Open questions for the owner — override register

All choices above are adopted proposals; none delegates policy invention to the
implementer. Owner approval must explicitly accept the narrow self permission,
retained-own-evidence withdrawal policy, expired-ACTIVE consent-cause staling and
Publication SRE coordination. An override requires corresponding body edits before
ratification. B15 acceptance and separate execution authorization remain necessary.

## 14. Documentation verification note

This task adds only this draft. Proposed B16 tests and database behavior above are
not implemented or verified by regression runs. Actual drafting checks follow.

All `uv` commands below used this exact environment prefix (shared existing
virtualenv; disposable cache, no dependency changes):

```sh
UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv UV_CACHE_DIR=/tmp/researchbase-b16-uv-cache
```

| Command after that prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | Exit 0: All checks passed. |
| `uv run --no-sync ruff format --check .` | Exit 0: 639 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0: 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/unit tests/architecture --tb=short > /tmp/researchbase-b16-unit-architecture.log 2>&1` | Exit 1: 5,105 passed, 4 failed, 12 errors, 8 warnings in 69.23s; not PASS. |

Exact focused PostgreSQL command, with that same prefix:

```sh
PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b12_prepare_approval.py tests/integration/phase2/test_b13_grant_lifecycle.py tests/integration/phase2/test_b13_grant_schema.py tests/integration/phase2/test_b13_grant_concurrency.py tests/integration/phase2/test_pr2_17_authorship.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_17_authorship_concurrency.py -x --tb=short > /tmp/researchbase-b16-postgres.log 2>&1
```

Result: exit 1, **1 setup error in 0.86s**, before database assertions; remaining
cases not run. Localhost PostgreSQL access was denied with `Operation not permitted`;
server version could not be verified. No PostgreSQL PASS is claimed. The four
unit failures are HG1 Unix-socket operations denied by the sandbox; the twelve
PR2-19 architecture setup errors are denied PostgreSQL connections. Eight existing
warnings concern Alembic path_separator deprecation. No whole-suite run occurred.

Draft-specific verification: a `python3` relative-link check inspected 27 local
links with 0 missing targets; a `PYTHONPATH=src uv run --no-sync python` check
(with the same environment prefix) compared all 15 §11.2 mappings to imported
`_STATUS`/`CLI_EXIT_CODES`, with 0 mismatches. `git diff --check` exited 0.
`git diff --no-index --check /dev/null docs/proposals/B16_Consent_Withdrawal_Contract_DRAFT.md`
reported no whitespace errors (exit 1 denotes the added-file difference).
Only this requested document is added; no implementation, test, migration,
dependency, governing file, branch, commit or push was changed or created.
