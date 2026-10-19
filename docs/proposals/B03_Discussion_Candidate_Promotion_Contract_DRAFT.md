# B03 Discussion Candidate Promotion Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B03 proposes one explicit command admitting a selected discussion candidate into
research as a new Hypothesis and its first HypothesisVersion, always DRAFT.
It retains the exact closed transcript, selected turn, question version and
initial admitted material. Discussion text, citations and confidence confer no
scientific truth or permission. This document changes no runtime behavior.

Build only after owner approval and separate implementation authorization:

1. Resolve ADR-0020's Architecture Questions and inspect the actual migration head (§§5, 13).
2. Add the typed provenance relation and extend the existing discussion receipt;
   preserve historical receipts (§12.1).
3. Add closed candidate/command DTOs and reuse research's creation rules inside
   the same UoW (§§4, 11.3, 12.3).
4. Implement write serialization, immutable admission readback and replay (§12.2).
5. Add focused unit, PostgreSQL, architecture and G4 suffix tests (§12.4).
6. Record executed checks and stop. Approval of this draft is not acceptance.

Five review rules:

- Only explicit authenticated HUMAN OWNER/RESEARCHER admission creates science.
- Output is a fresh DRAFT, never Claim, frozen truth, support or Decision.
- Provenance uses exact typed FKs and verified retained transcript bytes.
- One command, one transaction; snapshot locks precede every SQL read on writes.
- Completed replay returns saved admission material with current read entitlement;
  reads use one REPEATABLE READ snapshot and no explicit table, advisory or row locks.

Read §§1–4 first; use §10 for terms, §11 for pinned choices and §12 to build.
No implementation, migrations, architecture edits or gate declaration are authorized.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6–13 | One owning fact; Hypothesis differs from Claim; immutable formal history; shared Application boundary. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A1 | AgentPromotionRecord belongs to Phase 3. Do not instantiate it or invent AgentExecution for Phase 2. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 1/2 registries | Research owns Hypothesis/Version; discussion owns sessions/turns; retained bytes use ArtifactVersion. |
| [Cross-phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§6, 12–18 and H-INV-006 | Additive contracts, exact provenance, candidate default and common Application boundary. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§14, 41.6, 42.4, F4 | Explicit discussion-to-hypothesis promotion; discussion is not Decision; G4 ends in explicit research admission. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), discussion tables | Concrete question/claim/source inputs, sealed turns, transcript ArtifactVersion FK. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 17, 24 | Candidate → validation → explicit Application command; no direct Skill persistence or generic Phase 3 runtime. |

Inspected baseline:

- [DiscussionService](../../src/researchbase/application/discussion.py) uses HUMAN
  project roles, scoped command receipts, closed-session derivation and exact
  transcript binding. `request_promotion` unconditionally raises FORBIDDEN.
  Its current `read` calls a project-locking authorizer; B03 must not reuse that
  helper for its new reads or claim the legacy path already meets §12.2.
- [discussion_artifacts.py](../../src/researchbase/application/discussion_artifacts.py)
  deterministically derives transcript and mechanical concept-map bytes only.
  Neither is a structured hypothesis candidate. B03's selected candidate DTO is
  a proposed manual extraction, not an existing generator feature.
- [ApplicationService.create_hypothesis](../../src/researchbase/application/commands.py)
  creates an identity, first DRAFT version and current pointer, then commits its
  own UoW. It has no candidate provenance or durable promotion replay. Calling it
  as a nested public command would break atomicity.
- [domain/research.py](../../src/researchbase/domain/research.py) owns statement,
  expected_direction, success_criteria and rationale. DRAFT hashes remain null.
