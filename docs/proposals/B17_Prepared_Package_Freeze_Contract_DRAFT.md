# Prepared-package Freeze (B17) Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B17 freezes an existing PREPARED package against the exact manuscript, authorship,
manifest and current author consents. It consumes one distinct PREPARE_SUBMISSION
grant through B13 in the same transaction. It records no external send.
This document proposes the remaining package lifecycle and G7 freeze evidence;
owner approval and separate execution authorization are still required.

Build in this order:

1. Reconcile the head (currently `0064_b14_publication_ready`) and the six gates
   in §3.1. Add only the forward migration in §12.1.
2. Extend the existing pure package types/hashes and B13 concrete result decoder
   (§11.3), preserving old vectors and saved results.
3. Add `freeze_prepared_submission` to PreparedSubmissionService and an in-UoW
   B13 consumption helper. Follow §12.2 before any database lookup.
4. Extend package exact reads, history, preview and OWNER withdrawal for frozen
   history. Preserve B16 direct-author withdrawal and narrow offboarding access.
5. Build the PostgreSQL gates, races, G7 suffix and bounded benchmark in §12.4.
   Record exact results and remaining blockers, then stop.

Read §§1–3 first, use the glossary (§10) as a lookup, and use §11 as the fixed
policy/DTO/error contract. §12 supplies the build plan. Old dependency inventories
are historical evidence; command presence alone is not acceptance.

Five rules whose violation fails review:

1. Exact scientific closure and current VALID facts precede every authority gate.
2. Bind each author's current GRANTED head; preserve frozen consent FKs forever.
3. Freeze, supersession, package events, receipt and grant terminalization commit
   together, with no failed-command maintenance side effects.
4. Use B16's compatible prefix and author-before-grant order; preserve B13's
   SERIALIZABLE effect transaction. All reads/replays are lock-free snapshots.
5. Frozen withdrawal changes derived validity, never hashes or consumed history;
   G7/benchmark evidence cannot establish unrelated Phase 2 gates.

**Scope:** documentation proposal only. This is neither a migration nor an
architecture freeze, execution pack, implementation authorization or gate result.

## 1. Purpose, authority and inspected baseline

