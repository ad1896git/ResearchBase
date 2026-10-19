# ADR-0020 — Candidate promotion admission and typed provenance

Status: ACCEPTED — APPROVED by owner 2026-10-19 (all five tables: B02-AQ-01..04, B03-AQ-01); first slices authorized for implementation.

## Context

[B02](../../proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md) and
[B03](../../proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md) propose the missing
strategy/discussion → research DRAFT admission links. Existing native candidates
and closed discussion artifacts are not scientific truth; ordinary research
creation alone does not prove that an exact candidate was explicitly admitted.

[Registry 03](../03_Global_Schema_and_Contract_Registry_v1.0.md) and
[Field Contract 13](../13_Phase2_Schema_Field_Contract_v1.0.md) do not
register any of the five relations below. AGENTS.md §4 says **DO NOT ADD SCHEMA**
unless existing Entity + Relation + Assessment + Snapshot + Event patterns cannot
clearly express the fact and architecture review approves the change. Reusing a
Relation pattern does not itself admit its physical schema. This single draft
requests five explicit, bounded exceptions; it changes no frozen architecture,
DDL, runtime or acceptance status. Owner approval and separate execution authority
are prerequisites, not results of this documentation revision.

## Decision

### 1. Shared admission shape and existing ownership

Propose origin-specific typed `StrategyQuestionAdmission`,
`StrategyHypothesisAdmission` and `DiscussionHypothesisAdmission` records. All
retain admission-time text/rationale, `admitted_by`, `admitted_at`, concrete origin
FKs and exact output version IDs, with one new version 1 DRAFT and current pointer
in the same UoW. Research retains sole ownership of scientific material. Immutable
admission history retains initial material when the editable DRAFT changes; its
output ID is creation provenance, not a frozen scientific reference.

The common receipt/replay protocol is: serialize request; authorize original actor
with current read entitlement before comparing normalized request material; return
saved admission/IDs for a completed match; reject changed material as
IDEMPOTENCY_CONFLICT; reject another request for the same origin candidate as
DUPLICATE_CONTENT. No replay recreates science or reapplies current writer/source
eligibility. Exact reads use a single lock-free REPEATABLE READ snapshot and fail
closed on corrupt saved links/bytes. New writes require current domain authority.

B02 has no existing native-strategy receipt: its capture/admission relations double
as receipts, `id` equals command ID, and retained fields reconstruct the request.
B03 reuses `discussion_command_receipts` and its deployment/project/actor/command/
request scope and `input_hash`; the admission PK/FK is `receipt_id`, and actor/time
come from receipt actor_id/completed_at. This storage difference avoids a second
owner. No new receipt table is admitted. All input provenance uses concrete
RESTRICT version FKs and verification of the exact immutable input hashes/bytes.

B02 captures a service-executed native result, then selects an ordered question
or adapts an answered brief section; no native hypothesis is fabricated. It permits
verified Human/Agent writers, requires rationale and leaves direction null; an
optional question identity is organizational parent only, not frozen input basis.
B03 manually extracts from one sealed turn, requires its exact frozen session
question version, preserves HUMAN-only authority, and permits optional direction/
rationale. B02 trims new authored material; B03 preserves meaningful whitespace
under its existing NFC convention. These differences are explicit policies, not
permission to weaken the other domain's gates.

### 2. Architecture Question B02-AQ-01 — retain `strategy_candidate_captures`?

**Existing representation first:** reuse existing ResearchBrief ArtifactVersion
for the entire frozen native request/result envelope, including warnings and
implementation revision; no parallel brief entity. Native ResearchStrategyResult
is transient. Field Contract 13's `literature_search_executions` binds a frozen
search plan, queries and provider results, not execution of native strategy over
an explicitly selected SourceVersion corpus. That corpus need not involve a
search execution at all. An artifact hash/creator proves retained bytes and their
uploader, not that the capture command executed the configured native revision.
No existing request key links that execution claim to the exact artifact.

**Proposed separate decision:** retain one immutable relation/receipt with B02
§12.1's exact columns, unique artifact FK, capture command ID, project, normalized
request, native implementation IDs, actor/time and hash. The service must run the
native strategy itself and cannot admit a submitted result or arbitrary artifact.
Source membership is the child relation in AQ-02. This binds attributable local
execution, not the truth of the output. Reject a fake search execution, new generic
native execution entity or JSON-only request receipt. No new column on ArtifactVersion
is needed; its existing bytes/hash and attribution remain owned there.

