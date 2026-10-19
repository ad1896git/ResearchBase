# B02 Strategy Candidate Promotion Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B02 supplies the missing attributable Strategy → ResearchBrief → question/hypothesis
DRAFT suffix of G2. Saving a candidate, creating an ordinary research object,
and admitting that exact candidate are different operations. Nothing here freezes
scientific material, verifies evidence or establishes a scientific finding.

Read §1 for authority, §10 for terms, §11 for fixed choices and §12 for the build
plan. Follow this order only after owner approval and separate execution authority:

1. Approve the bounded artifact-binding relations in §12.1 and allocate the next
   migration after the actual head. Do not amend accepted migrations.
2. Build the closed candidate envelope, selectors and hash vectors (§§5, 11.3).
3. Build capture and the two admission commands in the shared Application boundary;
   reuse research domain construction in the same UoW (§12.3).
4. Implement SHARE-first writes, immutable receipts and lock-free snapshot reads
   (§12.2). A second transaction around ordinary create is forbidden.
5. Add the focused tests, demonstrate G2's saved binding after restart, record
   results, and stop (§§8–9, 12.4–12.5).

Five review rules:

1. Native `candidate-v1` emits open-question strings and **no hypotheses**. Never
   manufacture a native hypothesis output to make G2 pass.
2. Bind exact frozen artifact bytes, candidate position, original text, adaptation,
   actor and exact new version IDs. A topic, current pointer or ordinary create
   result alone proves no promotion.
3. Validation and explicit OWNER/RESEARCHER admission establish a DRAFT only;
   Agent output, confidence and authority establish no scientific truth.
4. Admission and its receipt commit together. Historical replay returns the saved
   admission, even after the resulting draft changes; it never creates again.
5. Reads take one REPEATABLE READ snapshot with no explicit locks. Writes acquire
   the entire specified SHARE set as their first SQL statement.

**Scope:** this document is a proposal, not an ADR, architecture freeze, execution
pack, migration authorization, B02 acceptance or Phase 2 gate success. This revision
changes only B02, B03 and their shared ADR draft. Proposed names and policies below
describe future work explicitly.

## 1. Purpose, authority and inspected baseline

| Governing source | Constraint carried here |
| --- | --- |
| [Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), scientific invariants and Application boundary | One owner per fact; Human/Agent share commands; Hypothesis differs from Claim; immutable formal history and exact provenance. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A1 | Generic AgentPromotionRecord is Phase 3. B02 must not introduce AgentExecution or that generic record early. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), research and Phase 2 artifact rows | ResearchQuestion/Hypothesis own scientific versions; ResearchBrief is an ArtifactVersion role. |
| [Cross-phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), invariants, Application and strategy compatibility | Additive contracts, concrete FKs, unchanged Phase 1 material hashes; replaceable strategies do not own science. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§8–9, transaction boundary, G2 | ResearchBrief uses existing Artifact; all native outputs remain candidates until Application admission; external work stays outside DB transactions. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), roles and artifact boundaries; [Identity R2 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md); [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Contextual effective project roles, verified identity, fresh post-wait DB time; authority cannot validate scientific facts. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md) | Keep Phase 1 scientific hashes unchanged; candidate artifact hash is an exact-byte hash, not a scientific support hash. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 9–10, 15, 17 | Candidate → validation → explicit command; identifiable strategy provenance; no parallel canonical strategy schema. |
| [B30 §2 G2](B30_PR2-19_Remaining_Rows_Contract_DRAFT.md), [B01](B01_Search_Result_Resolution_Contract_DRAFT.md) | G2 lacks binding/authority/replay ownership. B01 supplies exact result resolution, not promotion or evidence verification. |

Inspected implementation, rather than historical draft inventories, is the baseline:

- [native_research_strategy.py](../../src/researchbase/application/native_research_strategy.py):
  `native-storm-like` / `candidate-v1`, three perspectives; open questions are
  strings; `hypothesis_candidates` is `tuple[()]` and always empty. Failed retrieval
  can still produce a valid open question. Warnings and limitations are retained.
- [commands.py](../../src/researchbase/application/commands.py): ordinary
  `create_research_question` and `create_hypothesis` allocate identity/version,
  create version 1 DRAFT and commit their own UoW. They have no candidate binding
  or replay receipt. Do not call those public methods inside B02 admission.
- [research.py](../../src/researchbase/domain/research.py) and
  [artifact.py](../../src/researchbase/domain/artifact.py): existing typed domain
  constructors, mutable DRAFT material, frozen artifact bytes and version states.
- [B01 service](../../src/researchbase/application/search_result_resolution.py)
  and [repository](../../src/researchbase/persistence/search_result_resolution_repository.py)
  already exist. Its exact frozen source resolution does not authenticate a brief.