- Migrations [0032](../../migrations/versions/0032_pr2_10_discussion.py) and
  [0034](../../migrations/versions/0034_pr2_10_exact_transcript_binding.py) supply
  discussion history/binding, not admission. [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
  supplies the deferred completeness-trigger pattern. Decision and novelty
  repositories supply first-statement SHARE locking and lock-free snapshot reads.

No B03 execution pack exists in this proposal. B02 and this draft share the
admission convention in §5.1; neither draft is approved for implementation.

## 2. Scope, dependency boundaries and non-goals

One new research-owned `promote_discussion_to_hypothesis` command and one exact
`get_discussion_hypothesis_admission` query. One candidate selects one existing
turn from a CLOSED, transcript-bound session and one admitted question version.
The caller explicitly supplies the hypothesis material. This slice does not
infer or automatically extract a statement from conversation.

New output always has a fresh Hypothesis identity and version 1. Existing-parent
revision, batch admission, ResearchQuestion creation and Claim/Decision promotion
are excluded. Existing research draft edit/freeze commands retain their contracts.
The admission preserves creation material even if the output draft later changes.

## 3. Invariants and conservative judgments

1. Project, session, selected turn, transcript and question agree. The exact
   question is in `discussion_session_question_inputs`; its parent supplies
   `Hypothesis.research_question_id`. Never resolve `latest/current` as provenance.
2. First admission requires CLOSED, a bound exact transcript and a question
   version in FROZEN/SUPERSEDED with valid frozen material. Verify transcript
   role `discussion_transcript`, media type `application/json`, frozen metadata,
   byte size, content hash and CAS bytes against deterministic session rendering,
   as `_verify_version(..., binding=False)` does. SUPERSEDED is historical, not
   automatically invalid. A concept map cannot substitute for the transcript.
3. The selected turn must belong to the session. Its actor/role and every input
   and citation remain reachable through the transcript and sealed typed tables.
   Admitting a statement does not verify any cited assertion, add evidence or
   claim that the turn author authored the new hypothesis. `admitted_by` is the
   authenticated caller; never accept an asserted actor from candidate material.
4. Fresh output is DRAFT, version_number=1, row_version=1, current pointer set;
   content_hash, hash_scheme, frozen_at are null. Initial success_criteria is
   null in this bounded slice. Do not alter Phase 1 hypothesis hash payloads.
5. Admission relation and receipt are immutable. No late provenance attachment
   to an existing hypothesis. Admission, both research rows, pointer and receipt
   commit together; any failure rolls everything back.
6. The initial material is retained in typed columns. The candidate digest is
   an identity of proposed content/context, not a frozen scientific content hash.
   No generic polymorphic target table or JSON reference graph is introduced.

### 3.1 Candidate identity

A candidate is the closed DTO in §11.3, not a new canonical entity. Its identity
is `(session_id, turn_id, candidate_hash)`. Different extracted statements from
one turn are distinct candidates; the exact same candidate cannot create another
hypothesis through a new request, actor or process. This is an admission relation
uniqueness rule, not a claim that similar scientific statements are duplicates.

## 4. Proposed commands, DTOs and historical readback

`promote_discussion_to_hypothesis(principal, command)` accepts VerifiedPrincipal
out of band. `PromoteDiscussionHypothesisCommand` contains project_id, session_id,
request_id and one `DiscussionHypothesisCandidate`. Fields and bounds are §11.3.

First execution requires current HUMAN OWNER or RESEARCHER, ACTIVE project,
active membership/binding, unretired actor, effective role and valid credential.
Use fresh database `clock_timestamp()` after waits and immediately before commit;
never infer authority from a turn role, transcript label or `ExecutionContext`.

`DiscussionHypothesisAdmission` returns receipt_id, project_id, session_id,
turn_id, transcript_artifact_version_id, research_question_version_id,
candidate_hash, initial material, hypothesis_id, hypothesis_version_id,
admitted_by and admitted_at. It describes historical admission, not current
hypothesis state. Its query takes `(principal, project_id, receipt_id)` and
requires current HUMAN OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER read entitlement;
an archived project remains readable under the existing discussion read policy.

Leave the legacy untyped `DiscussionService.request_promotion` denied. New
callers use the typed research command; discussion may expose a thin delegate
only after authorization, without owning scientific creation or a second UoW.
No new HTTP route or CLI command is needed for the first Application slice.

## 5. Proposed migration — one admission relation and existing receipt constraints

The proposed migration adds `discussion_hypothesis_admissions` and extends only
the constraints/indexes/guards on `discussion_command_receipts` to accept
`PROMOTE_HYPOTHESIS` and enforce receipt/admission completeness (§12.1); it adds
no column to an existing table.
The relation is not registered in Registry 03 or Field Contract 13. Calling it a
Relation pattern is not schema approval: [ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md)
asks B03-AQ-01 under AGENTS.md §4. No migration is implemented or authorized here.

| Proposed addition | Existing representation tried; missing fact and disposition |
| --- | --- |
| `discussion_hypothesis_admissions` | Reuse session/turn/input/citation seals and bound ArtifactVersion for all discussion history. Existing receipts already own actor, time, scoped request and input_hash, but result_session_id/result_turn_id cannot name a scientific version or retain the manual extraction. HypothesisVersion stores editable material and a question identity, not immutable initial text, selected turn/transcript/exact question version or request binding. No existing provenance relation connects those facts. Retain one typed receipt → origin → exact new hypothesis-version relation. |
| `discussion_command_receipts.result_hypothesis_version_id` | Dropped. Receipt → admission via receipt_id PK/FK → hypothesis_version_id already supplies the exact output, uniquely. Deferred guards enforce one admission per PROMOTE receipt and forbid admissions on other commands. A second output FK duplicates that fact and is not needed for replay. |

### 5.1 Shared B02/B03 admission convention

Use [B02 §5.1](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md#51-shared-b02b03-admission-convention):
`DiscussionHypothesisAdmission` uses `admitted_by`, `admitted_at`, exact
`hypothesis_version_id` and retained `statement`, `expected_direction`, `rationale`.
These are initial material, never current draft values. Both drafts atomically
create typed provenance plus version 1 DRAFT, serialize requests, compare normalized
input only after original-actor/current-read authorization, and return saved IDs
and material on replay. Different input conflicts; another request admitting the
same origin candidate is DUPLICATE_CONTENT. No second creation on replay.

Both use concrete RESTRICT FKs and verified hashes/bytes of exact immutable input
versions. Here the bound transcript and frozen question hashes are verified through
existing rows, not copied into new hash columns; candidate_hash binds their exact
IDs and retained extraction. The output DRAFT ID is creation provenance, not a
FrozenReference. No scientific hash is added to a DRAFT or changed on later edits.

Necessary differences: B03 already has a deployment/project/actor/command/request
receipt and saved input_hash; reuse it, with receipt_id as the admission PK/FK,
and derive admitted_by/time from actor_id/completed_at. B02's relation is itself
the receipt, keyed by command id, with request comparison reconstructed from its
retained fields. B03 requires a frozen question input and HUMAN admission; B02
allows Human/Agent and optional organizational question parent. B03 manually
extracts content from a turn and permits optional direction/rationale with existing
NFC/whitespace semantics; B02 selects an ordered candidate/section, requires
trimmed adaptation rationale and leaves direction null. These differences do not
justify a generic target table, new discussion capture/source tables or a second
receipt mechanism.

### 5.2 Literal material

Use existing `sha256_canonical_json`, lowercase UUID strings and explicit nulls.
Candidate hash literal:

```text
{"schema":"discussion_hypothesis_candidate_v1","project_id":UUID,
 "session_id":UUID,"turn_id":UUID,"transcript_artifact_version_id":UUID,
 "research_question_version_id":UUID,"statement":str,
 "expected_direction":str|null,"success_criteria":null,"rationale":str|null}
```

Here UUID means canonical string in JSON, not a Python UUID object. Input_hash
literal is `{"command":"PROMOTE_HYPOTHESIS","project_id":UUID,
"session_id":UUID,"candidate_hash":hex64}`. Receipt scope binds deployment,
actor and request separately; no principal credential or timestamp enters either
hash. Normalize newly supplied candidate text to NFC before validation/storage/hash,
as required by Hash R2 15; preserve meaningful whitespace without trimming or
case folding. Never normalize or rewrite existing transcript/Phase 1 bytes. Hash
material is closed and versioned; no provider metadata or opaque JSON semantics.

## 6. Error contract — proposed use of existing categories

Use only §11.2's existing codes. Authorization precedes resource disclosure.
Missing own-scope records return NOT_FOUND; inaccessible project returns
FORBIDDEN. Invalid enum/type/text is VALIDATION_ERROR. Invalid candidate context
is distinct from a corrupt retained transcript. Raw SQLSTATE is never an API
code; translate known constraints to the pinned category, let unexpected defects
remain internal failures. Do not invent a promotion-specific code or new mapping.

## 7. Transactions, concurrency and failure recovery

One READ COMMITTED UoW per write attempt, with the literal first SHARE statement
in §12.2 before authorization queries. No public create command nested inside it.
At most three whole aborted-transaction attempts for normalized concurrency
failures, following DiscussionService's bounded retry convention. Constraint,
authorization, provenance and duplicate denials are not retried.

Completed same-scope request: check current read entitlement, compare input_hash,
return the saved immutable admission and output IDs. Do not allocate IDs, rerun
admission eligibility, require still-DRAFT output or return its edited material.
Changed input is IDEMPOTENCY_CONFLICT. A different actor's request scope cannot
read another actor's receipt as replay. Exact query remains separately authorized.
Replay does not require still-writable project/role, but does require valid current
credential/binding and read access. Missing or contradictory persisted provenance
fails closed; missing transcript bytes is PROVENANCE_CLOSURE_VIOLATION, including
on read/replay. Recompute candidate_hash from retained initial columns/context
and compare input_hash to the receipt; verify receipt/relation/output IDs and
same-project ownership. Do not compare initial material to subsequently edited
hypothesis material. A failed or rolled-back request leaves no durable receipt.

Concurrent same-scope requests serialize by existing discussion receipt advisory
key. Different scopes attempting the same candidate serialize by candidate key;
one commits, the other returns DUPLICATE_CONTENT with no extra research rows.
Lost response/restart returns the same receipt and output IDs. A different
request is not replay even if its candidate matches.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Use §12.4's files. G4 needs a positive control with an explicit candidate and
one DRAFT output, plus F4 zero-write tests for instructions in turns. Retain the
legacy FORBIDDEN test. Candidate text saying “approved” cannot freeze, support,
release or create Decision. Tests must inspect durable rows after reconnect.

## 9. Acceptance criteria and evidence boundary

Dependencies already represented in code are PR2-10 closed discussion/exact
artifact binding and research identity/version creation. Presence is not a gate
acceptance claim. Follow [PR2-19's G4/F4 boundary](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md):
this contract proposes the missing positive suffix only, not full Phase 2 exit.

B02 and B03 should use the same owning-research admission convention: closed
candidate, retained initial material and exact ArtifactVersion/context FKs,
existing scoped durable receipt, one transaction, DRAFT-only output and historical
replay. Reuse transaction-local research creation logic and hash conventions;
do not force strategy/discussion origins into generic `target_type + target_id`
or invent a shared Phase 3 record. The names and origin-specific differences
are pinned in §5.1.

Acceptance requires approved contract, separate execution scope, real PostgreSQL
18 migration/constraint/race tests, existing discussion and research regressions,
static/type/architecture checks, and recorded counts. No open P0/P1 findings.
This documentation change neither runs future tests nor removes G4's blocker.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Candidate | Explicit caller-selected hypothesis material, without scientific authority. |
| Admission | Owning research creation of a fresh DRAFT with retained provenance. |
| Transcript | Exact bound ArtifactVersion bytes rendered from the closed discussion. |
| Receipt | Existing discussion request completion row, scoped by deployment/project/actor/command/request. |
| Initial material | Statement/direction/rationale admitted at creation, independent of later draft edits. |
| UoW / CAS | Unit of Work / existing content-addressed ArtifactStore. |
| G4 / F4 | Phase 2 discussion-to-research golden path / unsafe discussion-promotion failure probe. |
| B02 | Parallel strategy candidate admission backlog item; not an approved dependency here. |

## 11. Decisions taken in this draft

These are proposed pins for owner approval, not new frozen architecture.

### 11.1 Scope and policy decisions

Fresh hypothesis only; exactly one selected turn and question; transcript must
already be bound; manual explicit candidate; initial success_criteria=null.
Only existing HUMAN writer roles. No new agent authority. Historical replay uses
current read entitlement. New queries never call the locking discussion
`_authorize`. Persist one typed relation plus the existing receipt constraint extension.
No new runtime dependencies, event framework, generic promotion registry or
storage backend. ADR-0020 approval is required before implementation authorization.

### 11.2 Pinned error mappings

Mappings match [api/errors.py](../../src/researchbase/api/errors.py) `_STATUS`
and [cli/errors.py](../../src/researchbase/cli/errors.py) `CLI_EXIT_CODES`.
They apply even though no new transport adapter is authorized here.

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/bounds/unknown field failure. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverified principal. |
| FORBIDDEN | 403 | 3 | Current credential/project/role denial; legacy promotion denial. |
| NOT_FOUND | 404 | 3 | Authorized exact session, turn, question or receipt absent. |
| INVALID_STATE_TRANSITION | 409 | 4 | Session not CLOSED or transcript not bound. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Question not admitted/frozen or candidate's exact context mismatched. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Transcript bytes/hash/role or saved admission closure/creation completeness corrupt or unavailable. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same scoped request, changed normalized input. |
| DUPLICATE_CONTENT | 409 | 4 | Same candidate already admitted under another request. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted bounded deadlock/serialization/lock-timeout retries. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Known FK constraint rejection. |
| IMMUTABLE_RECORD | 409 | 4 | Attempted receipt/admission history mutation. |

Unexpected errors retain existing HTTP 500 / CLI 1 transport handling. Direct SQL
tests assert SQLSTATE/constraint and rollback, not fictional HTTP responses.

### 11.3 DTO fields, Python types and limits

Immutable, closed DTOs; exact UUID values at Application boundary, canonical UUID
strings at a future transport. Reject bool as int, unknown fields and caller
status/hash/time/actor/output IDs. Text must be valid UTF-8 without NUL or lone
surrogates. Candidate text is NFC-normalized first. Bounds count Python characters after
NFC; whitespace-only strings fail.

| DTO/field | Type and bound |
| --- | --- |
| Command project_id, session_id, request_id | `UUID`, required, no default. |
| Command candidate | `DiscussionHypothesisCandidate`, required. |
| Candidate turn_id, transcript_artifact_version_id, research_question_version_id | `UUID`, required; no live references. |
| Candidate statement | `str`, 1..16,000 characters, nonblank. |
| Candidate expected_direction | `str | None`, null or nonblank 1..64; free text, not an invented enum. |
| Candidate rationale | `str | None`, null or nonblank 1..16,000. |
| Candidate success_criteria | No caller field; always derived null in this slice. |
| Admission IDs | `UUID`: receipt/project/session/turn/transcript/question/hypothesis/version/admitted_by. |
| Admission candidate_hash | `ContentHash`, lowercase SHA-256 hex64. |
| Admission statement, expected_direction, rationale | Same text/null types and bounds as candidate. |
| Admission admitted_at | UTC-aware `datetime`, database-derived. |

No lists, batches or extra references. Enums are command `PROMOTE_HYPOTHESIS`,
required session `CLOSED`, initial output `DRAFT`, and existing role sets in §4;
transcript/question historical versions accept `FROZEN` or `SUPERSEDED`.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Choose the next migration filename only after checking `uv run alembic heads`;
do not reserve a number in this draft. All new FKs use ON DELETE RESTRICT.
The following names/types are proposed exact pins. Preserve and recreate existing
receipt CHECKs by inspected names, including historically anonymous checks;
never edit migration 0032 or invalidate APPEND_TURN/BIND_TRANSCRIPT receipts.

```sql
ALTER TABLE discussion_command_receipts
  DROP CONSTRAINT ck_pr210_receipt_command_with_binding;
ALTER TABLE discussion_command_receipts ADD CONSTRAINT ck_b03_receipt_command
  CHECK(command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION',
                        'BIND_TRANSCRIPT','PROMOTE_HYPOTHESIS'));
-- Retain (command_name='APPEND_TURN')=(result_turn_id IS NOT NULL).
ALTER TABLE discussion_command_receipts ADD CONSTRAINT uq_b03_receipt_context
  UNIQUE(id,project_id,result_session_id);

CREATE TABLE discussion_hypothesis_admissions (
  receipt_id UUID CONSTRAINT pk_b03_admission PRIMARY KEY,
  project_id UUID NOT NULL,
  session_id UUID NOT NULL,
  turn_id UUID NOT NULL,
  transcript_artifact_version_id UUID NOT NULL,
  research_question_version_id UUID NOT NULL,
  hypothesis_version_id UUID NOT NULL,
  candidate_hash CHAR(64) NOT NULL,
  statement TEXT NOT NULL,
  expected_direction VARCHAR(64),
  rationale TEXT,
  CONSTRAINT fk_b03_receipt FOREIGN KEY(receipt_id,project_id,session_id)
    REFERENCES discussion_command_receipts(id,project_id,result_session_id) ON DELETE RESTRICT,
  CONSTRAINT fk_b03_session FOREIGN KEY(project_id,session_id)
    REFERENCES discussion_sessions(project_id,id) ON DELETE RESTRICT,
  CONSTRAINT fk_b03_turn FOREIGN KEY(session_id,turn_id)
    REFERENCES discussion_turns(session_id,id) ON DELETE RESTRICT,
  CONSTRAINT fk_b03_question FOREIGN KEY(session_id,research_question_version_id)
    REFERENCES discussion_session_question_inputs(session_id,version_id) ON DELETE RESTRICT,
  CONSTRAINT fk_b03_transcript FOREIGN KEY(transcript_artifact_version_id)
    REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_b03_hv FOREIGN KEY(hypothesis_version_id)
    REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b03_output UNIQUE(hypothesis_version_id),
  CONSTRAINT uq_b03_candidate UNIQUE(session_id,turn_id,candidate_hash),
  CONSTRAINT ck_b03_hash CHECK(candidate_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_b03_statement CHECK(length(statement) BETWEEN 1 AND 16000
    AND length(btrim(statement)) > 0),
  CONSTRAINT ck_b03_direction CHECK(expected_direction IS NULL OR
    (length(expected_direction) BETWEEN 1 AND 64
     AND length(btrim(expected_direction)) > 0)),
  CONSTRAINT ck_b03_rationale CHECK(rationale IS NULL OR
    (length(rationale) BETWEEN 1 AND 16000
     AND length(btrim(rationale)) > 0))
);
```

`hypothesis_id`, admitted_by/time and request scope are derived through the exact
version and immutable receipt, not duplicated columns. Add named index
`ix_b03_admission_project_receipt(project_id,receipt_id)` for scoped exact reads.
Use `b03_admission_immutable` BEFORE UPDATE OR DELETE calling existing
`m2_immutable()`. Existing receipt immutability remains active.

Following 0042, `b03_complete_receipt` AFTER INSERT on receipts and
`b03_complete_admission` AFTER INSERT on admissions are CONSTRAINT TRIGGERs,
DEFERRABLE INITIALLY DEFERRED, calling `b03_complete_admission_guard()`.
For each PROMOTE receipt require exactly one relation; reject an admission whose
receipt command is not PROMOTE_HYPOTHESIS. Resolve the only output via the relation's
hypothesis_version_id (no output column on the receipt). Require
CLOSED session and matching bound transcript, same-project question parent and
hypothesis, parent question match, version 1/current pointer, same creator/time
as receipt, initial DRAFT/null hashes and material equal to retained columns with
success_criteria null. Require the new hypothesis and version to have been
inserted in this transaction (existing `xmin`/transaction pattern); reject grafts
onto preexisting outputs. On a receipt trigger, non-promotion receipts with no admission are left unchanged;
an admission trigger always checks its referenced receipt command before proceeding.
Checks validate creation only; later legal draft edit/freeze must not reapply
initial-DRAFT requirements. `SET CONSTRAINTS ALL IMMEDIATE` before final auth.

Byte rendering, candidate/input hash recomputation, NFC/Unicode bounds and credential
authority remain Application checks; SQL must not pretend to authenticate CAS
bytes. Completeness guard failures use existing P17D3 → PROVENANCE_CLOSURE_VIOLATION; immutability
uses existing P17D1. Preflight existing receipts; downgrade refuses if promotion
history exists, otherwise remove owned guards/relation/receipt context UNIQUE
and restore old CHECKs.

### 12.2 Exact lock order and transactions

New write snapshot inventory `B03_SNAPSHOT_TABLES`, lexicographic order:

```text
actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions,
claims, discussion_session_claim_inputs, discussion_session_question_inputs,
discussion_session_source_inputs, discussion_sessions,
discussion_turn_claim_citations, discussion_turn_source_citations, discussion_turns,
literature_source_project_links, literature_sources, project_membership_events,
project_memberships, project_role_assignments, projects, research_question_versions,
research_questions, source_versions
```

These are read dependencies for current authorization, closed rendering and exact
input accessibility/status checks. Include neither hypotheses/versions nor the
receipt/admission tables in SHARE: this command writes them. Avoid concurrent
SHARE-to-write lock upgrades. This inventory does not claim to verify scientific
support closure; no such closure is created here.

| Operation | Exact sequence |
| --- | --- |
| New write attempt | Set connection READ COMMITTED before SQL → **FIRST statement** `LOCK TABLE <literal inventory above> IN SHARE MODE` → `SET LOCAL lock_timeout='10s'` → `SET LOCAL statement_timeout='30s'` → plain authority reads/fresh DB time → existing `discussion-receipt:{deployment}:{project}:{actor}:PROMOTE_HYPOTHESIS:{request}` advisory transaction lock → current read authorization and receipt lookup. |
| Completed replay | Same write entry protocol → compare input_hash → plain exact admission/transcript verification → fresh read authorization → commit read-only effect; no candidate advisory or research inserts. |
| First admission after absent receipt | Require writer authorization → `pg_advisory_xact_lock(hashtextextended(:key,0))`, key `b03:discussion-hypothesis:{session}:{turn}:{candidate_hash}` → duplicate lookup → plain source/session/turn/input/bytes validation → fresh writer auth → allocate research IDs and insert identity/version/current pointer → insert receipt → insert admission → force deferred constraints → fresh writer auth/time → commit. |
| Exact admission query | Set REPEATABLE READ before first query → plain current read authorization → scoped receipt/relation/exact output identity and transcript verification → fresh read authorization/time → commit. No `LOCK TABLE`, advisory lock, `FOR UPDATE`, `FOR SHARE` or locking authorizer. |

No explicit row locks in this fresh-parent command. INSERT/FK and own-pointer
UPDATE locks are implicit; no existing hypothesis is modified. Do not call legacy
`DiscussionService.read` as a second transaction to obtain the snapshot. Build it
through plain repository reads in the current UoW. Do not take project row locks
after other locks. `clock_timestamp()` advances even inside the read snapshot;
credential validity is checked at that fresh time. SHARE prevents concurrent
membership/binding changes through commit on writes. Read authorization observes
one committed snapshot, not an assertion of linearizable revocation.

### 12.3 Ordered build steps and module paths

1. Verify authoritative docs, B02 shape and actual Alembic head. Add the approved
   next `migrations/versions/` migration with §12.1's named guards/preflight.
2. Extend [domain/research.py](../../src/researchbase/domain/research.py) only if
   needed for pure validation; preserve HypothesisVersion material/hash rules.
   Add closed DTOs and pure candidate hash builder in proposed
   `src/researchbase/application/discussion_hypothesis.py`.
3. Extract reusable transaction-local creation from
   `src/researchbase/application/commands.py`; it receives the existing UoW and
   validated material/actor/time, creates research objects/current pointer and
   never commits. Existing `create_hypothesis` wraps it without changing behavior.
   B03 applies its own principal/receipt rules before calling it.
4. Add explicit repository port in `src/researchbase/application/ports.py`,
   adapter `src/researchbase/persistence/discussion_hypothesis_repository.py`,
   and wiring in `src/researchbase/persistence/uow.py`. Follow
   `decision_repository.py` / `novelty_repository.py` snapshot preparation,
   existing discussion receipt scoping and constraint normalization. Pin
   `uq_b03_candidate` to DUPLICATE_CONTENT; a receipt scope unique conflict must
   reread/compare the winning receipt after rollback, never infer success from
   SQLSTATE alone. Preserve P17D1/P17D3 mappings; map B03 FK failures (23503) to
   REFERENTIAL_INTEGRITY_ERROR, B03 bound CHECK failures (23514) to
   VALIDATION_ERROR, and 40001/40P01/55P03 to CONCURRENT_MODIFICATION. Unknown
   constraints are not silently reclassified. Domain and
   candidate builders import no Session, FastAPI, Typer or external framework.
5. Implement the two methods in the new Application service. Reuse pure
   rendering in `application/discussion_artifacts.py`, existing ArtifactStore
   verification and research repository ports, all in the same UoW.
6. Add §12.4's tests, run focused checks, document evidence and stop. Transport
   adapters/composition changes require a separately authorized extension.

### 12.4 Test artifacts and required cases

Proposed new files, not created by this documentation task:

- `tests/unit/phase2/test_b03_discussion_hypothesis_contract.py`: closed types,
  all bounds/extra keys, literal hash vectors, nulls, NFC candidate text,
  no actor/status assertions, initial material preserved after draft edit.
- `tests/integration/phase2/test_b03_discussion_hypothesis.py`: real PG18 empty
  upgrade and prior-head upgrade; historical receipts survive; positive new
  identity/DRAFT/current pointer; same-project/question-input/turn constraints;
  OPEN/unbound/missing/corrupt/wrong-role transcript; wrong bytes/hash; foreign
  project and nonmember; Agent and read-only writer denial; credential expiry
  after waits; same-request restart/lost response; changed-request material;
  concurrent equal requests and cross-actor/cross-request duplicate candidates;
  failure after each insert/pointer update/constraint check leaves zero delta.
- `tests/integration/phase2/test_b03_discussion_hypothesis_guards.py`: direct SQL
  missing/mismatched receipt relation; existing-output graft; wrong project,
  question, transcript, initial material or creator; non-DRAFT initial output;
  deferred failure at commit; immutable rows; downgrade populated-history refusal.
- `tests/architecture/test_b03_discussion_hypothesis_boundaries.py`: domain import
  boundary; first literal SHARE SQL precedes queries; correct fixed inventory;
  no nested public command/commit; exact reads contain no locks, use REPEATABLE
  READ and fail closed on corrupt saved provenance.
- Extend `tests/integration/phase2/test_pr2_19_discussion.py`: G4 positive suffix
  selects candidate after bound transcript and verifies one DRAFT/provenance
  after reconnect; F4 instruction-only prefix still writes zero science;
  legacy `request_promotion` remains FORBIDDEN.

Regression files: `tests/unit/domain/test_pr04_research.py`,
`tests/unit/phase2/test_pr2_10_discussion_artifacts.py`,
`tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`,
`tests/integration/phase2/test_pr2_10_discussion_persistence.py`,
`tests/integration/phase2/test_pr2_10_binding_contract.py` and existing architecture
suite. Assert no new Claim, EvidenceRelation, support snapshot, Decision or grant.
An absent byte store must fail, never skip the provenance check.

### 12.5 Not in this slice

AgentPromotionRecord/AgentExecution; strategy generation/B02 implementation;
new question or claim; revision of existing hypotheses; automated extraction;
non-null structured success criteria; audit/review or support inference; new
scientific hashes; agent authorization; transport routes/CLI commands; background
jobs, queues, new storage, new dependencies; full G4 or Phase 2 acceptance claims.
No repair of unrelated legacy discussion read transactions is bundled here.

## 13. Open questions for the owner — override register

Resolve B03-AQ-01 in
[ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md) before admitting the
unregistered relation and receipt constraint extension. The redundant receipt
output column is withdrawn. B02/B03 convergence is pinned in §5.1, including the
existing scoped receipt and explicit domain differences; approval must not add a
second receipt mechanism. Also approve the bounded manual, single-turn,
question-required candidate, HUMAN-only policy and null-success-criteria policy.
Neither this draft nor the ADR authorizes implementation.

## 14. Documentation verification note

Joint B02/B03/ADR-0020 documentation revision, 2026-10-19. Exact commands and
results are recorded once in [B02 §14](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md#14-documentation-verification-note).
Static checks passed (736 files formatted; Pyright 0 errors/warnings/informations).
Focused unit/architecture: **184 passed, 14 setup errors, 4 warnings** (missing
explicit DB admin URL). Configured focused PostgreSQL: **14 failed, 73 errors,
1 warning**, zero passing cases (sandbox socket access denied). Neither result
is an all-tests PASS. Documentation link/status/scope and whitespace checks passed.

Only the two drafts and ADR-0020 change; proposal status lines remain unchanged.
No implementation, migration, commit, branch or push. Current-code checks do not
prove proposed admission behavior; §12.4's tests remain planned. The loop's next
whole-suite run supplies its own evidence; this task did not run the whole suite.