### 3. Architecture Question B02-AQ-02 — retain `strategy_candidate_sources`?

**Existing representation first:** SourceVersions own exact source material;
search_result_resolutions owns search hit → source/version facts. Neither stores
the capture's chosen input membership. Captures C1 and C2 may select different
subsets of the same corpus without search records. Their existing ArtifactVersion
bytes can retain those UUIDs, but no existing relation enforces that those sources
exist or supplies a protected, sealed capture → SourceVersion FK set. Parsing JSON
alone would make primary-chain source links soft references.

**Proposed separate decision:** retain only `(capture_id, source_version_id)` as
concrete RESTRICT FKs with pair PK, source index and same-transaction sealing/
deferred set closure. Reuse SourceVersion facts, project links and usability
predicate. No copied source, generic source manifest entity, or second source
validity owner. Capture hash derives sorted membership from these pairs and is
checked against the frozen envelope. Do not invent search executions to populate
an unrelated relation.

### 4. Architecture Question B02-AQ-03 — retain `strategy_question_admissions`?

**Existing representation first:** ResearchQuestionVersion has editable question
text, scope, rationale and creator/time; it has no capture/index or receipt link.
After admission text A is edited to B, that version ID and creator/time cannot
reconstruct the chosen candidate, A or validation rationale. ArtifactVersion and
search outputs have no concrete research-question output FK. Existing literature
relations describe evidence/support semantics, not admission, and must not imply
that a question has verified evidence.

**Proposed separate decision:** retain B02 §12.1's immutable typed capture/index →
exact fresh question/version relation, including selected text, admitted text,
rationale, admitting actor/time and digest. It is also the command receipt, with
unique capture/index and output version. No separate receipt or initial-text
snapshot table. Ordinary create followed by a later provenance graft is forbidden.

### 5. Architecture Question B02-AQ-04 — retain `strategy_hypothesis_admissions`?

**Existing representation first:** HypothesisVersion similarly stores editable
statement/direction/criteria/rationale, not a brief section, original answer,
adaptation rationale or request binding. Hypothesis.research_question_id is an
optional organizational parent, not strategy provenance. Neither existing question
versions nor search/artifact records encode the adaptation-to-exact-output link.
The question-admission relation cannot represent a hypothesis FK or distinguish a
brief-section adaptation from an emitted open question without changing its shape.

**Proposed separate decision:** retain the separate typed capture/section → exact
fresh hypothesis/version relation/receipt in B02 §12.1, with caller-authored
statement, original selected answer, rationale, actor/time, optional question parent
and digest. One adaptation per capture/section; initial direction/criteria null.
No native hypothesis output or scientific support is implied.

A combined strategy table with concrete XOR question/hypothesis FKs is technically
possible (unlike a prohibited target_type/target_id soft reference). It cannot reuse
an existing relation and would introduce selector-dependent nullability, two output
shapes and conditional uniqueness/closure. Prefer these two narrow typed relations
with the same receipt protocol; this choice and both exceptions require owner
approval. Neither record duplicates a fact expressible by an existing table.

### 6. Architecture Question B03-AQ-01 — retain `discussion_hypothesis_admissions`?

**Existing representation first:** closed discussion sessions, sealed turns/input/
citation relations and the bound transcript ArtifactVersion already retain all
conversation history. Reuse them without discussion capture/source copies. Existing
receipts retain scoped request, actor/time and input_hash; result_session_id and
result_turn_id cannot reference HypothesisVersion. A digest alone cannot enumerate
the output or recover manual extraction A after a draft edit. HypothesisVersion's
question identity cannot recover which frozen question version/turn/transcript was
selected or its immutable initial material. Existing provenance relations have
other owners/semantics; neither a discussion citation nor a LiteratureEvidenceRelation
is an admission.

**Proposed separate decision:** retain one research-owned immutable relation with
receipt_id PK/FK, exact project/session/turn/transcript/question-version/output FKs,
candidate_hash and initial statement/direction/rationale. Follow B03 §12.1's concrete
FKs, same-transaction fresh-output closure and candidate/output uniqueness. Derive
hypothesis identity, admitted_by and admitted_at through existing version/receipt;
do not add duplicate columns for them. Extend the existing receipt command CHECK
for PROMOTE_HYPOTHESIS, add its composite context UNIQUE and deferred bidirectional
completeness guards. Every PROMOTE receipt has exactly one admission; an admission
must reference a PROMOTE receipt. Preserve all historical commands and receipts.

