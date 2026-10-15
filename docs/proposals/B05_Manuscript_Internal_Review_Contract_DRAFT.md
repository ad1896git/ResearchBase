# B05 Manuscript Internal Review Contract — DRAFT

**Status: APPROVED by owner 2026-10-15 — first slice authorized for implementation**

## Start here (for the implementer)

B05 records an independent HUMAN evaluation of one exact frozen manuscript and
its initial OPEN issues. It also supplies a complete, verified manuscript review
basis to later governance commands. Review never makes a manuscript READY or
changes scientific truth. This is the review prerequisite of G6/F5, not their
end-to-end acceptance.

Build in this order after owner approval **and separate execution authorization**:

1. Reconcile the migration head, accepted PR2-14 base and B04 freeze dependency
   (§1); add only the review guards described in §12.1.
2. Extend exact manuscript target verification and immutable review hashing
   (§§3–5, 11); preserve the Claim/Conclusion branches.
3. Extend Application create/read and add the same-UoW complete-basis helper
   (§4), through repository ports with the write lock order and lock-free read
   protocol (§12.2).
4. Add migration, authority, replay, phantom and rollback cases (§12.4).
5. Run the named checks, retain actual results and stop. No readiness, Decision,
   Approval or Issue-disposition implementation belongs here (§12.5).

Read §§1–4 first; §10 is a glossary, §11 pins decisions and §12 is the build plan.
The owner override register (§13) identifies proposed refinements needing approval.
This proposal is not an architecture amendment, execution pack or acceptance record.

Five review rules:

1. Recompute the exact B04 seal and scientific closure; no DRAFT, current-pointer
   substitution, hash-shaped string or earlier trace result can satisfy review.
2. Reviewer is an authenticated HUMAN with current REVIEWER/OWNER authority,
   independent of the manuscript and its material provenance authors.
3. Preserve every exact-target review, including unfavorable recommendations and
   zero-issue reviews; never accept a caller-selected favorable basis.
4. Write commands lock the exact manuscript before discovering reviews/issues,
   including normal SQL insertion paths; recheck credential/role time after waits.
   Exact-ID reads use one lock-free REPEATABLE READ, READ ONLY snapshot.
5. OPEN/BLOCKING anywhere in the exact-target review set fails the later gate.
   Review, Decision, Approval, revision and readiness remain separate facts.

## 1. Purpose, authority and inspected baseline