- [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py)
  and [decision_repository.py](../../src/researchbase/persistence/decision_repository.py)
  supply protected SHARE snapshots; [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
  supplies immutable rows and deferred closure guards. Use their mechanisms.
- [G2 candidate tests](../../tests/integration/phase2/test_pr2_19_candidates.py)
  currently prove candidate-only output and zero scientific delta. Preserve them.

No B02 execution pack exists in this proposal. Implementation must reconcile the
actual head and these dependencies again; source presence is not acceptance.

## 2. Scope, dependency boundaries and non-goals

Propose three commands: capture a service-executed native result, admit one open
question, admit one **researcher-adapted brief section** as a hypothesis. Add three
exact-ID reads. All are Application-only; public API/CLI activation is deferred.

Capture stores a frozen `research_brief` ArtifactVersion and narrow attribution/
source relations. Admission stores a typed relation to the exact resulting DRAFT.
These are existing Artifact + Relation patterns, not new top-level scientific
entities or a new persistence mechanism. Their bounded DDL still requires owner
architecture approval. No generic promotion or execution subsystem is proposed.

B01 remains a prerequisite for the full search-resolution route; B02 never invokes
its writes implicitly. Native execution already consumes explicit SourceVersions,
so capture may use an authorized preselected corpus without inventing search-run
IDs or claiming every native call has a LiteratureSearchExecution. G1 and G2 remain
distinct. Source/result links, if used to construct the corpus, remain B01-owned.

## 3. Invariants and conservative judgments

1. Capture runs the configured native implementation itself. Neither a submitted
   `ResearchStrategyResult`, arbitrary existing ArtifactVersion, nor metadata
   claiming a strategy revision can enter the capture relation. Store the actual
   request/result and derived implementation IDs. This proves attributable local
   execution, not the truth of provider statements.
2. Frozen capture artifact is project-owned, `artifact_type='research_brief'`,
   `media_type='application/json'`, CAS bytes/hash verified. Its envelope retains
   the plan, brief sections, warnings, limitations, open questions, empty hypothesis
   list and execution metadata. Store exact source membership with concrete FKs;
   do not rely on UUID strings inside the artifact for relational integrity.
3. Only `open_question_candidates[index]` admits a question. Only
   `research_brief_candidate.sections[index]` with nonnull `answer_candidate`
   admits a researcher-adapted hypothesis. Retain source text unchanged alongside
   proposed text and a mandatory validation/adaptation rationale. Question text
   is the normalized selected string; a hypothesis statement is explicitly caller
   authored. No endpoint treats brief prose as an emitted native hypothesis.
4. An empty list or out-of-range index denies admission. Failed retrieval and
   missing evidence may yield admissible questions; a section with no answer
   cannot yield a hypothesis. Contradictions, missing evidence and all warnings
   remain visible, never silently omitted or converted into support.
5. Active verified OWNER/RESEARCHER in the same active project may capture/admit;
   Human and Agent follow identical policy. Attribution distinguishes capture
   actor from admitting actor. No independent reviewer, Decision or Approval is
   required for DRAFT creation. Their absence must not be described as verification.
6. Every new admission rechecks current project access, exact artifact/source
   closure, bytes/hash and source lineage usability using B01's existing source
   predicate. No new general validity traversal is implied. No evidence relation,
   LiteratureSupportSnapshot, review, grant, Claim, ExperimentSpec or Run is made.
7. Each admission creates one new identity, version 1 DRAFT, current pointer and
   immutable receipt in one UoW. Scientific `content_hash`, `hash_scheme` and
   `frozen_at` remain NULL. Receipt hash is admission history, not a frozen
   scientific-version hash. Normal later draft editing/freezing remains available.
8. One question admission per capture/index; one adapted hypothesis admission per
   capture/section. Different actors cannot race to mint duplicate targets. A
   corrected interpretation uses normal research revision or a new capture;
   no receipt update, replacement winner or automatic backfill is allowed.

## 4. Proposed commands, DTOs and historical readback

| Method | Inputs/result |
| --- | --- |
| `capture_native_strategy` | VerifiedPrincipal plus CaptureNativeStrategyCommand; execute outside transaction, then save artifact/bindings atomically; return CaptureReadback. |
| `promote_strategy_question` | Principal plus PromoteStrategyQuestionCommand; return StrategyQuestionAdmission. |
| `promote_strategy_hypothesis` | Principal plus PromoteStrategyHypothesisCommand; return StrategyHypothesisAdmission, explicitly labeled researcher adaptation. |
| `get_strategy_capture`, `get_strategy_question_promotion`, `get_strategy_hypothesis_promotion` | Principal plus ExactStrategyQuery; exact immutable readback, no current-pointer substitution. |

All current project reader roles (OWNER, RESEARCHER, REVIEWER, APPROVER, VIEWER)
may read receipts and accessible capture material. For command replay additionally
require the original command actor, then compare normalized request material;
other actors receive FORBIDDEN before material comparison. Losing writer role
alone does not defeat an entitled original actor's historical replay. Losing read
entitlement or credential does. Cross-project/missing IDs give the same NOT_FOUND.

Return admission-time material, original IDs, actor, time and hash after a draft
is edited, frozen, superseded or abandoned. Do not reapply current source usability
or writer gates on historical reads/replay. Still verify saved immutable artifact/
receipt hashes and FKs; corrupt history fails closed. A separate ordinary research
read obtains current science. Uncertain commit recovery uses the same command ID.

## 5. Proposed migration — four typed capture/source/admission relations

The proposed migration adds `strategy_candidate_captures`,
`strategy_candidate_sources`, `strategy_question_admissions` and
`strategy_hypothesis_admissions`, with the constraints, indexes and guards in §12.1;
it adds no columns to existing tables.
None is registered in Registry 03 or Field Contract 13. Reusing the Relation
pattern does not authorize a new table: [ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md)
asks four separate Architecture Questions under AGENTS.md §4. No migration is
implemented or authorized here.

| Proposed table | Existing representation tried; missing fact and disposition |
| --- | --- |
| `strategy_candidate_captures` | Reuse the frozen ResearchBrief ArtifactVersion for all output bytes. `literature_search_executions` owns a frozen search plan/query/result lifecycle, not the native strategy result over a preselected corpus. Native `ResearchStrategyResult` is transient; artifact creator/hash alone does not bind a capture request to an actually service-executed strategy/revision. Retain one immutable request/attribution-to-artifact relation, also the capture receipt; do not add a native execution entity. |
| `strategy_candidate_sources` | SourceVersions already own source material; existing query/result resolutions bind search hits, not this capture's exact corpus, which can omit search entirely. UUIDs in an artifact cannot enforce source FKs or enumerate protected relational membership. Retain only capture → exact SourceVersion pairs, sealed at capture; no copied sources or second source owner. |
| `strategy_question_admissions` | Question versions own editable scientific text and creator/time, not capture/index, validation or immutable initial text. Search records and ArtifactVersion have no typed question-output FK. Retain one typed origin → exact new question-version relation that also serves as its receipt. |
| `strategy_hypothesis_admissions` | Hypothesis versions and optional question parent likewise lack the selected brief section/adaptation and replay binding. Retain one typed origin → exact new hypothesis-version relation/receipt, distinct from question selection; no separate strategy command-receipt table. |

### 5.1 Shared B02/B03 admission convention

Both drafts name the records `StrategyQuestionAdmission`,
`StrategyHypothesisAdmission` or `DiscussionHypothesisAdmission`, with
`admitted_by`, `admitted_at`, exact `*_version_id` outputs and retained
`question_text` / `statement`, `expected_direction` where supported, and `rationale`.
These fields always mean admission-time material, never the current draft.
Both use one immutable typed origin-to-output relation, atomically created with
version 1 DRAFT, request serialization, original-actor/read-entitled replay,
normalized request comparison, changed-input IDEMPOTENCY_CONFLICT and
cross-request candidate DUPLICATE_CONTENT. Replay never reruns admission or create.

Provenance in both is concrete RESTRICT FKs to exact saved versions, with hashes
verified from those immutable inputs and exact CAS bytes; no current pointer or
JSON-only reference substitutes. The output DRAFT's version ID is historical
creation provenance, not a FrozenReference or a claim of immutable draft content.
Initial material lives in the immutable admission, outside scientific hash payloads.

Necessary differences: B02 has no existing command receipt owner, so admission
`id` is the command ID and the relation doubles as receipt; request material is
reconstructed from retained fields. B03 reuses its existing scoped receipt's
`input_hash`, and `receipt_id` is the admission's PK/FK; its request_id is not the
receipt ID. Do not add another receipt table or a redundant output FK to that
receipt. B02 selects an ordered frozen candidate/section; B03 hashes manual
extraction from a sealed turn. B02 allows verified Human/Agent writers and an
optional question identity as organizational parent (not frozen question basis);
B03 preserves HUMAN-only authority and requires an exact frozen session question
version. B02 requires trimmed adaptation rationale and fixes expected_direction
null; B03 preserves discussion NFC/whitespace rules and optional direction/rationale.
These origin-specific policies are not a shared validation or authority expansion.

### 5.2 Literal material

Capture's exact UTF-8 canonical JSON envelope has exactly these top-level keys:
`schema='b02-native-capture-v1'`, `project_id`, `request`, `result`. Request fields
are `topic`, UUID-sorted `source_version_ids`, `max_evidence_candidates`; result
fields are exactly the fields of ResearchStrategyResult and recursively its
current dataclasses. Serialize UUIDs canonically and UTC times with existing
`format_utc`; preserve result tuple order, warnings, duplicate question text and
nulls. Reject unknown fields. Freeze bytes once; do not reserialize old captures
with a newer serializer. This closed artifact format is not semantic JSON storage
for canonical research or relations.

ArtifactVersion.content_hash is `sha256_bytes(envelope_bytes)`. New relation hashes
use `sha256_canonical_json` / `sha256-cjson-v1`. Literal material builders:

- Capture: `{type:'StrategyCandidateCapture', material_version:1, id, project_id,
  artifact_version_id, artifact_content_hash, topic, source_version_ids,
  max_evidence_candidates, strategy_id, strategy_version, captured_by, captured_at}`.
- Question: `{type:'StrategyQuestionAdmission', material_version:1, id, project_id,
  capture_id, capture_content_hash, candidate_index, candidate_text, question_text,
  rationale, research_question_id, research_question_version_id, admitted_by, admitted_at}`.
- Hypothesis: `{type:'StrategyHypothesisAdmission', material_version:1, id, project_id,
  capture_id, capture_content_hash, candidate_index, candidate_text, statement,
  rationale, research_question_id, hypothesis_id, hypothesis_version_id,
  admitted_by, admitted_at}`. Optional question ID is serialized as null when absent.

Braces above specify exhaustive JSON keys; identifiers/times become strings,
index/count become integers. Type tags are serialization labels, not entity types.
Capture's source set is UUID-sorted; all other fields are scalar. The matching
command fields excluding `id` are replay request material; saved actor, time,
allocated IDs and artifact hash are server results, never caller assertions.
Capture replay compares its request, not a fresh nondeterministic provider output.

## 6. Error contract — proposed use of existing categories

§11.2 pins transports. No new ErrorCode enum member or mapping is needed. Validate
DTO shape before I/O; authenticate and authorize before exposing any saved basis.
Named SQL constraints map via driver metadata, never exception message parsing.
Do not translate all integrity errors or timeouts into idempotency conflicts.

## 7. Transactions, concurrency and failure recovery

Capture follows Phase 2's bounded external-work pattern: an authorized lock-free
snapshot preflight checks replay and request source access; close it; execute the
native strategy/RAG outside transactions; put exact bytes in existing CAS; open
one write UoW, reauthorize and persist artifact plus capture/source rows together.
Concurrent/restarted capture attempts may repeat provider calls before a receipt
exists; there is no exactly-once external-call promise. At final admission the
first committed matching request wins; discard the losing output and return the
saved result. Unreferenced CAS bytes may remain on failure under existing store
semantics; no canonical partial artifact/binding is allowed. No reservation,
queue, lease or fake SearchExecution is added.

Question/hypothesis admission performs no external call or separate create
transaction. Generate result IDs inside the successful UoW. Use one DB-derived admission time
for receipt and initial research identity/version creation. Capture likewise uses
one DB-derived time for its attribution and artifact creation/freeze. Exact write/read
protocols are §12.2. Retry only SQLSTATE 40001/40P01, three total fresh-UoW attempts,
no delay; redo reads, locks and DB-time authorization each time. Capture persistence
retries reuse the already obtained candidate bytes, without another provider call.
Do not retry business duplicates, timeouts, connection failure or uncertain commit.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 is the test inventory. Tests must prove the complete persisted G2 suffix,
not merely that ordinary create accepts prose. Candidate execution's zero
scientific delta and admission's exact positive delta are separate assertions.
Use real PostgreSQL 18, existing disposable databases, real CAS and independent
connections for races. No SQLite or in-memory replay substitute.

## 9. Acceptance criteria and evidence boundary

Owner approval and separate execution authorization precede any build. B02's
bounded acceptance needs exact saved native revision/output, selected candidate,
validation/adaptation, actor, target DRAFT and restart replay; atomic rollback,
authority/race checks and unchanged scientific hashes must pass. The adapted
hypothesis path must be labeled as such in G2 evidence. It does not prove native
hypothesis generation, independent audit, formal support or full Phase 2 exit.
Record exact commands/counts and open P0/P1 findings; do not declare success with
such findings. The owner's loop runs the full suite; focused work does not.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Capture | Attributable saved native result in an existing frozen ResearchBrief ArtifactVersion, with typed source bindings. |
| Candidate index | Zero-based position in the saved open-question list or brief section list; equal text at different positions stays distinct. |
| Admission / promotion | Explicit Application command making a selected candidate a new canonical DRAFT and retaining immutable provenance. |
| Adaptation | Caller-authored hypothesis statement based on an exact saved brief section; not an emitted native hypothesis. |
| Validation | Structural, access, closure and declared rationale checks; no claim of scientific truth or independent review. |
| Receipt | Immutable typed admission relation, not a new scientific entity or Phase 3 AgentPromotionRecord. |
| Replay | Authorized exact return of committed material without repeating its effect. |
| CAS / UoW / G2 | Existing content-addressed ArtifactStore / transaction boundary / strategy-to-research golden-path row. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Pin Application-only capture, two admissions and three reads; native `candidate-v1`
only. Question selector is OPEN_QUESTION; hypothesis selector is BRIEF_SECTION
adaptation. These two literals name separate DTOs, not a generic target enum.
Capture requires the configured native implementation, not caller results. Keep
four narrow relation tables (§12.1), no top-level canonical schema, generic JSON
owner, dependencies or new infrastructure. Owner approval must include these
relations and the explicit adaptation policy; absence of native hypotheses remains
visible. No implementation choice is intentionally delegated to an unspecified
future policy engine.

### 11.2 Pinned error mappings

These match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); they constrain any separately
authorized future adapters, not new routes in this slice.

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong/extra fields, strict types/bounds, invalid selector/index or empty selected answer. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing trusted principal. |
| FORBIDDEN | 403 | 3 | Credential/read/write authority denied, inactive writer project, other-actor replay or inaccessible source. |
| NOT_FOUND | 404 | 3 | Missing or wrong-project capture/receipt/question parent. |
| SOURCE_VERSION_NOT_FOUND | 404 | 3 | Missing exact source after access check. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Nonfrozen capture/source basis. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Wrong-project closure, source unusability for new admission, substituted bytes/hash or corrupt saved binding. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Entitled original actor reuses same command ID with changed material. |
| DUPLICATE_CONTENT | 409 | 4 | Different command ID reuses the same capture/selector/index. |
| IMMUTABLE_RECORD | 409 | 4 | Receipt/capture relation UPDATE or DELETE, late source binding. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Sanitized concrete FK failure. |
| CONCURRENT_MODIFICATION | 409 | 4 | Three exhausted serialization/deadlock attempts. |
| ADAPTER_UNAVAILABLE | 503 | 5 | Native capability unavailable before a valid result; individual handled RAG failures remain saved warnings. |
| INTERNAL_ERROR | 500 | 1 | Existing sanitized unexpected-error fallback; not an ErrorCode enum member. |