**Column withdrawn:** do not add `discussion_command_receipts.result_hypothesis_version_id`.
The path receipt.id → admission.receipt_id → admission.hypothesis_version_id already
resolves the exact unique output. A second FK and equality guard duplicate it.
There are no remaining new columns on existing tables, so no column Architecture
Question is requested. All columns of the five new relations are bounded by their
respective table question and the drafts' §12.1 inventories.

### 7. Hash/material impact and Phase boundary

B02 §5.2 proposes a new closed `b02-native-capture-v1` exact-byte artifact envelope
and new v1 capture/admission material digests (`sha256-cjson-v1`). They bind request,
exact artifact/capture hash, selector, retained original/adapted text, attribution
and exact output IDs, with sorted source membership. Its hypothesis type tag is
`StrategyHypothesisAdmission`, consistently with the record name. These are new
proposal formats; no accepted digest or artifact is reserialized or rehashed.

B03 §5.2's new versioned candidate digest binds exact project/session/turn/transcript/
question IDs and retained initial material. Its existing receipt input_hash pattern
binds command/project/session/candidate_hash; scope binds actor/request separately.
No new admission hash column is needed: recompute candidate and request hashes from
saved relation/receipt fields and verify referenced frozen input hashes/CAS bytes.
B02's combined relation/receipt digest includes server results; B03's existing
input_hash is request-only. Do not substitute one for the other or claim either is
a scientific support hash. Neither draft changes Phase 1 or Contract 15 scientific
payloads: output DRAFT content_hash/hash_scheme/frozen_at remain null. Later legal
draft edits/freezes never rewrite the admission or change replay's initial material.

[Addendum 02 A1](../02_Final_Architecture_Correction_Addendum_v1.0.md)
and Registry 03 assign AgentPromotionRecord to Phase 3 agent_runtime, with execution
and validated target provenance. Neither proposal builds that runtime/execution
subsystem now. B03 is human admission; B02's identifiable native strategy artifact
is not AgentExecution. A generic promotion record would pull later-phase schema
forward and introduce a second provenance owner. Use existing research/artifact/
discussion owners plus only the explicitly approved typed relations above.

## Consequences

Proposed total: four new B02 tables, one new B03 table, and no new column on an
existing table. Receipt constraints/guards change only for B03's new command;
existing receipt/history hashes remain unchanged. No frozen numbered architecture
is silently amended. Owner approval must explicitly admit each question and its
§12.1 inventory before separately authorizing forward migrations at the actual head.
Downgrades refuse populated new history; no backfill, scientific deletion or
rewriting accepted migrations. This ADR does not authorize schema expansion by
analogy or establish implementation/Phase 2 gate success.

Future verification must include real PostgreSQL 18 upgrade/constraint/rollback/
race/restart/replay and populated-downgrade refusal, independent literal hash
vectors, later draft mutation, exact input corruption and authority checks, plus
unit/architecture/static regressions listed in both drafts. Current-code regression
results cannot prove these unimplemented admissions.

## Alternatives

- Ordinary create plus prose provenance or artifact UUID lists: cannot enforce
  the exact typed origin/output link, preserve initial material or prevent replay
  duplication. Existing Snapshot/Event/Assessment records have specific owners;
  no registered generic event payload supplies these concrete FKs. A new generic
  JSON event would merely move the missing schema and violate the semantic-core rule.
- New question/hypothesis provenance columns: would need separate immutable
  origin/initial-material fields and guards alongside editable DRAFT fields. This
  changes a wider established scientific contract than these sealed relations.
- Reuse literature search executions/results or evidence relations: falsely claims
  a search lifecycle or scientific evidence for preselected native inputs/manual
  discussion extraction. Reuse their facts only where they actually apply.
- Extra capture/source tables for B03: existing discussion seals and transcript
  binding already express those facts. Dropped rather than duplicating them.
- Extra strategy receipts or B03 output column: redundant with the combined B02
  receipts and the B03 receipt → admission → output path; not admitted.
- One generic target_type/target_id promotion table or Phase 3 AgentPromotionRecord:
  breaks concrete provenance or phase discipline. A concrete-XOR combined B02
  relation is possible but rejected for the selector/output complexity in AQ-04.
- Freeze output on admission: changes the requested DRAFT behavior and conflates
  explicit candidate admission with scientific validation. Immutable initial
  material belongs to the admission history, not a forced scientific freeze.