| Source | Rule carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–12 | Deterministic facts precede authority; exact frozen closure; immutable history; Review ≠ Decision ≠ Approval. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23; [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), governance registry | Existing InternalReviewRecord, ReviewIssue and events suffice; concrete references, focused R2/R3/R4 precedence and bounded purposes. |
| [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 28 | Shared Application boundary, synchronous transaction, exact references, stable errors and preserved Phase 1 behavior. |
| [Phase 2 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19, 33.3, 37, 42.6, F5, PR2-14 | Immutable evaluation plus issues; frozen manuscript review/re-review; blocking issues prohibit ready approval. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§2, 4–7; [Fields 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), review/issue contracts | Exact nonnull target hash, independent reviewer, append-only issue history and typed FKs. |
| [Closure R2 14](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md); [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), review template/vector; [Ownership R2 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md) | Scientific closure remains with owning services; literal hashes and project-scoped access, including globally owned sources. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §1; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §§1, 5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Exact independent manuscript review prerequisite for READY_FOR_SUBMISSION; finite complete basis; fresh advancing DB time; approval consumes a distinct grant. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 16, 18–19 | Application writes, independently reconstructed review inputs and evidence before completion. |

Inspected baseline:

- [InternalReviewService](../../src/researchbase/application/internal_review.py)
  accepts CLAIM_VERSION and SCIENTIFIC_CONCLUSION_VERSION, validates current
  closure and target-author independence, uses deterministic request IDs, and
  stores initial issues atomically. `_verify` and `_view` currently assume those
  two target kinds. They must dispatch explicitly for manuscript support.
- [0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py)
  already has `manuscript_version_id UUID`, three other concrete target FKs,
  `ck_pr214_one_target`, OPEN issues and automatic OPEN events. It checks frozen
  status/hash/project/HUMAN and direct target-author independence in SQL.
- [0041](../../migrations/versions/0041_pr2_15_review_coordination.py)
  takes the exact Conclusion FOR UPDATE before its parent/review for both review
  and Issue INSERT, including zero-issue reviews. Its manuscript branch still
  takes SHARE; B05 must extend coordination rather than copy that gap.
- [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
  enforces complete Conclusion/review basis and blockers with deferred constraint
  triggers. [DecisionService](../../src/researchbase/application/decision.py)
  includes every review type/recommendation, verifies creation-time reviewer
  authority and transitive material-author independence. It only supports
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED; it cannot record manuscript readiness.
- [B04](B04_Manuscript_Freeze_Contract_DRAFT.md) is a **draft dependency**, not
  implemented freeze evidence. Current publication persistence is draft-only.
  Its future same-UoW verifier must exist and pass acceptance before B05 writes
  manuscript reviews. Do not fabricate FROZEN manuscripts by fixture SQL.
- The current migration head is `0047_pr2_18_novelty_prior_art`; recheck before
  implementation. [PR2-14 matrix](../phase2/PR2-14-review-slice-matrix.md)
  documents the original narrower acceptance, not B05 acceptance.

No B05 execution pack is assumed. The reference drafts' approval does not approve
B05. Code presence alone does not prove milestone acceptance.

## 2. Scope, dependency boundaries and non-goals

Extend the existing `InternalReviewService.create/read` with MANUSCRIPT_VERSION.
Add a verified complete-basis helper for later Application commands, with no new
canonical record or persisted readiness flag. Record zero to 100 initial issues;
retain append-only Issue INSERT semantics and the existing automatic OPEN event.

B05 does not enable publication INTERNAL_REVIEW/READY, new Decision purposes,
approval request/decision/consumption, Issue resolution/dismissal, RevisionAction
or manuscript revision. A manuscript may be reviewed while its Publication is
DRAFTING: B04 deliberately leaves that lifecycle unchanged. Lifecycle transition
contracts remain prerequisites for the full G6/F5 workflow.

## 3. Invariants and exact review basis

1. **Exact target.** Project and Publication agree; manuscript has frozen_at,
   complete B04 seal and FROZEN or SUPERSEDED status. SUPERSEDED preserves exact
   history and is accepted here as in PR2-14; it never substitutes for a future
   readiness command's current FROZEN target requirement. Review copies only the
   independently verified manuscript hash. Verify document CAS bytes/size, both
   seal hashes, complete placements and exact scientific closure through B04.
   New review requires derived current validity VALID. Citation alone is not
   scientific support; contradictory evidence is retained.
2. **Independent reviewer.** Current verified HUMAN, active project and effective
   REVIEWER or OWNER role. Exclude manuscript/Publication creators, all placement
   creators, document/artifact creators and every author reached by the exact
   frozen scientific graph (including owning identities, evidence relations,
   explicit literature snapshots, source correction/predecessor provenance).
   Use Decision's typed material-author traversal extended with manuscript edges,
   not a generic JSON graph or a new authorship snapshot. These attribution facts
   are different from the publication author list. An Agent cannot become a
   formal reviewer by asserting a HUMAN identity or recommendation.
3. **Immutable evaluation.** No target write or automatic scientific verification.
   Recommendation is assessment, not authority. Review hash excludes issues,
   timestamps and status, exactly as R2 15 requires. Issue history remains separate;
   appending a blocker never rewrites an old review hash.
4. **Complete basis.** In the protected transaction, select **all** reviews whose
   manuscript FK and Project equal the exact target. Verify each review's target
   digest, own hash, historical reviewer authority at created_at and independence
   from the material-author set. Never silently skip a corrupt/ineligible row:
   fail closed. Include all six review types and all five recommendations, even
   REJECT/UNCERTAIN, repeat reviewers, and zero-issue reviews. No latest-per-person
   reduction, caller review-ID filter, pagination or truncation.
5. **Blocking issue universe.** Query every issue joined through those exact-target
   reviews, independently of any proposed subset. OPEN with severity BLOCKING
   blocks the gate. Other severities and unfavorable recommendations remain
   visible; they do not become automatic Decision outcomes. No affirmative
   recommendation can cancel a blocker. No cross-version or cross-project review
   satisfies this gate. Issues on placed scientific inputs are handled through
   owning validity/gate contracts; B05 invents no cross-target Issue inheritance.
6. **Recheck at use.** Complete basis is an observation in one transaction, not a
   reusable certificate. Later commands must rerun it in their effect UoW after
   the same locks; an earlier read or persisted Decision cannot suppress a newer
   review/blocker. Historical reads preserve old facts when validity later changes.

### 3.1 Basis projection and ordering

The helper returns one exact `ManuscriptVersion` reference plus every exact
`InternalReviewRecord` reference, duplicate-free, sorted by `(type, canonical
lowercase UUID text, content_hash)` with derived contiguous zero-based ordinals.
This matches `domain/decision.py` and R3 18's basis rules. It does not persist a
Decision, compute a new scientific hash, or extend 0042's Conclusion-only tables.
No-review returns an empty review tuple and gate failure; completeness failure or
corrupt provenance raises an error. Blockers remain listed even if the gate fails.

## 4. Proposed commands, DTOs and historical readback

| Operation | Inputs / result |
| --- | --- |
| `InternalReviewService.create` | Existing principal, project, target_kind, target_id, review_type, recommendation, summary, issues, request; add only MANUSCRIPT_VERSION dispatch. Return existing InternalReviewReadback with explicit manuscript kind. |
| `InternalReviewService.read` | Existing principal, project, review_id; exact historical review and all appended issue history visible in its snapshot, ordered ordinal/id. Extend target/hash verifier explicitly. |
| `collect_manuscript_review_basis(uow, project_id, manuscript_version_id)` | Internal Application helper after §12.2 locks/authorization; returns §11.3 projection, never opens another UoW or commits. No public readiness command. |

Independent inputs comprise exact manuscript/document/trace, applicable frozen
specifications and machine verification evidence. A review summary can refer to
those inputs; no author reasoning transcript, generic review-context schema or
Agent runtime is required. This slice records an evaluation, not proof that the
reviewer read or understood all prose.

## 5. Schema and literal hash proposal — no migration

Reuse `internal_review_records`, `review_issues`, `review_issue_events`; no new
columns or tables. Preserve all existing concrete RESTRICT FKs and indexes.
Use the exact existing review payload with target.type `ManuscriptVersion`:

```json
{"type":"InternalReviewRecord","material_version":1,"project_id":"<uuid>","target":{"type":"ManuscriptVersion","id":"<uuid>","content_hash":"<verified hash>"},"reviewer_actor_id":"<uuid>","review_type":"<enum>","recommendation":"<enum>","summary":"<NFC text>"}
```

Use existing canonical JSON/SHA-256, scheme `sha256-cjson-v1`. R2 15's manuscript
review golden digest is `f974d3fad6625fe231671f5f485cc7a6ef8dc7926beba71259813fb75d3de704`.
No issue list or basis projection enters this payload. §12.1 specifies the forward
migration guards, not an instruction to edit 0040–0042.

## 6. Error contract — existing categories only

§11.2 pins all mappings against actual API/CLI dictionaries. Authorization precedes
any target-specific disclosure. Missing or wrong-project review read is NOT_FOUND;
authorized create with absent, wrong-project or unsealed target follows existing
REVIEW_TARGET_NOT_FROZEN. Hash/closure/authority-history corruption fails provenance
validation. Basis gate failure is a projection, not an invented exception; later
approval commands translate it to their existing APPROVAL_GATE_FAILED boundary.

## 7. Transactions, concurrency and replay

One synchronous PostgreSQL 18.x READ COMMITTED UoW per create. First take the
fixed SHARE table inventory, then request advisory, exact manuscript,
Project coordination, Publication, authority, review rows and Issue reads in the
order in §12.2. The target row serializes both review INSERT and Issue INSERT,
including ordinary SQL and zero-issue reviews; SHARE guards protect mutable
closure/authority INSERT phantoms without adding review-table lock upgrades.

Each exact-ID read uses one fresh REPEATABLE READ, READ ONLY transaction, set
before the first query including authorization. Authenticate the reader, verify
saved hashes and exact B04 closure in that snapshot, and recheck fresh credential/
time and read entitlement before return. No explicit table, advisory or row locks
are taken, including by authorization and closure adapters (§12.2).

Preserve the existing deterministic identity:
`uuid5(NAMESPACE_URL, f"pr214:{deployment_id}:{project}:{actor_id}:{request}")`;
issues use `uuid5(review_id, f"issue:{ordinal}")`. Same namespace across kinds
means reusing a request for another target must conflict, never create a second
review. Compare normalized review material and ordered issue triples. As in the
current service, subsequently appended issues can make replay conflict; never
silently append, drop or overwrite them. No receipt table is added.

Proposed manuscript replay refinement: after current read entitlement, verify the
saved historical binding and exact request first, without requiring today's
VALID status or current write role. Changed material is IDEMPOTENCY_CONFLICT.
New creation requires current HUMAN writer authority and VALID target. Historical
read/replay recomputes frozen material and review hashes while reporting/retaining
later invalidity; it does not recertify scientific validity. This refinement does
not change accepted Claim/Conclusion replay behavior.

Use fresh `clock_timestamp()` and credential validation after every lock wait
phase and immediately before commit/return; no cached authorization timestamp.
Deadlock/serialization restarts the entire UoW at most three attempts; timeouts
fail as CONCURRENT_MODIFICATION without internal retry. No partial review, issue
or event survives failed validation, credential expiry, trigger error or commit.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Tests must show complete old-or-new observations for every competing writer.
For write races, observe actual blocking with independent connections and barriers,
not sleeps. For exact-ID reads, prove a concurrent unrelated INSERT commits while
the reader remains open, with a consistent snapshot and no explicit locks.
Normal application-role SQL must participate in the manuscript row protocol.
At deferred constraint firing, the final review/issue/event structure must be
complete. Do not pretend a hash verifies issue history, or that row locks on
already discovered reviews exclude a new zero-issue review.

## 9. Acceptance criteria and evidence boundary

B05 needs approved/accepted B04 freeze and the accepted PR2-14 base. Acceptance
requires exact sealed target verification, independent HUMAN review, immutable
review+OPEN issues/events, replay/reconnect, complete basis and phantom/race tests.
No P0/P1 may remain. Source code or this draft cannot certify that prerequisite.

G6 tests later follow frozen v1 → independent review/blocker → separately
contracted Decision/revision → frozen v2 → independent re-review. v1 and its
issues remain unchanged. F5 must later exercise the real ready-approval boundary
and prove a newer blocker rejects it with no lifecycle/grant effect. B05 proves
that the helper sees and blocks that issue; it cannot claim full G6/F5 PASS while
those commands are unavailable. See [PR2-19 plan](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md).

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Frozen target | Exact B04-sealed manuscript UUID/hash with verified retained document and placements. |
| Independent | HUMAN reviewer is outside the typed material-author set and has authenticated current project authority. |
| Complete basis | Target plus all exact-target reviews, including unfavorable and zero-issue records. |
| Eligible | Same exact target/hash, independently verified review and creation-time authority; invalid stored rows fail closed. |
| Issue phantom | New issue committed after an earlier query, previously invisible to that query. |
| Review phantom | New review, even without issues, missed by locking only existing review rows. |
| Historical validity | Retained frozen material remains verifiable; today's derived scientific status can differ. |
| SHARE inventory | Fixed table locks protecting every consulted mutable closure and authority fact for a write UoW. |
| Gate projection | Transient typed observation used inside a command; never a persisted approval or truth flag. |
| G6 / F5 | Review/revision workflow and blocking-issue bypass failure injection; broader than this slice. |

## 11. Decisions taken in this draft

These are proposed refinements requiring owner approval, not delegated choices
for an implementer. Existing architecture and accepted hashes remain authoritative.

### 11.1 Scope and policy decisions

- Application-first extension of PR2-14, no new transport routes or commands.
- New manuscript review accepts verified FROZEN/SUPERSEDED with current VALID
  closure; no Publication lifecycle prerequisite beyond active Project authority.
- Extend transitive independence to all manuscript material/placement creators;
  current PR2-14's direct-author check alone is insufficient for this slice.
- All review types/recommendations count as basis facts. Require at least one
  verified independent review and no OPEN/BLOCKING issue for gate success; no
  invented SCIENTIFIC+EDITORIAL quorum or ACCEPT-only filter.
- Append-only later issues remain allowed through SQL guards. No Issue disposition
  is introduced. Do not reinterpret existing OPEN events as addressed/dismissed.
- Current review read roles remain OWNER/REVIEWER. Manuscript completed replay may
  use those current read roles; no role broadening to VIEWER in this slice.
- No persisted basis table or receipt. Later effect commands must run the helper
  inside their own protected transaction and enforce their own broader authority.

### 11.2 Pinned error mappings

These match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py), including the two mappings
marked provisional there. B05 adopts their current values, not a global remapping.

| ErrorCode | HTTP | CLI exit | Use |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO, UUID, enum, Unicode or limit violation. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverified principal. |
| FORBIDDEN | 403 | 3 | Current credential, actor type, role or project entitlement fails. |
| NOT_FOUND | 404 | 3 | Authorized exact review read cannot resolve record. |
| REVIEW_TARGET_NOT_FROZEN | 409 | 4 | Create cannot resolve same-project frozen target/seal. |
| CONFLICT_OF_INTEREST | 403 | 3 | Reviewer belongs to material-author set. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt hash/binding/closure or invalid stored reviewer provenance. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Saved request differs in target, review or issue material. |
| IMMUTABLE_RECORD | 409 | 4 | Direct mutation/deletion of historical record. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK failure. |
| CONCURRENT_MODIFICATION | 409 | 4 | Unique race, deadlock, serialization failure or bounded timeout. |
| APPROVAL_GATE_FAILED | 409 | 4 | Reserved for later approval adapter of failed basis/blocker gate. |

Unexpected failures keep sanitized HTTP 500 `INTERNAL_ERROR` / CLI exit 1, as in
current adapters. No SQL, credential, driver detail or exception chain is exposed.

### 11.3 DTO fields, Python types and limits

All new values are frozen/closed, reject extra keys and wrong types before SQL.
Transport UUID text is parsed at adapters; Application fields require exact UUID
objects. Authenticated principal is separate, never caller reviewer_actor_id.

| Value | Pinned fields/types and bounds |
| --- | --- |
| Existing create inputs | `project: UUID`, `target_id: UUID`, `request: UUID`; `target_kind: Literal['MANUSCRIPT_VERSION']` for new branch. Existing two literals remain supported independently. |
| Review text/enums | `review_type` and `recommendation`: exact strings from lists below; `summary: str`, NFC, strict UTF-8, nonblank, 1..16,000 Unicode characters after NFC; preserve meaningful whitespace. |
| Initial issues | `issues: tuple[ReviewIssueRequest, ...]`, 0..100; each has `severity: str`, `issue_type: str`, `description: str` with same text bounds. Order material for replay; repeated identical issues allowed at distinct ordinals. |
| Unsupported Issue inputs | No locator or related Claim/Source/Run inputs in this slice; stored nullable columns stay NULL on service creation, as today. No caller status/ordinal/ID/time. |
| Existing InternalReviewReadback | `id, project_id, target_id, reviewer_actor_id: UUID`; `target_content_hash, content_hash: str` lowercase 64 hex; `review_type, recommendation, summary, target_kind: str`; `issues: tuple[ReviewIssueReadback, ...]`. Explicit manuscript target_kind; no ORM rows. |
| Existing ReviewIssueReadback | `id: UUID`; `severity, issue_type, description, status: str`; status is OPEN in this slice. Reads include all appended issues, no 100-row truncation. |
| New ManuscriptReviewBasis (internal) | `project_id, manuscript_version_id: UUID`; `target_content_hash: str`; `basis: tuple[DecisionBasisReference, ...]` using existing `(type: str, id: UUID, content_hash: str, ordinal: int)`; `reviews: tuple[InternalReviewReadback, ...]` sorted UUID; `blocking_issue_ids: tuple[UUID, ...]` sorted UUID; `gate_satisfied: bool` derived from nonempty reviews and empty blocker set. |

Review types: SCIENTIFIC, STATISTICAL, LITERATURE, REPRODUCIBILITY, EDITORIAL,
COMPREHENSIVE. Recommendations: ACCEPT, MINOR_REVISION, MAJOR_REVISION, REJECT,
UNCERTAIN. Severities: INFO, MINOR, MAJOR, BLOCKING. Issue types:
UNSUPPORTED_CLAIM, CITATION, STATISTICAL, METHODOLOGICAL, REPRODUCIBILITY, OVERCLAIM,
CONTRADICTION, NOVELTY, WRITING, OTHER. Hash scheme: sha256-cjson-v1. No new enums.
Initial ordinals derive 0..N-1; subsequent appends continue the sequence. No basis
size cap, pagination or omission; operational timeouts roll back the entire attempt.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Candidate **new** path: `migrations/versions/0048_b05_manuscript_review.py`, with
`down_revision='0047_pr2_18_novelty_prior_art'` only if still actual head after B04.
Otherwise allocate the next revision at implementation time. No historical edits.
No new persistence mechanism: extend 0041 row coordination and 0042 final-state
constraint-trigger pattern on the existing tables.

Retained typed layout (not CREATE instructions):

```sql
-- internal_review_records
-- id UUID PK; project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT
-- manuscript_version_id UUID REFERENCES manuscript_versions(id) ON DELETE RESTRICT
-- claim_version_id/scientific_conclusion_version_id/artifact_version_id UUID nullable FKs
-- ck_pr214_one_target CHECK (num_nonnulls(all four concrete FKs)=1)
-- target_content_hash/content_hash CHAR(64) NOT NULL, lowercase SHA-256 CHECK
-- reviewer_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT
-- review_type/recommendation VARCHAR(24) NOT NULL; summary TEXT NOT NULL
-- created_at TIMESTAMPTZ NOT NULL; hash_scheme VARCHAR(32) NOT NULL
-- review_issues: id UUID PK; review_record_id UUID NOT NULL RESTRICT FK
-- severity/status VARCHAR(16); issue_type VARCHAR(32); description TEXT
-- target_locator JSONB NULL; three existing concrete related UUID FKs NULL
-- ordinal INT NOT NULL CHECK (ordinal>=0); UNIQUE(review_record_id,ordinal)
-- review_issue_events: UUID PK/FKs; occurred_at TIMESTAMPTZ NOT NULL
-- prior_status VARCHAR(16) NULL; new_status VARCHAR(16) NOT NULL; UNIQUE(issue_id)

CREATE CONSTRAINT TRIGGER b05_complete_review
AFTER INSERT ON internal_review_records DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION b05_check_review_structure();
CREATE CONSTRAINT TRIGGER b05_complete_issue
AFTER INSERT ON review_issues DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION b05_check_review_structure();
CREATE CONSTRAINT TRIGGER b05_complete_issue_event
AFTER INSERT ON review_issue_events DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION b05_check_review_structure();
```

| Guard/function | Required behavior |
| --- | --- |
| Replace `pr214_review_guard()` retaining trigger name | Preserve existing branches and immutable UPDATE/DELETE rejection. Manuscript INSERT locks exact manuscript FOR UPDATE in a separate statement before Publication FOR SHARE; then rereads seal/project/hash/HUMAN/direct-author rules. Never SHARE→UPDATE upgrade. This covers zero-issue SQL review INSERTs. Full B04 hash/CAS and transitive checks remain Application responsibilities. |
| Replace `pr214_issue_guard()` retaining trigger name | Discover immutable review target IDs without row locks; for manuscript, exact manuscript FOR UPDATE first, then review FOR SHARE in a new statement; reread FK equality after wait. Preserve Conclusion branch and existing related-reference/project checks. All manuscript Issue INSERTs serialize, including additions to an old review. |
| `b05_check_review_structure()` (new) | Resolve review from NEW review/issue/event FK; manuscript branch only. Under target FOR UPDATE then review FOR SHARE, check final same-project frozen target/hash, issues have contiguous 0..N-1 ordinals, and each issue has exactly one OPEN event with NULL prior_status, matching reviewer_actor_id and issue.created_at. Zero issues valid. No duplicate/missing/forged event or skipped ordinal may commit. Preserve other target branches unchanged. |
| Existing `pr214_open_event`, issue/event/review immutable guards | Retain automatic initial OPEN event and all UPDATE/DELETE prohibitions. Do not generate hashes, claim semantic closure or silently repair imported rows. |

Do not add a complete-*Decision* trigger or manuscript Decision basis table in
B05. 0042's deferred final-state check is the precedent for structural checking;
complete manuscript review-basis equality and blocker checks run in the helper,
and must run again in future consuming commands. Such commands must separately
contract their own deferred exact-basis guards, rather than reusing Conclusion-only
0042 unchanged.

Preflight under ACCESS EXCLUSIVE locks on the three review tables validates any
existing manuscript history; incompatible rows abort with IDs, no rewrite. Guard
functions additionally lock target rows as above. Downgrade refuses while any
manuscript review exists before restoring weaker guards; preserve all history.
Retain `ix_pr214_review_manuscript` and existing Issue review/severity indexes.

Scoped proposed SQLSTATE `P05R1` → PROVENANCE_CLOSURE_VIOLATION for new final-state
failure. Keep existing P17E1 → IMMUTABLE_RECORD and P17E2 →
REVIEW_TARGET_NOT_FROZEN in the manuscript command normalizer; Application detects
COI explicitly before INSERT. 23503 → REFERENTIAL_INTEGRITY_ERROR;
23514/23502 → VALIDATION_ERROR; 23505/40001/40P01/55P03/57014 →
CONCURRENT_MODIFICATION, with internal retry only for 40001/40P01. These are proposed
scoped mappings, not claims that today's UoW already implements them.

### 12.2 Exact lock order and transactions

For write commands only, `B05_SNAPSHOT_TABLES` is this literal fixed set, sorted
lexically into one SHARE statement. Read paths must never take this inventory or
advisory locks: they block writers without improving snapshot verification.
The set matches the B04 closure inventory; new consulted facts require an inventory
review and race test, not dynamic catalog discovery.

```text
actor_subject_bindings actors artifact_versions artifacts audit_findings
claim_versions claims correction_records dataset_snapshots datasets
evidence_relations experiment_spec_versions experiment_specs impact_assessments
impact_targets literature_evidence literature_evidence_review_events
literature_evidence_relations literature_source_project_links literature_sources
literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements measurements
metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects run_artifact_inputs
run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions
scientific_conclusions source_versions statistical_result_inputs statistical_results
```

For write commands, **first means first SQL data statement**, before authorization,
advisory/row locks, lookup, SET LOCAL or autoflush; BEGIN transaction control is excluded. Use fresh
READ COMMITTED, autoflush=False, connection-level initial 10s lock/30s statement
timeouts to bound the first wait. Then SET LOCAL those same limits. This follows
Novelty coverage `prepare()`'s first SHARE pattern. Decision uses SHARE protection
but currently takes request/target locks before it; do not claim it is SHARE-first.
Reuse these existing mechanisms, not SERIALIZABLE snapshots, queues or a new lock
service. Review/Issue tables are excluded from SHARE to avoid write-lock upgrades;
the exact manuscript coordination in both SQL guards closes their phantoms.

| Operation | Exact sequence after beginning UoW |
| --- | --- |
| Manuscript `create` | FIRST `LOCK TABLE <sorted B05_SNAPSHOT_TABLES> IN SHARE MODE` → SET LOCAL limits → existing review request advisory `pr214:review:<derived id>` → exact manuscript FOR UPDATE → existing `literature_search_plan.lock_project(project)` (project advisory then Project FOR UPDATE) → scoped Publication FOR SHARE → nonlocking exact-principal authority check/fresh DB time → saved replay branch or new target/closure/material-author validation → all exact manuscript review rows FOR SHARE sorted UUID → Issue reads ordered review UUID/ordinal/id → fresh writer authorization → review INSERT then issues in ordinal order (automatic events) → SET CONSTRAINTS ALL IMMEDIATE → fresh authorization → commit. |
| Manuscript `read` | Begin one fresh UoW with REPEATABLE READ and READ ONLY set before the first query (including authorization) → authenticate reader and check project read entitlement using nonlocking authority query and fresh DB time → discover exact review target identity → scoped Publication, exact manuscript and review reads without row locks → verify saved review hash and B04 seal/CAS/exact closure with require_current=False through nonlocking adapters in the same snapshot → read all snapshot-visible issues/events → final fresh credential/time and read-entitlement check → return typed DTO; no writes or explicit table, advisory or row locks. Missing or non-manuscript review preserves accepted dispatch semantics within the lock-free read protocol. |
| Complete-basis helper (inside a write command only) | Caller has already taken FIRST SHARE statement → SET LOCAL limits → exact manuscript FOR UPDATE → project helper → Publication FOR SHARE → caller's fresh authority → B04 seal/current validity and author traversal → all exact manuscript reviews FOR SHARE sorted UUID → all Issue/event reads → verify §3 and project gate projection → caller rechecks authority before effect/return. No separate request advisory for this helper in the caller’s write UoW. Reuse held locks; never invoke a public read that opens another UoW. |

The read dispatcher sets REPEATABLE READ and READ ONLY before any query, including
its target-kind lookup and authorization. As in B01's
`get_search_result_resolution`, the PR2-18 exact-read fix and revised B04 reads,
authenticate the reader and verify saved hashes/closure without locks. Never call
the locking `_authorize` or project lock helper, take manuscript FOR UPDATE,
Publication FOR SHARE or review FOR SHARE, or acquire table/advisory locks on a
read path. Architecture regression tests must cover dispatch and nested adapters.

Use a nonlocking authority query matching verified subject/deployment/credential,
HUMAN actor, membership events, binding and effective role predicates. For writes,
SHARE has stabilized those rows; reads consult them in their REPEATABLE READ
snapshot. Do not call existing locking `_authorize` after closure reads on writes.
Enable `uow.enable_revision_action_snapshot_reads()` and use B04's same-UoW
nonlocking verifier/author queries for both protocols; no hidden nested transactions.

Normal SQL review/Issue writers need not take the SHARE inventory; their triggers
must take exact manuscript FOR UPDATE before any review row lock. A committed
writer before target acquisition is included; a writer waiting behind the helper
commits after its observation and is seen by the next gate. Opposing owner writes
can deadlock with SHARE-first commands: abort/retry the whole attempt, never
continue with a stale snapshot. Test mixed B04/Decision/Novelty protocols.

### 12.3 Ordered build steps and module paths

1. Verify approved dependencies, actual Alembic head and legacy review material;
   add only the candidate forward migration (§12.1). Preserve old checks/branches.
2. **New** `src/researchbase/domain/internal_review.py`: pure review enums/text
   validation and literal review material builder; reuse foundation canonical
   JSON/hash helpers. Delegate existing `_hash` without changing accepted payloads.
3. `src/researchbase/application/internal_review.py`: explicit three-way target
   dispatch in create/read/verify/view, manuscript replay branch and closed basis
   projection/helper. Use B04's future `application/manuscript_freeze.py` verifier
   inside the same UoW; add typed author traversal for manuscript placements,
   document and existing Decision material edges. Do not call public B04 read.
4. `src/researchbase/application/ports.py`: typed review repository operations and
   required snapshot/authority methods. Extend
   `src/researchbase/persistence/internal_review_repository.py` with write-only literal SHARE
   inventory and exact manuscript/parent locks, lock-free snapshot read queries, sorted
   complete reviews/issues/events and historical authority verification (reuse
   `decision_repository.py` predicates). Queries returning dicts stay inside
   persistence/Application; no SQLAlchemy imports in domain.
5. `src/researchbase/persistence/uow.py`: scoped error normalization, protected
   closure adapters and constraints forcing; `persistence/database.py`: bounded
   initial connection settings as in B04. Preserve existing transaction behavior
   outside opt-in manuscript operations. No API/CLI changes in this first slice.
6. Add §12.4 tests, run focused regressions and record exact evidence. Update owning
   PR2-14 matrix with actual results only in the later implementation PR.

### 12.4 Test artifacts and required cases

Paths marked new are proposed, not existing tests or passes.

| File | Required cases |
| --- | --- |
| **New** `tests/unit/phase2/test_b05_review_contract.py` | UUID/extra-key/tuple/type/enum failures; NFC and malformed UTF-8; 16,000/16,001 text; 0/100/101 initial issues; explicit manuscript dispatch; ordered issue replay; closed projection and no basis truncation. |
| **New** `tests/unit/phase2/test_b05_review_hash_vectors.py` | Exact R2 manuscript review vector/digest (§5), every material field changes hash; issue/time/status excluded; Claim/Conclusion vectors unchanged; canonical basis includes every recommendation/type. |
| **New** `tests/architecture/test_b05_review_boundaries.py` | First emitted SQL inventory for create/helper in write commands; exact reads set REPEATABLE READ and READ ONLY before any query, including dispatch/authorization, with no explicit table/advisory/row locks in any nested adapter; no nested UoW, SQL in domain, ORM DTO, new schema/receipt or lifecycle effect; protected queries contain no late row locks; normal SQL triggers target-before-review. |
| **New** `tests/integration/phase2/test_b05_review_migration.py` | Clean/actual-head upgrade, retained old-target reviews, preflight rejection, catalog trigger/constraint types/names, deferred checks at commit/SET CONSTRAINTS; zero issues succeeds, forged/missing/duplicate event and gapped ordinals fail; immutable UPDATE/DELETE, wrong project/hash/multiple FK/draft SQL rejected; populated-history downgrade refusal. |
| **New** `tests/integration/phase2/test_b05_manuscript_review.py` | Application-frozen B04 target success, reconnect, same request replay, changed target/summary/issues conflicts, manuscript UUID reused across kinds; DRAFT/wrong project/unsealed/hash tamper/CAS corruption rejected; HUMAN/Agent, author and transitive creator COI; credential/role expiry after waits; historical read/replay after staleness and role change; rollback after review/each issue/event and commit failure. |
| **New** `tests/integration/phase2/test_b05_review_basis.py` | Every type/recommendation, zero-issue and repeated-reviewer records included; empty reviews fail gate; no caller selection; old version/project/hash excluded or corrupt exact-target row fails closed; historical authority remains valid after reviewer retires; OPEN/BLOCKING under an unfavorable/unselected review blocks; no review/Decision/Approval equivalence. |
| **New** `tests/integration/phase2/test_b05_review_races.py` | Review INSERT including zero issues and Issue INSERT on old review versus helper, both orderings, normal-role SQL and Application; source retraction/correction, evidence dispute and governance INSERT phantoms; observe blocking, complete old/new basis or full rollback/retry; concurrent identical requests; first SHARE timeout; mixed B04/Decision/Novelty deadlock normalization and fresh post-wait credentials. Exact-ID review read does not block a concurrent unrelated INSERT into a consulted table: separate connections and barriers hold the reader open after its first query; assert REPEATABLE READ/READ ONLY and absence of explicit table/advisory/row locks, require INSERT commit before releasing the reader, and verify the inserted row stays outside its snapshot while saved review/B04 hashes and closure verify. |

Existing focused regressions: `tests/unit/phase2/test_pr2_15_decision.py`,
`test_pr2_15_uow_errors.py`; under `tests/integration/phase2/`,
`test_pr2_14_internal_review.py`, `test_pr2_14_conclusion_review.py`,
`test_pr2_15_coordination.py`, `test_pr2_15_decision_schema.py`,
`test_pr2_15_decision.py`, `test_pr2_19_governance.py`. Run B04 migration/freeze/race
suites once implemented. Later G6/F5 E2E tests must use real commands and cannot
replace the absent readiness boundary with a mock/helper PASS.

### 12.5 Not in this slice

Publication lifecycle transitions; manuscript Decision/Approval purposes or basis
tables; grant consumption; Issue addressed/dismissed state/events; RevisionAction
extensions; new manuscript revision/supersession commands; authorship/consent;
package preparation, sending or ExternalEffect; prose truth automation; Agent
runtime; new dependencies/infrastructure; SQLite integration; Phase 1 hash changes.
Only this draft is changed by the present task.

## 13. Open questions for the owner — override register

Approval must explicitly accept or replace: transitive manuscript-material
independence; review of exact SUPERSEDED targets and DRAFTING publications; unchanged
review-type quorum (one independent review, all recommendations included); current
OWNER/REVIEWER historical-read/replay roles; append-only later Issue INSERT with
contiguous final ordinals/events; transient complete basis without new tables;
Application-first delivery. B04 approval/acceptance and separate implementation
authorization remain required. No unresolved policy is delegated to the implementer.

## 14. Documentation verification note

Verification of this documentation change is recorded below. Future B05 tests and
full G6/F5 acceptance are not claimed. The whole test suite is reserved for the
loop's check, per the task instruction.

Documentation-only run, 2026-10-15. Only this proposal was added; no commit, push
or branch. Existing offline environment used `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache`.

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff format --check .` | Exit 0; 536 files already formatted. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff check .` | Exit 0; All checks passed. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/unit tests/architecture -o addopts='' -ra --tb=short > /private/tmp/b05-unit-architecture.log 2>&1` | Exit 1; 2,156 collected, 2,139 passed, 5 failed, 12 errors, 5 warnings in 42.90s. |
| `git diff --check` | Exit 0; no diagnostics. |
| `git diff --no-index --check /dev/null docs/proposals/B05_Manuscript_Internal_Review_Contract_DRAFT.md` | Exit 1 for new-file difference; no whitespace diagnostics. |

The static-acceptance unit failure is the inherited
`git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` check reporting a new blank
line at EOF in
`pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt:4`.
That file was unchanged. Four `tests/unit/test_hg1_runner.py` failures are
`PermissionError: Operation not permitted` at socket bind. All 12 errors are
`tests/architecture/test_pr2_19_boundaries.py` fixture setup demanding explicit
`RB_TEST_ADMIN_URL`; no PostgreSQL selector was supplied to that run.
These are failures/errors, not passes or skips.

Exact focused PostgreSQL command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_19_governance.py -o addopts='' -ra --tb=short -x > /private/tmp/b05-postgres.log 2>&1
```

Observed: exit 1, **81 collected, 1 setup error in 0.43s**, stopped at the first
case; the other 80 did not execute. PostgreSQL connections to localhost:5432 were
denied with Operation not permitted. No PostgreSQL PASS is claimed.

A read-only Python check resolved all 24 local Markdown links, matched all 12
HTTP/CLI mapping pairs against the source dictionaries and verified all 41 lock
tables against SQL CREATE TABLE/Alembic create_table declarations. It exited 0.
The whole suite was not run; the loop's subsequent check supplies that evidence.

### Director review 1 revision verification — 2026-10-15

Only this proposal was revised; the status line is unchanged. Read contracts now
use lock-free REPEATABLE READ, READ ONLY snapshots, consistent with revised B04,
B01 and the PR2-18 fix. Planned architecture/race cases distinguish write-only
SHARE coordination from reads and require a concurrent unrelated INSERT to commit
while the reader remains open. These are planned tests, not implemented B05 passes.
The earlier verification record above is retained as history.

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff format --check .` | Exit 0; 536 files already formatted. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff check .` | Exit 0; All checks passed. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/unit tests/architecture -o addopts='' -ra --tb=short > /private/tmp/b05-r1-unit-architecture.log 2>&1` | Exit 1; 2,156 collected, 2,139 passed, 5 failed, 12 errors, 5 warnings in 37.50s. |
| `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_18_concurrency.py tests/integration/phase2/test_pr2_18_replay.py -o addopts='' -ra --tb=short -x > /private/tmp/b05-r1-postgres.log 2>&1` | Exit 1; 110 collected, 1 setup error in 0.40s; other 109 did not execute. PostgreSQL connection denied: Operation not permitted. |
| `git diff --check` | Exit 0; no diagnostics. |

The unit/architecture failure causes match the earlier record: inherited
`pyright-000.txt` blank line at EOF, four denied socket binds, and 12 PR2-19
architecture fixtures requiring explicit `RB_TEST_ADMIN_URL`. No PostgreSQL PASS
is claimed. A read-only Python check also confirmed the unchanged status line,
24 resolving local links, snapshot-read protocol text and the planned nonblocking
INSERT case. The whole test suite was not run; the loop's check supplies that evidence.

## 15. First-slice implementation notes — 2026-10-15

Owner authorization covers this first slice. The earlier documentation-only
verification records above remain historical records, not implementation evidence.

Substitutions and deferrals:

- Actual predecessor is `0048_b04_manuscript_freeze`; the sole new migration is
  `0049_b05_manuscript_review`. Existing migrations are unchanged.
- `ManuscriptFreezeService.verify_in_uow` is the existing same-UoW B04 verifier.
  Review-side predicates accept FROZEN/SUPERSEDED. For SUPERSEDED verification,
  the review adapter verifies the immutable seal with B04's existing literal
  algorithm, without treating the Publication's current pointer as historical
  provenance. No persisted status or pointer is changed. B04 currently makes
  SUPERSEDED manuscripts unreachable; the integration case is explicitly skipped
  until a later supersession contract permits their creation. This is a deferred
  reachable-state test, not a reason to block the FROZEN first slice.
- `InternalReviewService.collect_manuscript_review_basis(uow, project_id,
  manuscript_version_id)` is an instance helper so it reuses the configured CAS
  verifier. It opens no UoW and commits nothing. The caller must first prepare
  the SHARE inventory and authorize in that write UoW; the helper rejects an
  unprepared repository, reuses target/project/Publication locks, and verifies
  the complete basis. The caller must recheck authority before its own effect.
- B05 reuses B04's fixed 41-table inventory and protected closure adapters.
  `create_database_engine(..., b05_write_timeouts=True)` supplies the existing
  bounded initial connection settings for B05 write factories. Exact reads do
  not take that inventory or any explicit row/advisory locks.
- The existing `pr214_issue_events_immutable` trigger delegates to `m2_immutable`
  and emits `P17D1`, rather than `P17E1`. The scoped B05 normalizer maps both to
  IMMUTABLE_RECORD; the trigger and historical migrations are preserved.

No readiness, manuscript Decision/Approval, Issue disposition, revision,
supersession command or external effect is introduced. B05 technical verification
is not full G6/F5 acceptance or owner milestone acceptance.

The B05 deferred triggers use INSERT-time `WHEN` predicates over immutable target
bindings, so only manuscript rows queue the new final-state checks. Issue/event
predicates perform nonlocking typed FK lookups; final validation still takes the
exact manuscript before review-row locks. The predicates are VOLATILE to see
current-command inserts. Legacy target writes therefore retain their original
commit behavior, including temporary SQL-role grant revocation before commit.