Proposed guard SQLSTATE P22B1 maps to IMMUTABLE_RECORD; P22B2 maps to
PROVENANCE_CLOSURE_VIOLATION. Pin only after verifying no collision at build time.
Unique names in §12.1 distinguish candidate duplicates from request PK races.
After a PK race, reauthorize and read in a fresh UoW before replay classification.

### 11.3 DTO fields, Python types and limits

Frozen slotted dataclasses; strict Python UUID/int (reject bool), canonical UUID
wire strings if adapters are later built. Principal is a separate trusted argument,
never a command field. Reject unknown keys and caller actor/time/hash/status IDs.

| DTO | Exhaustive fields |
| --- | --- |
| CaptureNativeStrategyCommand | `id: UUID`, `project_id: UUID`, `topic: str`, `source_version_ids: tuple[UUID, ...]`, `max_evidence_candidates: int = 20`. |
| PromoteStrategyQuestionCommand | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `candidate_index: int`, `rationale: str`. |
| PromoteStrategyHypothesisCommand | Same five fields plus `statement: str`, `research_question_id: UUID \| None = None`. |
| ExactStrategyQuery | `id: UUID`, `project_id: UUID`. |
| CaptureReadback | `id: UUID`, `project_id: UUID`, `artifact_version_id: UUID`, `artifact_content_hash: str`, `topic: str`, `source_version_ids: tuple[UUID, ...]`, `max_evidence_candidates: int`, `strategy_id: Literal['native-storm-like']`, `strategy_version: Literal['candidate-v1']`, `captured_by: UUID`, `captured_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`. |
| StrategyQuestionAdmission | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `capture_content_hash: str`, `candidate_index: int`, `candidate_text: str`, `question_text: str`, `rationale: str`, `research_question_id: UUID`, `research_question_version_id: UUID`, `admitted_by: UUID`, `admitted_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`. |
| StrategyHypothesisAdmission | Same common admission fields; replace `question_text` and question-version ID with `statement: str`, `hypothesis_id: UUID`, `hypothesis_version_id: UUID`; `research_question_id: UUID \| None`; all remaining fields unchanged. |