| Authority | Rule carried into this draft |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 9–13; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Facts precede authority; exact immutable provenance; prepared differs from sent; fresh DB time and entitled replay. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§12–18, 28, 41 | Existing publication objects and concrete relations; common Application boundary; additive compatibility and golden regressions. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§23–24, 34, 37–42, PR2-17 | Prepared package, authorship, internal gates and E2E evidence; no external effect. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7; [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), prepared-package rows | Separate single-use preparation grant; registered lifecycle, typed manifest and append-only events. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), “Authorship and prepared package”; [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–3 | Literal package payloads; exact current consent at freeze; withdrawal races and retained historical hashes. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Normalized consumption request, concrete saved result, SERIALIZABLE atomic effect, advancing clock after waits. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–19 | Application-only canonical writes and executed evidence before acceptance. |
| [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md), §§3, 11–12; [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md), §12 | Draft structure, six prerequisites, bounded slices; novelty is not an implicit freeze gate. |
| [B13](B13_Grant_Consumption_Contract_DRAFT.md), §§11–12; [B15](B15_Package_Preparation_Contract_DRAFT.md), §12.5; [B16](B16_Consent_Withdrawal_Contract_DRAFT.md), §12.2 | Reuse receipts; widen both B15 status/version checks; adopt manuscript→Publication→package→author chains→grants ordering. |

Current code, rather than older proposal inventories, supplies the baseline:

- `application/manuscript_freeze.py`, `internal_review.py`, `decision.py`,
  `approval.py` and `publication.py` implement B04–B05, B11–B14, B14a and B14r.
  Migrations 0062–0064 add entry, READY approval and the atomic READY effect.
- `application/prepared_submission.py`, `domain/prepared_submission.py` and
  `persistence/prepared_submission_repository.py` implement B15/B16. Migration
  0060 permits only PREPARED/WITHDRAWN, null package hashes and no persisted
  AUTHOR_CONSENT item; 0061 implements alternating consent and grant staling.
- `domain/approval.py:consumption_request_material` already admits the freeze
  request shape, but its saved-result decoder admits only release and READY.
  Migration 0064's `ck_b13_result_tuple`, receipt/hash functions and consumption
  guard likewise enable only those two effects. The package result UUID column
  exists without an enabled package FK/result branch. B17 must complete it.
- `tests/integration/phase2/test_pr2_19_dependencies.py` still lists package
  blockers. `tests/e2e/test_pr2_20_benchmark.py` has no package freeze case.
  Reconcile only B17-owned subcases; do not erase historical blocker evidence.

No target B17 execution pack is supplied by this drafting task. All implementation
names below are proposals, not claims that B17 code/tests already exist.

## 2. Scope, dependency boundaries and non-goals

Add one Application command to freeze a precreated package; enable exact frozen
history/readback, supersession by a newer package, and OWNER withdrawal from
FROZEN. Preserve B15 preparation and B16 consent commands. Consume the exact
manuscript preparation grant through B13; never consume the READY grant again.

B04–B05, B11–B16, B14a and B14r are dependencies, not work to reimplement.
G7 gains the preparation/current-consent/freeze suffix and bounded performance
samples. Novelty retains its separate accepted scope. See §12.5 for exclusions.
No executable file, migration, test, dependency or governing file changes here.

## 3. Invariants and prepared-package closure

Publication must be READY with this exact current FROZEN ManuscriptVersion.
Package and authorship snapshot belong to that Publication and Project. Reverify
B04 document bytes, placements and transitive scientific/literature closure in
this UoW, plus S1 snapshot/contribution hashes and HUMAN author coverage. Reuse
in-UoW verifiers; public services opening separate transactions are unsuitable.
Hash mismatch or missing exact dependency fails closed. A correctly shaped hash,
review, Decision, Approval, consent or Agent assertion cannot repair invalid facts.

Non-consent manifest rows must equal B15's sealed occurrence projection, including
multiplicity and category/ordinal, without extras or deduplication. FIGURE/TABLE
map to exact ArtifactVersion, CITATION to SourceVersion, CLAIM to ClaimVersion,
CONCLUSION to ScientificConclusionVersion. OTHER remains unsupported. Document
and authorship references occur only in the two manifest top-level fields.

For every snapshot author, inspect the complete same-package/actor/scope chain,
verify every link/hash and evidence binding, and select its unique terminal head
by absence of successor. Require exactly one GRANTED PREPARED_PACKAGE head and
no unlisted author chain. Verify retained evidence bytes, size, frozen material
and hash. No timestamp/latest heuristic, truncated chain scan or proxy consent.
Persist one AUTHOR_CONSENT item per author, zero-based ordinal in authored order.

### 3.1 Six prerequisite gates, independently rechecked

These are the first six rows of PR2-17 §12.1, not six interchangeable approvals:

| Gate | Implemented owner and required proof at freeze |
| --- | --- |
| 1. Manuscript freeze/sealed placements | B04 `application/manuscript_freeze.py`, B05 exact manuscript reviews: same selected FROZEN manuscript, document bytes, exact placement/hash closure and current VALID facts. |
| 2. Publication READY transition | B14 `application/publication.py`: verify the saved READY event and its distinct B13 receipt, tied to this Publication and manuscript basis; lifecycle text alone is insufficient. |
| 3. Manuscript internal review | B05 `application/internal_review.py`: required exact-target independent reviews, verified hashes and complete Issue discovery; no applicable OPEN/BLOCKING Issue, including closure targets. |
| 4. READY_FOR_SUBMISSION Decision | B11 `application/decision.py`, B14r approval: verify exact affirmative prior basis and independent approval behind the READY receipt; it supplies no preparation authority. B14a's exact entry must remain consistent. |
| 5. PREPARE_SUBMISSION Decision | B12 `application/decision.py`: distinct PROCEED for this exact manuscript/hash, complete sealed review basis, matching request and independent HUMAN approval. Preserve rejection/new-target fences and typed conditions. |
| 6. Grant consumption/lifecycle | B13 `application/approval.py`: exact ACTIVE, unexpired single-use PREPARE_SUBMISSION grant, lowercase capability `freeze_prepared_submission`, max_uses=1, current issuer authority, mandatory `requires_current_author_consent=true`, complete checked reviews and B17 result binding. |

Additionally enforce B15's fixed package/authorship context and B16's current
consent and withdrawal rules. Recheck current caller credential/binding/actor,
project entitlement, issuer authority and scheduled expiry after waits and before
commit. No new novelty assessment, Decision purpose or review taxonomy is added.

## 4. Proposed commands, closed DTOs and historical readback

`PreparedSubmissionService.freeze_prepared_submission(principal, command)` returns
B13's typed `ConsumptionReadback[PreparedSubmissionFreezeResult]`. The command
fields are fixed in §11.3; `result_id` is the existing package UUID. It creates no
second package. Current OWNER/RESEARCHER may invoke it through the same Human/Agent
boundary; that permission cannot substitute for direct HUMAN consent/approval.

Retain `get_prepared_submission`, `get_prepared_submission_history`,
`preview_prepared_submission`, `get_author_consent` and own-consent reads. Frozen
readback adds actual hashes/time and derives grant/receipt IDs from the concrete
consumption relation. General readers retain B15's effective project roles;
offboarding retains only B16's narrow own-consent path. No API/CLI routes here.

Frozen reads separate saved material from current diagnostics. Recompute the
saved manifest using stored consent FKs, even after withdrawal; never replace
those FKs with current heads. Preview on a sealed package reports that saved
manifest/hash, not a newly projected consent set. PREPARED preview remains B15's
transient candidate and is never persisted as a package hash.

## 5. Schema and literal hash proposal — one forward migration

Reuse the four registered B15 tables and `approval_grant_consumptions`. No new
canonical table, head pointer, token, lock service or package-grant association.
Use §12.1's forward checks/guards, retaining all immutable history and concrete FKs.

Manifest hash: use existing `domain/prepared_submission.py:manifest_material`
with exact manuscript/snapshot refs and all stored items sorted by category text
then ordinal. Package content material is exactly:

```json
{"type":"PreparedSubmissionVersion","material_version":1,"publication_id":"<uuid>","manuscript_version":"<exact ref>","authorship_snapshot":"<exact ref>","package_manifest_hash":"<digest>"}
```

Use Hash R2 15's `canonical-json-v1`/`sha256-cjson-v1`, NFC text and lowercase
UUID/digest conventions. No status, row_version, event, clock, grant or receipt
enters package hash material. Draft and never-frozen withdrawn hashes stay SQL
NULL. Freeze fills both hashes and finite `frozen_at` together; later lifecycle
changes preserve all three exactly. The two published R2 package vectors remain
`1378737b…d40d46` (manifest) and `2ffff00e…b2d32d` (content).

Enable PREPARE_SUBMISSION in `ApprovalService._evaluate_in_uow`'s current
dependency-availability predicate and the corresponding SQL gate branch. It now
admits only release/READY for evaluation. Evaluate manuscript facts through the
existing B12 gate and package heads through the explicitly selected freeze
context; keep B16's manuscript-scoped withdrawal staling. No package means no
invented withdrawal cause.

B13 request material remains R3 v1: actual actor/project/grant, uppercase command,
exact manuscript ref, package result ID, expected manifest digest and sorted
complete checked review IDs. Derive the saved expected digest from the sealed
package in `b13_request_hash`; do not add a competing persisted request document.

## 6. Error contract — existing categories only

Use §11.2 exactly. Architecture 12's conceptual SUBMISSION_PACKAGE_INVALID is not
an implemented ErrorCode; do not emit it or add HASH_MISMATCH ad hoc. Preserve
B13's temporal/terminal precedence and distinguish corrupt saved history from
current staleness. Entitlement precedes detailed missing/conflict disclosure.

## 7. Transactions, concurrency and failure recovery

One local effect equals one transaction. In order: verify gates, heads and
expected digest; preallocate receipt/event IDs; insert consent items; supersede
any older FROZEN package; seal target and append package events; insert B13
receipt; mark grant CONSUMED with its terminal event. Use one observed DB time for
freeze, consumption and their events. Force deferred constraints before final
advancing-clock authorization/expiry checks. Any failure rolls everything back,
including supersession. Never stale/expire grants as a side effect of denied
freeze; B13 maintenance/B16 withdrawal own those changes.

Same-key replay uses current read entitlement and the saved normalized request,
including original actor, grant, package, expected digest and review set. Exact
replay returns the saved result after grant expiry, role change or later consent
withdrawal if the caller can still read. Different authorized material conflicts;
no second receipt/event/transition. Recover uncertain commit with the same key;
do not allocate another key or retry an uncertain commit automatically.

Retry only SQLSTATE 40001/40P01, three total fresh-UoW attempts without delay or
external call. Reacquire every lock, snapshot, clock and verifier. No business
conflict, unique-predecessor loss or timeout retry. Do not describe SSI as snapshot
refresh: initial table locks precede snapshot creation; a later conflicting change
requires serialization failure/retry or a fresh READ COMMITTED statement.

Withdrawal first: package's head becomes WITHDRAWN and related unused preparation
grants become STALE atomically, so freeze fails. A valid PREPARED regrant plus a
new eligible grant may permit a later freeze. Freeze first: subsequent direct
author withdrawal appends B16 history, preserves package material and CONSUMED
grant, and makes derived package validity STALE immediately. No regrant restores
a frozen package: new package, consents and approval are required.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 defines test paths and cases. Prove complete graphs, ordinary-role SQL
defenses, both commit orders with observed PostgreSQL blocking, exact replay and
rollback after every effect stage. Availability flags, mocks, forged READY state
and plausible hashes are not G7 evidence. All fixtures use owning commands and
real PostgreSQL 18.x; no SQLite or disabled trigger substitute.

## 9. Acceptance criteria and evidence boundary

Require approved contract and execution scope, forward/populated migration and
roundtrip evidence, package/receipt/hash verification, all six gates, current
consent, races, atomic rollback, lock-free reads/replay and the G7 suffix. Retain
B04/B05/B11–B16/B14a/B14r regressions and Phase 1 vectors. No open P0/P1 finding.
Report exact focused commands/counts, PostgreSQL version, skips and blockers.
The loop owns the whole-suite check; this agent must not run it. Small benchmark
samples are functional evidence, never large-profile performance acceptance.
Stop after authorized B17 evidence; no full PR2-17, G7 or Phase 2 gate claim from
this draft or from dependency source presence alone.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Prepared package | Existing PreparedSubmissionVersion, intended for possible submission; never proof of sending. |
| Current head | Unique consent row with no successor for package/author/PREPARED_PACKAGE. |
| Frozen consent | Exact GRANTED head FK captured at freeze, retained even after a successor withdrawal. |
| Manifest occurrence | One sealed placement occurrence or authored consent item; repeated targets remain repeated occurrences. |
| Closure | Exact transitive material/hash/validity dependencies, not current pointers or a hash-shaped string. |
| Grant / receipt | Authorization capability / immutable record of its single concrete local effect. |
| Saved history / current validity | Immutable facts of freeze / timestamped present usability; they can differ. |
| SRE | PostgreSQL SHARE ROW EXCLUSIVE table mode used by B13/B16 for Publication coordination. |
| G7 suffix | Real Application trace from READY through package preparation, consent and freeze; novelty remains separate. |

## 11. Decisions taken in this draft

### 11.1 Scope, lifecycle and replay decisions

| Choice | Adopted decision |
| --- | --- |
| Lifecycle | PREPARED→FROZEN or WITHDRAWN; FROZEN→SUPERSEDED or WITHDRAWN. SUPERSEDED/WITHDRAWN terminal. No restore/reset. |
| One current frozen package | Partial unique Publication index; newer version_number freeze atomically supersedes older FROZEN. Reject freezing an older/equal version while a newer FROZEN exists. No current-package pointer. |
| OWNER withdrawal | Extend B15 exact actor/reason terminal replay to frozen packages. Requires OWNER, preserves bytes and consumed history; no author-consent mutation or grant maintenance. |
| Consent after freeze | Direct withdrawal allowed even after supersession/OWNER withdrawal; GRANTED successors only on PREPARED. No requirement that an offboarded author regain project membership. |
| Read validity | INVALID for corrupt material (formal reads fail); STALE for withdrawn captured consent, package withdrawal or upstream stale facts; VALID for intact usable frozen closure; NOT_FROZEN for intact PREPARED. Supersession alone does not invalidate historical material. INVALID takes precedence over STALE. |
| Missing bytes | Formal verification fails FROZEN_REFERENCE_REQUIRED. Ordinary diagnostics may retain B15 DEPENDENCY_UNAVAILABLE without pretending evidence is valid. |
| Consumption | Extend existing B13 helper/receipt and v1 concrete result union, preserving release/READY behavior. No nested lifecycle command or separate commit. |
| Transport | Application only, matching B15/B16. Pin future error mappings now; no route/CLI exposure in B17. |

### 11.2 Pinned error mappings

These match `src/researchbase/api/errors.py:_STATUS` and
`src/researchbase/cli/errors.py:CLI_EXIT_CODES` at drafting time.

| Code | HTTP | CLI exit | B17 use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong/extra field, strict type, enum, digest or bound. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing or invalid trusted credential. |
| FORBIDDEN | 403 | 3 | Missing project role/access or offboarding disclosure. |
| NOT_FOUND | 404 | 3 | Entitled exact record absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Nonindependent required participant. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Wrong purpose/capability/target/result tuple. |
| DECISION_BASIS_INVALID | 409 | 4 | Wrong affirmative basis or incomplete checked review set. |
| APPROVAL_GATE_FAILED | 409 | 4 | Missing READY/reviews/current consent or applicable OPEN blocker. |
| APPROVAL_TARGET_STALE | 409 | 4 | Selected manuscript/hash or current target validity changed. |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Existing purpose rejection fence. |
| GRANT_INVALID | 409 | 4 | Expired, consumed, revoked or otherwise unavailable grant. |
| GRANT_STALE | 409 | 4 | Stored/effectively stale grant or lost issuer authority. |
| INVALID_STATE_TRANSITION | 409 | 4 | Withdrawn/superseded package, wrong version order or invalid new transition. |
| VERSION_NOT_FROZEN | 409 | 4 | Required version lacks frozen material. |
| IMMUTABLE_RECORD | 409 | 4 | Attempted frozen material/history mutation. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same command key with different normalized request. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted retry budget, timeout or competing single-use consumption. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Exact retained bytes unavailable. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Hash mismatch, malformed chain or inconsistent saved graph. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK failure. |

Unexpected errors retain sanitized INTERNAL_ERROR, HTTP 500 / CLI exit 1.
Expected preview/digest drift uses CONCURRENT_MODIFICATION; it leaves no receipt.
Corrupt saved hashes use PROVENANCE_CLOSURE_VIOLATION instead of drift. No raw SQL,
credential, evidence bytes or other-author details enter error envelopes.

### 11.3 DTO fields, Python types, limits and enums

All DTOs are frozen closed dataclasses, strict `uuid.UUID` (canonical UUID strings
at future transport boundaries); reject extra attributes/keys and bool-as-int.
Use B13's 1..100 checked-review limit, superseding the older PR2-17 proposal's
1,000-review suggestion. Normalize the duplicate-free set by UUID text order.

```python
# New command; every field required, no defaults.
FreezePreparedSubmissionCommand:
    command_key: UUID
    project_id: UUID
    grant_id: UUID
    result_id: UUID                       # existing prepared package
    expected_package_manifest_hash: str   # exactly 64 lowercase hex characters
    checked_review_ids: tuple[UUID, ...]   # 1..100 distinct, complete sealed set

# New closed saved v1 result; follows the existing B13 three-key result pattern.
PreparedSubmissionFreezeResult:
    prepared_submission_version_id: UUID
    consumption_id: UUID
    command: Literal["FREEZE_PREPARED_SUBMISSION"]  # derived, init=False
```

Outer `ConsumptionReadback` retains its existing fields/types, including
`id`, `grant_id`, `command_key`, `project_id`, `actor_id` UUIDs,
`consumed_at: datetime`, `request_hash: str`,
`hash_scheme: str` fixed `sha256-cjson-v1`, `result_dto_version: int` fixed 1,
`result: PreparedSubmissionFreezeResult`, `command: str`,
`checked_review_ids: tuple[UUID, ...]`, and the existing three nullable concrete
result UUID fields. For this branch only `result_prepared_submission_version_id`
is nonnull. Widen the generic result bound to include the new result. The current
outer DTO has no historical/evaluation fields; current diagnostics remain in
package/grant readbacks. Do not put mutable validity or package status in the
immutable three-key saved JSON result.

Extend existing `PreparedSubmissionReadback` fields in place:
`package_manifest_hash/content_hash: str | None`, `frozen_at: datetime | None`,
`grant_id/consumption_id: UUID | None`. UUID/int/tuple/reference/time fields already
in B15 retain their types. `row_version` is a positive strict int, `version_number`
a positive int. Timestamps are finite UTC-aware `datetime`; hashes are lowercase
64 hex, scheme fixed. Extend event `prior_status` to `PackageStatus | None`.

Closed literals: PackageStatus PREPARED/FROZEN/SUPERSEDED/WITHDRAWN;
Validity NOT_FROZEN/VALID/STALE/INVALID. Keep B15 reason literals and add
CONSENT_WITHDRAWN. Keep category FIGURE/TABLE/CITATION/CLAIM/CONCLUSION/AUTHOR_CONSENT,
consent GRANTED/WITHDRAWN and sole scope PREPARED_PACKAGE. No new grant status.
Authors 1..100; total manifest ≤10,000 including consent; each category ordinals
0..N-1 within 0..9999. Consent history is uncapped and iteratively verified.
Withdrawal reason remains NFC, nonblank, 1..10,000 characters. No caller-supplied
actor, status, clock, receipt ID, content hash, consent head or row_version.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch with types and constraint names

Proposed file `migrations/versions/0065_b17_prepared_package_freeze.py`,
`down_revision='0064_b14_publication_ready'`; recheck actual head before building.
Use synchronous PostgreSQL 18.x SQL, existing named guards and immutable records.
All existing column types remain: UUID IDs/FKs, INTEGER versions/ordinals,
VARCHAR(16) status, CHAR(64) hashes, TIMESTAMPTZ clocks, VARCHAR(32) scheme.

```sql
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_status;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_status
 CHECK (status IN ('PREPARED','FROZEN','SUPERSEDED','WITHDRAWN'));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_row_version;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_row_version
 CHECK ((status='PREPARED' AND row_version=1)
     OR (status='FROZEN' AND row_version=2)
     OR (status='SUPERSEDED' AND row_version=3)
     OR (status='WITHDRAWN' AND row_version IN (2,3)));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_hash_state;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_hash_state
 CHECK ((status IN ('PREPARED','WITHDRAWN') AND row_version IN (1,2)
          AND package_manifest_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL)
     OR (status IN ('FROZEN','SUPERSEDED','WITHDRAWN')
          AND (status<>'WITHDRAWN' OR row_version=3)
          AND package_manifest_hash IS NOT NULL AND content_hash IS NOT NULL
          AND package_manifest_hash ~ '^[0-9a-f]{64}$'
          AND content_hash ~ '^[0-9a-f]{64}$'
          AND frozen_at IS NOT NULL AND isfinite(frozen_at)));
CREATE UNIQUE INDEX uq_b17_frozen_publication
 ON prepared_submission_versions(publication_id) WHERE status='FROZEN';
ALTER TABLE prepared_submission_manifest_items DROP CONSTRAINT ck_b15_manifest_s2;
-- Retain ck_b15_manifest_target XOR/category, fk_b15_manifest_consent
-- (package,id composite), uq_b15_manifest_position and ordinal bounds.
ALTER TABLE approval_grant_consumptions ADD CONSTRAINT fk_b17_result_package
 FOREIGN KEY(result_prepared_submission_version_id)
 REFERENCES prepared_submission_versions(id) ON DELETE RESTRICT
 DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX uq_b17_package_consumption
 ON approval_grant_consumptions(result_prepared_submission_version_id)
 WHERE result_prepared_submission_version_id IS NOT NULL;
```

Replace `ck_b15_event_transition`: retain initial NULL→PREPARED (reason NULL),
PREPARED→WITHDRAWN (reason required), add PREPARED→FROZEN and FROZEN→SUPERSEDED
(reason NULL), FROZEN→WITHDRAWN (reason required). Preserve actor/time/reason
checks and `uq_b15_package_event`. Replace `ck_b13_result_tuple` with its two
0064 alternatives unchanged plus FREEZE_PREPARED_SUBMISSION with only
`result_prepared_submission_version_id` nonnull. Keep `uq_b13_command_key` and
`uq_b13_consumption_grant`, result DTO version SMALLINT=1 and closed JSONB
projection; JSONB is an existing receipt projection, not the semantic owner.

Forward-replace functions below, preserving old branches and exact downgrade
predecessor definitions. Use fixed `search_path=pg_catalog,public,pg_temp`.

| Guard/function | Required forward behavior |
| --- | --- |
| `b15_preheld` | Preserve the READ COMMITTED/B15 Publication SHARE branch. Add a separately proved SERIALIZABLE freeze branch delegating to `b17_preheld`, accepting Publication SRE directly; do not require or upgrade Publication SHARE in freeze. Pure historical material verification must not invoke write-preheld checks. |
| `b15_package_guard`, `b15_capture_withdrawal` | Preserve PREPARED insertion/OWNER withdrawal; add only allowed frozen transitions, exact +1 row_version and sealed-field equality. Freeze alone may fill hashes/time. No DELETE, retarget or material edit. Supersession requires higher-number same-Publication successful freeze in this transaction; OWNER withdrawal does not write consent/grant history. |
| `b15_manifest_guard`, `b15_manifest_complete` | Preserve non-consent insertion with new PREPARED parent; consent INSERT only during authorized freeze. No UPDATE/DELETE. Check projection multiplicity, contiguous ordinals, cap, distinct authored consent coverage, same-package FK and current heads at admission. Historical verification thereafter checks captured GRANTED rows, not their continued head status. |
| `b15_package_events` | Validate complete exact event chain, row_version, actor/time, single freeze event and matching B13 receipt; sealed hashes retained after supersession/withdrawal. Do not let historical event verification rerun current consent/authority gates. |
| `b13_request_hash`, `b13_verify_receipt` | Add package result, exact manuscript target/hash, saved manifest digest, full sealed review set and exact three-key result projection. Complete graph requires CONSUMED grant/event and same-actor/time package freeze event; receipt time equals frozen_at. Preserve historical validity when consent later withdraws. |
| `b13_consumption_guard`, `b13_release_gate`, `b13_complete`, `b13_stale` | Enable only preparation freeze tuple, current-consent condition and all six admission gates. Extend 0064's observed-effect-time branch to freeze: preserve the validated same-transaction package event/frozen_at time, rather than overwriting consumed_at as the release branch does. Preserve release/READY checks, B16 consent-cause exceptions, expiry/issuer semantics and frozen history verification. Keep manuscript-scoped lifecycle evaluation and B16's exact withdrawal resolver. Evaluate current author heads only with the explicitly selected package in the freeze admission helper; do not select an arbitrary latest package or fabricate withdrawal when no package is selected. |
| New `b17_preheld`, `b17_verify_package`, `b17_complete_graph` | Require §12.2 modes/isolation before new effect statements; verify registered package/hash/event/receipt graph in both directions and current facts only for a new freeze. No GUC/token asserted by a caller can replace relational proof. |

Following 0042's parent-and-child pattern, add constraint triggers
`b17_complete_package` AFTER INSERT OR UPDATE on prepared_submission_versions,
`b17_complete_item` AFTER INSERT on prepared_submission_manifest_items,
`b17_complete_event` AFTER INSERT on prepared_submission_events and
`b17_complete_consumption` AFTER INSERT on approval_grant_consumptions.
All are FOR EACH ROW, DEFERRABLE INITIALLY DEFERRED, executing
`b17_complete_graph()`. Verify the final graph even when children are absent.
Update existing B15 deferred verifiers to accept the same graph; adding a parallel
trigger while old guards still forbid freeze is insufficient. Existing B16
triggers continue to validate post-freeze withdrawal and unused-grant staling.
No direct-SQL test may bypass gates by disabling triggers or forging authority.
Normalize `uq_b17_frozen_publication`/`uq_b17_package_consumption` competing
writes as CONCURRENT_MODIFICATION; FK failures as REFERENTIAL_INTEGRITY_ERROR;
use existing P17F2 for corrupt graph/hash, P15S1 for immutable edits and existing
B13/B09 gate SQLSTATE categories for their corresponding §11.2 codes. Retain
SQLSTATE 40001/40P01 retry classification independently of business codes.

Upgrade first locks affected tables, verifies existing package/receipt graphs,
then replaces guards/constraints. Downgrade refuses any frozen-origin package,
consent manifest item or package receipt before mutation. On compatible data,
restore all predecessor functions/checks verbatim and preserve existing history.
Test clean install, populated upgrade and catalog roundtrip to 0064 and back.

### 12.2 Exact lock order and transactions

Freeze uses B13's SERIALIZABLE UoW; this is the architecture R3 effect requirement.
Ordinary preparation/withdrawal/consent writes retain READ COMMITTED. For those
snapshot-consistent writes, as in decision_repository.py/novelty_repository.py,
the SHARE inventory is FIRST SQL, before SET LOCAL, SELECT or advisory calls.
Do not change B13 consumption to READ COMMITTED or make a preliminary SELECT to
choose the isolation/prefix. Configure isolation/autoflush without SQL.

Pin a literal `B17_SNAPSHOT_TABLES` in the adapter and migration, equal to this
lexically sorted B16 inventory; do not dynamically import a private list:

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

Freeze prefix, before any snapshot query: (1) `LOCK TABLE <inventory sorted>
IN SHARE MODE` FIRST; (2) `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`;
(3) `LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE` (B13's
freeze-only W addition); (4) `LOCK TABLE approval_decisions,
approval_request_reviews,approval_requests IN SHARE MODE`. Then SET LOCAL
lock_timeout='10s', statement_timeout='30s'. Initial-wait timeouts must already be
bounded by connection/server configuration; later SET LOCAL cannot bound them.
Never SHARE-lock an output table then upgrade. Consent/manifest/grant/event
outputs receive no SHARE lock; package/Publication exclusion protects consent
phantoms, including authors without any chain and empty grant ranges.

| Command | Exact continuation after its prefix |
| --- | --- |
| freeze_prepared_submission | Advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, key `b13:consume:{command_key}`; plain project-confined package/grant/request routing; scope advisory `pr216:scope:{project_id}:PREPARE_SUBMISSION`; exact manuscript FOR UPDATE; owning Publication FOR UPDATE; target package FOR UPDATE; other affected FROZEN packages FOR UPDATE by UUID; all snapshot author chains FOR UPDATE by Actor UUID then consent UUID; request FOR SHARE; selected grant FOR UPDATE (all grants UUID-sorted if a helper needs more than one); reread package, chain heads, receipt absence and grant/request graph; authorize and verify §3 gates, bytes/hashes, complete checked reviews and expected digest; fresh clock; perform §7 atomic effect; force constraints; final fresh caller/issuer/expiry checks; commit. |
| record_author_consent, all states | Retain B16 FIRST inventory SHARE→Publication SRE→approval SHARE, READ COMMITTED, then timeouts; advisory `b15:consent:{id}`; private routing; pr216 preparation scope; manuscript→Publication→package FOR UPDATE; own chain by UUID; reread heads/identity after waits. Withdrawal resolves all exact related ACTIVE grants and locks them UUID-sorted after chains, including expired-ACTIVE; B16 consent/event/staling commit atomically. Root/regrant remains PREPARED only. |
| withdraw_prepared_submission | Retain B15 FIRST inventory including publications SHARE, READ COMMITTED, then timeouts; advisory `b15:withdraw:{package_id}`; private routing; manuscript→Publication→package FOR UPDATE; reread history; exact terminal replay exits to read path; otherwise fresh OWNER gate, PREPARED/FROZEN→WITHDRAWN + event, force constraints, final OWNER check, commit. No consent/grant locks or changes. |
| prepare_submission | Unchanged B15 FIRST SHARE including publications, READ COMMITTED; timeouts; `b15:prepare:{id}` advisory; manuscript→Publication FOR UPDATE; saved UUID reread; full admission, insert package/items/event; deferred/final checks; commit. |
| get package/history/preview/consent/own consent, receipt and completed replay | One REPEATABLE READ READ ONLY UoW; plain authorization and exact parent/children/chain/receipt reads, saved hashes then timestamped current diagnostics; final fresh credential/entitlement check. No explicit table, advisory, FOR UPDATE/FOR SHARE locks, writes, maintenance or nested locking helper. |

B16's later-freeze chain-before-grant order supersedes B13 draft §12.2's older
future-freeze row. The accepted B13 release/READY sequences remain unchanged.
B09 issuance and B13 lifecycle hold Publication SRE before scopes, excluding
freeze/consent before range selection; B11/B12/B14a/B14r and B15 preparation/OWNER
withdrawal hold Publication SHARE and finish before freeze gets SRE. B14 READY
uses its accepted B13 SRE prefix. Author-chain mutation cannot pass B16's SRE
while freeze holds it. No dependency writer may start by locking a grant and
then enter this prefix. Older target-first scientific writers can deadlock;
retain bounded whole-UoW 40P01 recovery and test both orders.

Every blocking wait precedes a fresh `clock_timestamp()` authorization/expiry
check. SERIALIZABLE inputs are protected before snapshot creation; reread only
protected facts and retry serialization failures. Force `SET CONSTRAINTS ALL
IMMEDIATE` before the final clock check so FK/trigger waits occur first. Repeat
the final check if any subsequent required wait occurs. No external call in the
transaction; local retained ArtifactStore byte verification follows B04/B15.

### 12.3 Ordered build steps and real file paths

1. Add the §12.1 forward migration. Use `migrations/versions/0042_pr2_15_minimal_decision.py`
   and 0060–0064 as guard/rollback patterns. Prove predecessor catalog preservation.
2. Extend `src/researchbase/domain/prepared_submission.py` with package content
   material and lifecycle/validity literals; extend `src/researchbase/domain/approval.py`
   with the concrete freeze result and decoder union. Keep existing payloads exact.
3. Extend `src/researchbase/application/prepared_submission.py` with the command,
   orchestration, frozen readback and OWNER withdrawal; extend
   `src/researchbase/application/approval.py` with B13-owned in-UoW consumption and
   entitled replay comparison. Explicitly share pure/in-UoW verifiers, not public
   service transactions. Update `src/researchbase/application/ports.py` with typed
   operations; preserve common principal and accounting boundaries.
4. Extend `src/researchbase/persistence/prepared_submission_repository.py` for the
   literal prefix, sorted chain/package locks, seals and plain frozen reads;
   `src/researchbase/persistence/approval_repository.py` for concrete receipt/hash
   verification; `src/researchbase/persistence/uow.py` for narrow named constraint
   mappings and typed result normalization. Preserve strict SQLSTATE retry flags.
   Existing factory wiring supplies both repositories; add no transport/dependency.
5. Build §12.4 fixtures through accepted dependency commands. Update only the
   relevant consumer scenario/benchmark inventories after behavioral evidence.
6. Run static, unit/architecture and focused PostgreSQL checks, report exact
   results and unresolved blockers, obtain review with no P0/P1, then stop.

### 12.4 Test artifacts and required cases

Create `tests/integration/phase2/b17_fixtures.py` using `b15_support.py`, B14
fixtures and real Application commands: manuscript freeze, exact entry/reviews,
readiness Decision/approval/consumption, preparation Decision/approval, attribution,
package and direct consent. No manual READY update or forged consumption. Use two
independent engines/backend PIDs and DB-derived expiry for races.

| Proposed file | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b17_freeze_contract.py` | All strict DTO fields/limits, set normalization and closed result decoder; preserve old result versions; exact mappings in §11.2; lifecycle/validity precedence. |
| `tests/unit/phase2/test_b17_freeze_hash_vectors.py` | Independent literal R2 package vectors and R3 freeze request preimages; consent order, repeated placements, wrong member/hash, null drafts and unchanged Phase 1 vectors. |
| `tests/integration/phase2/test_b17_package_freeze.py` | Full happy path; independently fail each of six gates; wrong project/manuscript/snapshot/grant/capability; READY grant substitution; review omission/addition; missing/unlisted/withdrawn consent; chain corruption, stale scientific facts, missing/corrupt document/evidence; expected digest drift; zero partial writes. |
| `tests/integration/phase2/test_b17_package_history.py` | Exact sealed reads/restart; newer freeze supersedes older atomically, older-version denial; OWNER withdrawal before/after freeze; captured consent remains exact after withdrawal; STALE diagnostics, no regrant resurrection; historical supersession retains usable material; preview never replaces saved heads. |
| `tests/integration/phase2/test_b17_freeze_replay.py` | Matching key/material before/after expiry, withdrawal and role loss with read entitlement; review permutations match; altered actor/grant/result/digest/reviews conflict; lost reader denies; uncertain-commit same-key recovery; exactly one receipt/event and no read locks, including nested helpers. |
| `tests/integration/phase2/test_b17_freeze_schema.py` | Catalog names/types/NULL rules/FKs; clean and populated upgrade; compatible roundtrip and frozen-history downgrade refusal; normal-role SQL rejects direct seal without receipt/grant/event/consent, missing-child deferred graphs, foreign consent, duplicate FROZEN Publication, extra/late manifest items, fake event, mixed result DTO and mutation of frozen fields. Retain B13 release/READY and B16 staling branches. |
| `tests/integration/phase2/test_b17_freeze_concurrency.py` | Observed waits and both orders: withdrawal/freeze, OWNER withdrawal/freeze, two freezes/supersession, same grant/different key, same key, grant issuance/withdrawal including empty ranges, grant maintenance/freeze, authority revocation/scheduled expiry, Issue INSERT/disposition and scientific invalidation. Failure after each consent item/seal/supersession/event/receipt/grant update/deferred check rolls back all. Exactly three fresh attempts for 40001/40P01; no timeout/business retry; lock-free reads continue under held writer locks. |
| `tests/architecture/test_b17_boundaries.py` | Application/ports/UoW path, pure Domain and no ORM DTO; literal inventories and FIRST-SQL modes; no table upgrades, grant-before-chain or nested transaction; all reads/replay lock-free; no send/new schema/novelty gate; six gates cannot be bypassed by authority. |
| `tests/integration/phase2/test_pr2_19_package_freeze.py` | New G7 suffix using owning commands from READY through preparation/current consent/freeze, then withdrawal→STALE with immutable history and receipt; failed freeze leaves no partial state; no external-send record. |

Extend `tests/integration/phase2/pr2_19_support.py` and
`test_pr2_19_dependencies.py` only for demonstrated B17 subcases; retain historical
inventory and unrelated novelty/other blockers. Extend `tests/e2e/test_pr2_20_benchmark.py`
with named package first-freeze, exact replay, consent-denied and frozen-read
cases using its existing evidence/profile mechanism; align
`tests/unit/phase2/test_pr2_20_inventory.py` and evidence case validation where
required. First-freeze samples need fresh packages/grants outside timed calls;
replay uses the exact saved key. Record profile, fixture counts, warmups,
repetitions, concurrency, latency and failures under the existing contract.
Do not invent a new performance threshold or claim a large-profile PASS from CI.

After implementation, run new B17 tests plus focused B04/B05/B11/B12/B13,
B14a/B14r/B14, B15/B16 and G7/benchmark regressions. Static commands:
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`;
unit/architecture: `uv run pytest tests/unit tests/architecture --tb=short`.
Use explicit PostgreSQL file lists, record actual counts/version and all failures.
The loop runs the whole suite; do not run it here.

### 12.5 Not in this slice

- Actual SubmissionVersion/SubmissionRecord, venue connector, dispatch, receipt
  from a publisher, ExternalEffect, publication release or network send.
- Representative consent, legal signatures/PKI, authorship disputes, account
  recovery, general project access for offboarded authors or evidence downloads.
- New top-level schema, persisted consent head/current-package pointer, arbitrary
  JSON provenance owner, background staling, queue, scheduler or propagation engine.
- New novelty outcome/basis or approval gate; full G7/PR2-17/Phase 2 acceptance,
  large-profile performance acceptance and unrelated backlog implementation.
- API/CLI commands/routes, runtime dependency additions or changing dependency
  governance policy merely to make a B17 fixture pass.

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted for approval |
| --- | --- |
| Admit the full remaining local lifecycle? | Freeze plus atomic newer-version supersession and frozen OWNER withdrawal; no superseded-to-withdrawn transition or restore. |
| Approve exact integration choices? | B13 SERIALIZABLE consumption, B16 prefix/chain-before-grant, concrete existing receipt result and deferred graph checks; no new canonical table or result material version. |
| Approve consumer evidence scope? | G7 package suffix and bounded benchmark cases only; retain unrelated blockers and require separate execution authorization. |

These choices are proposed, not delegated to the implementer. An override requires
corresponding body edits before approval; this DRAFT authorizes no implementation.

## 14. Documentation verification note

Only this proposal is changed. Proposed B17 behavior/tests are not implemented or
verified by dependency regression runs. Actual drafting-check commands and observed
results will be recorded below; no whole-suite or phase-gate PASS is implied.


Drafting checks used this exact prefix for every `uv` command (the existing shared
virtualenv; no sync/dependency changes):

```sh
UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv UV_CACHE_DIR=/tmp/researchbase-b17-uv-cache
```

| Command after that prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | Exit 0: All checks passed. |
| `uv run --no-sync ruff format --check .` | Exit 0: 699 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0: 0 errors, 0 warnings, 0 informations. |
| `uv run --no-sync pytest tests/unit tests/architecture -o addopts='' -q --tb=short > /tmp/researchbase-b17-unit.log 2>&1` | Exit 1: 5,429 passed, 4 failed, 14 errors, 9 warnings in 63.93s. Not PASS. |

The four failures are HG1 runner Unix-socket operations denied with
`PermissionError: [Errno 1] Operation not permitted`. Fourteen PR2-19 architecture
setups require explicitly configured `RB_TEST_ADMIN_URL`, absent in the inherited
environment. These outcomes are recorded as failures/errors, not waived tests.

Exact initial focused PostgreSQL command, after the same prefix:

```sh
uv run --no-sync pytest tests/integration/phase2/test_b13_grant_consumption.py tests/integration/phase2/test_b13_grant_schema.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b15_package_schema.py tests/integration/phase2/test_b15_package_consent.py tests/integration/phase2/test_b16_consent.py tests/integration/phase2/test_b16_concurrency.py -o addopts='' -q --tb=short > /tmp/researchbase-b17-postgres.log 2>&1
```

Result: exit 1, **1 failed, 115 errors in 1.67s**. Required DATABASE_URL and/or
RB_TEST_ADMIN_URL were absent; database assertions did not execute.
A configured retry used the repository's documented disposable local DB URLs:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_b13_grant_consumption.py tests/integration/phase2/test_b13_grant_schema.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b15_package_schema.py tests/integration/phase2/test_b15_package_consent.py tests/integration/phase2/test_b16_consent.py tests/integration/phase2/test_b16_concurrency.py -o addopts='' -q --tb=short -x > /tmp/researchbase-b17-postgres-configured.log 2>&1
```

Result: exit 1, **1 setup error in 0.67s**, stopped at first error. PostgreSQL
TCP connections to localhost port 5432 were denied with `Operation not permitted`.
Remaining selected cases did not run on retry; server version could not be
verified. No PostgreSQL PASS or B17 implementation evidence is claimed.

A focused `PYTHONPATH=src uv run --no-sync python` script under the same prefix
checked all 17 Markdown local links (0 missing) and compared all 20 §11.2 rows
with imported `_STATUS`/`CLI_EXIT_CODES` (0 mismatches). `git diff --check`
exited 0. The added-file whitespace check also reported no errors.
Only this requested draft is added. No whole-suite run, commit, push or branch
creation occurred. The owner's loop supplies the subsequent whole-suite evidence.