Times are aware UTC; hashes are 64 lowercase hex. Topic is stripped, NFC, nonblank
1–255 characters. Rationale and hypothesis statement are NFC, outer-trimmed,
control/surrogate-free, 1–16,000 characters; preserve interior whitespace. Selected
original text remains byte-faithful in the artifact/receipt. Derived question text
uses the same normalization and 16,000-character admission bound. No arbitrary
scope/success-criteria JSON: question scope and hypothesis expected_direction/
success_criteria are NULL; rationale is the command rationale. No confidence enum.

Sources: 1–100 unique UUIDs, canonical sorted set. max_evidence_candidates: 1–100,
matching the existing RetrievalConstraints range. Index: 0–999 and in actual
saved list; cap each candidate/section list at 1,000 on capture. Envelope ≤8 MiB;
reject oversize without truncation. Reuse existing native/RAG field validation;
these additional capture bounds are proposed local admission limits. Unsupported
strategy versions require a contract amendment, never an automatic serializer upgrade.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Allocate `migrations/versions/<next_revision>_b02_strategy_admission.py` from the
actual head. This is proposed DDL, not existing tables. All omitted nullability
is NOT NULL. All FKs use ON DELETE RESTRICT. No ORM objects cross the boundary.

```sql
CREATE TABLE strategy_candidate_captures (
  id UUID CONSTRAINT pk_b02_capture PRIMARY KEY,
  project_id UUID NOT NULL CONSTRAINT fk_b02_capture_project REFERENCES projects(id) ON DELETE RESTRICT,
  artifact_version_id UUID NOT NULL CONSTRAINT fk_b02_capture_artifact REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  artifact_content_hash CHAR(64) NOT NULL,
  topic VARCHAR(255) NOT NULL,
  max_evidence_candidates INTEGER NOT NULL,
  strategy_id TEXT NOT NULL,
  strategy_version TEXT NOT NULL,
  captured_by UUID NOT NULL CONSTRAINT fk_b02_capture_actor REFERENCES actors(id) ON DELETE RESTRICT,
  captured_at TIMESTAMPTZ NOT NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme TEXT NOT NULL,
  CONSTRAINT uq_b02_capture_artifact UNIQUE (artifact_version_id),
  CONSTRAINT ck_b02_capture_topic CHECK (length(btrim(topic)) BETWEEN 1 AND 255),
  CONSTRAINT ck_b02_capture_limit CHECK (max_evidence_candidates BETWEEN 1 AND 100),
  CONSTRAINT ck_b02_capture_strategy CHECK (strategy_id='native-storm-like' AND strategy_version='candidate-v1'),
  CONSTRAINT ck_b02_capture_hash CHECK (content_hash ~ '^[0-9a-f]{64}$' AND artifact_content_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1')
);
CREATE TABLE strategy_candidate_sources (
  capture_id UUID NOT NULL CONSTRAINT fk_b02_source_capture REFERENCES strategy_candidate_captures(id) ON DELETE RESTRICT,
  source_version_id UUID NOT NULL CONSTRAINT fk_b02_source_version REFERENCES source_versions(id) ON DELETE RESTRICT,
  CONSTRAINT pk_b02_sources PRIMARY KEY (capture_id, source_version_id)
);
```

The two admission tables have the following exact column/type layout. `?` denotes
NULL allowed. This notation avoids duplicating the shared columns in SQL.

| Table | Columns |
| --- | --- |
| `strategy_question_admissions` | `id UUID PK`, `project_id UUID`, `capture_id UUID`, `capture_content_hash CHAR(64)`, `candidate_index INTEGER`, `candidate_text TEXT`, `question_text TEXT`, `rationale TEXT`, `research_question_id UUID`, `research_question_version_id UUID`, `admitted_by UUID`, `admitted_at TIMESTAMPTZ`, `content_hash CHAR(64)`, `hash_scheme TEXT`. |
| `strategy_hypothesis_admissions` | Same common columns; replace `question_text` with `statement TEXT`, replace question-version ID with `hypothesis_id UUID`, `hypothesis_version_id UUID`; `research_question_id UUID?`. |

For each table substitute prefix `b02_q` or `b02_h` in this exact constraint
inventory. Field names identify concrete references, never polymorphic soft refs.

- `pk_<prefix>` on id; `uq_<prefix>_candidate` on (capture_id, candidate_index);
  `uq_<prefix>_version` on the exact output version ID.
- `fk_<prefix>_project` → projects(id), `fk_<prefix>_capture` →
  strategy_candidate_captures(id), `fk_<prefix>_actor` → actors(id),
  `fk_<prefix>_question` → research_questions(id); q's question is nonnull.
  q: `fk_b02_q_version` → research_question_versions(id).
  h: `fk_b02_h_hypothesis` → hypotheses(id), `fk_b02_h_version` → hypothesis_versions(id).
- `ck_<prefix>_index`: candidate_index BETWEEN 0 AND 999;
  `ck_<prefix>_text`: btrim-normalized output text and rationale each have
  length 1–16000; candidate_text is nonblank (original text need not be normalized).
  `ck_<prefix>_hash`: both stored digests match lowercase 64-hex and
  hash_scheme='sha256-cjson-v1'. Application additionally enforces Unicode rules.

Indexes: `ix_b02_capture_project(project_id)`, `ix_b02_capture_actor(captured_by)`,
`ix_b02_sources_version(source_version_id)` and, on each admission table,
`ix_<prefix>_project(project_id)`, `ix_<prefix>_actor(admitted_by)`,
`ix_<prefix>_question(research_question_id)`; h also
`ix_b02_h_hypothesis(hypothesis_id)`. Unique indexes cover capture/version lookups.
Each exact output version is uniquely indexed; identity FKs are indexed above.
No unused index.

Guards, following 0042's mechanisms:

| Named guard | Exact obligation |
| --- | --- |
| `b02_capture_immutable`, `b02_sources_immutable`, `b02_q_immutable`, `b02_h_immutable` | BEFORE UPDATE/DELETE, function `b02_immutable`, P22B1. No mutable receipt lifecycle. |
| `b02_source_insert_guard` | BEFORE INSERT, function `b02_source_guard`: parent's xmin equals pg_current_xact_id(), like 0042; disallow child append after capture transaction, P22B1. |
| `b02_capture_complete`, `b02_sources_complete` | AFTER INSERT constraint triggers, DEFERRABLE INITIALLY DEFERRED, function `b02_capture_closure`: 1–100 source rows, same-project source access, exact frozen artifact/hash/type/media/actor, every source exact FROZEN/SUPERSEDED and structurally usable; P22B2. Run from parent and child so an empty child set cannot escape. |
| `b02_q_complete`, `b02_h_complete` | AFTER INSERT constraint triggers, DEFERRABLE INITIALLY DEFERRED, function `b02_admission_closure`: capture project/hash agree; exact output version belongs to referenced identity/project, is freshly inserted version 1 DRAFT, current pointer agrees, created_by/time match receipt, material equals the receipt including NULL defaults; h's optional parent question agrees with hypotheses.research_question_id and project; P22B2. |

Closure guards query without FOR UPDATE/SHARE; the write's preheld table locks
provide stability. Require the write protocol's READ COMMITTED/preheld SHARE
locks in these INSERT guards using the same catalog-inspection pattern as the
coverage capture guard in the novelty migration/repository. Guards are INSERT-only:
later legitimate research draft updates do not revalidate old admission material.
Output identities/versions must also have current-transaction xmin at admission;
ordinary existing create followed by receipt insertion in another UoW is denied.

SQL verifies typed structural closure; Application verifies CAS bytes, complete
source-set equality with envelope, hashes, selected index/text, native provenance
and authorization. SQL must not purport to execute Python or inspect the filesystem.
Force `SET CONSTRAINTS ALL IMMEDIATE` before final authorization/commit. Downgrade
locks all four tables ACCESS EXCLUSIVE in lexical order, refuses any populated
table, then drops only these objects; no deletion of scientific history. Upgrade
preserves all existing rows, hashes, migrations and enums.

### 12.2 Exact lock order and transactions

Fixed table set **S**, in this exact lexical order:

```text
actor_subject_bindings, actors, artifact_versions, artifacts,
hypotheses, hypothesis_versions, literature_source_project_links,
literature_sources, project_membership_events, project_memberships,
project_role_assignments, projects, research_question_versions, research_questions,
source_versions, strategy_candidate_captures, strategy_candidate_sources,
strategy_hypothesis_admissions, strategy_question_admissions
```

| Command | Exact ordered operations |
| --- | --- |
| capture_native_strategy, final persistence | Fresh READ COMMITTED UoW; FIRST SQL `LOCK TABLE <S in the order above> IN SHARE MODE`; then `SET LOCAL lock_timeout='10s'`, `SET LOCAL statement_timeout='30s'`; request advisory `SELECT pg_advisory_xact_lock(hashtextextended(:key,0))` with key `b02:capture:<canonical id>`; fresh clock/principal/read entitlement; exact scoped receipt/replay lookup; for new write recheck writer authority; read sources/lineage and project links UUID-sorted, verify source bytes as required by existing source closure; insert Artifact identity, frozen version, current pointer through existing repositories, capture, then UUID-sorted sources; force constraints; fresh clock and final credential/role/source checks; commit. |
| promote_strategy_question | Fresh READ COMMITTED UoW; S SHARE FIRST; same timeouts; advisory key `b02:question:<canonical id>`; fresh clock/read authorization; exact scoped receipt lookup and replay comparison; if new, writer authorization; read capture then UUID-sorted sources under S; load bounded CAS bytes and validate index/closure; check candidate uniqueness; construct/add question then DRAFT version then current pointer using existing research repositories; insert immutable question receipt; force constraints; fresh clock/final authority and source checks; commit. |
| promote_strategy_hypothesis | Same protocol with key `b02:hypothesis:<canonical id>`; after capture/source validation read optional exact parent question within S and check project; construct/add hypothesis, DRAFT version, current pointer, then hypothesis receipt; force constraints; fresh clock/final checks; commit. |
| Three exact reads; capture preflight/replay | One REPEATABLE READ read-only UoW configured before first query; clock/authenticate project reader; exact scoped parent, UUID-sorted source bindings, exact saved artifact/receipt validation; final fresh clock/credential/role check; return. No table, advisory or row locks, writes or FOR UPDATE/SHARE. Capture preflight additionally checks new-writer/source access before external execution and closes its snapshot first. |

Initial principal/DTO shape validation is in memory. No authorization query,
SET LOCAL, autoflush or advisory lock precedes S. Use connection-level operational
bounds for that first wait; later SET LOCAL cannot bound an earlier wait. Final
lock modes are acquired directly; no extra row locks or secondary advisory keys.
Existing target/current-pointer updates may acquire row locks only for newly
inserted identities. Do not call legacy authorization helpers that take row locks.

S deliberately includes write tables: concurrent SHARE holders can deadlock when
upgrading for INSERT. Use the §7 bounded retries, as in B01; do not invent different
snapshot semantics. A unique candidate loser returns DUPLICATE_CONTENT; same-ID
winners enter authorized replay. All authority/source mutations conflict with S;
scheduled expiry still requires advancing `clock_timestamp()`. After every wait
reread protected inputs using READ COMMITTED and recheck trusted credentials and
temporal roles. Constraint forcing moves its waits before the final check. Repeat
that check if any later operation waits. Reads never use this lock protocol.

### 12.3 Ordered build steps and module paths

1. Reconcile §1 and the actual migration head; approve bounded relation DDL.
   Add only the forward migration of §12.1. Do not edit governing architecture
   or accepted migrations to manufacture approval.
2. Create `src/researchbase/domain/strategy_candidate_promotion.py` for closed
   selectors, normalization, typed records and literal hash builders. Reuse
   `foundation/canonical_json.py`, `foundation/hashing.py` and domain/research.py.
   No SQLAlchemy, provider, transport or ArtifactStore import in Domain.
3. Create `src/researchbase/application/strategy_candidate_promotion.py` for the
   §11.3 DTOs/service, configured NativeResearchStrategy invocation, bounded
   artifact serialization and protected admission. Share pure research object
   construction with `application/commands.py` only where necessary; never call
   its committing create methods or change their existing contract. Use existing
   ArtifactStore/repositories, verified principal and credential interfaces.
4. Extend `src/researchbase/application/ports.py` with narrow typed repository/UoW
   ports. Create `src/researchbase/persistence/strategy_candidate_promotion_repository.py`
   for S, protected authority/closure reads, relations and constraint forcing.
   Wire `src/researchbase/persistence/uow.py`, isolated SQLSTATE/constraint mapping
   and bounded retries. Preserve ordinary research create/freeze behavior.
5. Wire service construction in `src/researchbase/cli/composition.py` and test
   composition as needed; this does not add CLI commands or HTTP routes.
   Existing `api/errors.py` / `cli/errors.py` mappings stay unchanged.
6. Add §12.4 tests; extend `tests/integration/phase2/test_pr2_19_candidates.py`
   with the independently inspectable persisted G2 suffix after authorization.
   Record exact results and limitations; stop without implementing §12.5.

### 12.4 Test artifacts and required cases

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b02_strategy_promotion_contract.py` (new) | Every closed DTO/type/bound; bool/unknown fields, NFC and controls, stable source sorting, duplicate question text by index, empty/out-of-range selectors; no native hypothesis list; explicit adaptation/null defaults and enum literals; exact transport mapping table. |
| `tests/unit/phase2/test_b02_strategy_promotion_hashes.py` (new) | Independent literal envelope/three relation hash vectors, Unicode/null/time/order, byte substitution and changed material; no reuse of production builders as expected oracle; unchanged Phase 1 vectors. |
| `tests/integration/phase2/b02_support.py` (new) | PG18 disposable migrated fixture, real CAS, configured native strategy/scripted RAG, two projects, verified Human/Agent writers/readers and separate capture/admission actors; two engines/backend PIDs for races. |
| `tests/integration/phase2/test_b02_strategy_capture.py` (new) | Real native run and artifact read after restart, exact revisions/limitations, source membership and handled retrieval failures retained; no scientific delta; reject caller-manufactured artifact/result, bad source closure, corruption/oversize/cancellation; concurrent capture first result wins, no external call in transaction. |
| `tests/integration/phase2/test_b02_strategy_admission.py` (new) | Saved question and explicitly adapted hypothesis create exact version 1 DRAFT with null hashes and concrete bindings; optional parent closure; authority parity, writer denial, wrong project, empty hypothesis output never relabeled, missing answer denied, retained warnings; ordinary create lacks promotion proof. |
| `tests/integration/phase2/test_b02_strategy_replay.py` (new) | Restart/unknown commit exact-ID recovery, actor takeover, changed normalized request, other-ID candidate duplicate; lost writer versus lost reader/credential; source later merge/retraction and target edit/freeze/abandon do not change saved historical replay; zero duplicate effect. |
| `tests/integration/phase2/test_b02_strategy_schema.py` (new) | Real catalog/types/names/FKs/indexes; clean/populated upgrade and empty/populated downgrade; UPDATE/DELETE/late child denial; force deferred guards and commit; missing children, wrong parent/project/material, ordinary existing target and unprotected capture writes denied; no scientific ON DELETE CASCADE. |
| `tests/integration/phase2/test_b02_strategy_concurrency.py` (new) | FIRST SQL S proof; same-ID/candidate races and phantom source-link revocation; capture versus admission versus ordinary create/update; credential/role/project/source mutation and scheduled expiry across waits; observed blocked backend locks; exactly three 40001/40P01 attempts, no business/timeout retries; failure at every artifact/identity/version/pointer/receipt/deferred step rolls back canonical writes. |
| `tests/architecture/test_b02_strategy_promotion_boundaries.py` (new) | Shared Application path, Domain dependency isolation, no nested commit/provider call under transaction, no read locks, no AgentExecution/AgentPromotionRecord, no generic semantic JSON or new truth owner, no evidence/governance/later-phase side effects. |

Existing regression targets: `tests/unit/phase2/test_pr2_08_native_strategy.py`,
`tests/integration/phase2/test_pr2_19_candidates.py`,
`tests/integration/phase2/test_b01_resolution_admission.py`,
`tests/integration/phase2/test_b01_resolution_replay.py`,
`tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`,
`tests/integration/phase2/test_pr2_15_decision_schema.py` and
`tests/integration/phase2/test_pr2_18_search_coverage.py`. Keep candidate-only
assertions separate from positive admission tests. Future planned command:
`uv run pytest tests/unit/phase2/test_b02_*.py tests/integration/phase2/test_b02_*.py tests/architecture/test_b02_strategy_promotion_boundaries.py`.
Run static checks, unit/architecture and these affected PostgreSQL suites; do not
run the full suite, which belongs to the owner's loop. Planned tests are not PASS.

### 12.5 Not in this slice

Native hypothesis generation or new strategy revision; automated scientific
validation, claim/support/evidence promotion, independent review, approval or
freeze; discussion promotion; new generic Agent execution/promotion/runtime;
provider persistence framework, reservations, external-effect exactly-once,
queues or background workers; public API/CLI activation; bulk promotion, editable
receipts, backfill or automatic candidate replacement; new runtime dependencies;
other backlog items, full G2/Phase 2 gate success.

## 13. Open questions for the owner — override register

Resolve the four table-specific Architecture Questions in
[ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md) before admitting any
unregistered relation. The shared admission convention is §5.1 and B03 §5.1;
there is no pending parallel-draft reconciliation or generic promotion schema.
Approve or override service-owned capture,
explicit researcher adaptation policy, source usability restriction, one admission
per candidate index and Application-only boundary. These choices are fixed in this
draft; an override requires corresponding body edits before freeze. If G2 instead
requires a genuinely emitted native hypothesis, contract a new strategy revision
separately: current `candidate-v1` cannot supply it. Pending approval authorizes no
partial implementation.

## 14. Documentation verification note

Joint B02/B03/ADR-0020 documentation revision, 2026-10-19. Only these three files
change; both proposal status lines remain unchanged and the ADR is PROPOSED.
Existing-code results below do not verify future admission behavior, migrations
or tests. No dependency sync, implementation, commit, push or branch creation.
The owner's loop runs the whole suite; this task did not run it.

| Exact command | Observed result |
| --- | --- |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check .` | All checks passed. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check .` | 736 files already formatted. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0; 0 errors, 0 warnings, 0 informations. |

Focused unit and architecture command (exit 1):

```sh
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit/domain/test_pr04_research.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/architecture -o addopts='' -q -p no:cacheprovider > /private/tmp/lane54-unit-architecture.log 2>&1
```

Observed **184 passed, 14 errors, 4 warnings in 6.28s**. The 14 PR2-19 architecture
setup errors require an explicitly configured RB_TEST_ADMIN_URL. This is not an
all-architecture PASS. The separate configured PostgreSQL run below establishes
that local socket access is unavailable in this sandbox; no database success is
inferred and no test/environment workaround was introduced.

Focused PostgreSQL regression command, combining the existing targets from both
§12.4 inventories (exit 1):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://fengwang@/postgres?host=/private/tmp' DATABASE_URL='postgresql+psycopg://fengwang@/postgres?host=/private/tmp' PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/integration/test_pr04_application.py tests/integration/test_pr04_schema.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_b01_resolution_admission.py tests/integration/phase2/test_b01_resolution_replay.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_19_discussion.py -o addopts='' -q -p no:cacheprovider --tb=short > /private/tmp/lane54-postgres.log 2>&1
```

Observed **14 failed, 73 errors, 1 warning in 12.50s**, zero passing cases.
Connections to `/private/tmp/.s.PGSQL.5432` fail with `Operation not permitted`.
PostgreSQL admission/constraint/replay verification remains unverified here;
planned B02/B03 tests do not exist yet and are not PASS.

Documentation checks: `git diff --check` returned exit 0.
`git diff --no-index --check /dev/null docs/proposals/../architecture/adr/ADR-0020-candidate-promotion-admission.md`
returned exit 1 for the new-file difference, with no whitespace diagnostics.
A focused Python check verified all 53 relative file links across
the three documents, two unchanged proposal status lines against HEAD, one AQ per
remaining table, no new existing-table column in either DDL sketch, and exactly
the three authorized paths in git status. These are documentation checks, not
approval of the proposed schema or gate success.
