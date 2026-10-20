# B30-S3 architecture questions — 2026-10-20

Status: OPEN — owner reconciliation required for the cases identified below.
The S3 approval status is preserved. Non-conflicting G2/G4 tests proceed; none
of these questions is resolved by changing production, schema, expected errors,
or marking a disputed case passed. Full PR2-19 acceptance remains BLOCKED.

## Authority and scope check

The approved S3 guide explicitly selects **two** candidate origins:
[G2 strategy](B30S3_PR2-19_Remaining_Rows_Contract_DRAFT.md#21-newly-runnable-suffixes-in-b30-s3-once-b02-and-b03-land)
uses B02 open-question and researcher-adapted brief-section admission; **G4** uses
B03 manual discussion-hypothesis admission from a bound CLOSED session.
B03-only restrictions do not apply to G2.

S3 §13 says “No architecture exceptions are proposed” and “Adopt the exact B02”
and “B03” “command names, DTOs, hash domains and lock protocols”. Its Start here
also says “No production code, migration, dependency, fault hook or other document
changes belong to this slice.” The owner's review explicitly requests these AQs.
Approval after B02/B03 landed does not say which of the incompatible literals
below replaces the other. Treating S3 as a deliberate behavior override would
require production changes, forbidden by this test-only slice. These are semantic
contract decisions, not filename or method-name substitutions.

Exact source locations (quotes are reproduced in the questions below):

| Question / candidate origin | Approved S3 guide lines | Approved owner contract lines |
| --- | --- | --- |
| AQ-S3-01, G4 discussion authority | `B30S3_PR2-19_Remaining_Rows_Contract_DRAFT.md:198`, `:487` | `B03_Discussion_Candidate_Promotion_Contract_DRAFT.md:127`, `:294` |
| AQ-S3-02, G2/G4 duplicate errors | S3 `:375`, `:486`, `:487` | B02 `:332`, `:338`; B03 `:316` |
| AQ-S3-03, G4 scientific hash (G2 broad readback) | S3 `:220`, `:244`, `:487` | B03 `:104`, `:175`; B02 `:135` |
| AQ-S3-04, G2/G4 receipt hash literals | S3 `:236`, `:241` | B02 `:229`; B03 `:195` |
| AQ-S3-05, G4 receipt/turn layout | S3 `:196`, `:421` | B03 `:366`, `:419` |
| AQ-S3-06, G2/G4 advisory lock identity | S3 `:440`, `:441`, `:442` | B02 `:495`; B03 `:461` |

The no-exceptions/adopt-owner clauses are S3 `:521` and `:524`.

## AQ-S3-01 — G4 HUMAN-only authority versus positive AGENT admission

S3 §3 invariant 6: “Both `ActorType.HUMAN` and `ActorType.AGENT` callers use the
same B02/B03 Application commands”. Its §12.4 G4 positive admission case says
“testing both HUMAN and AGENT actors”.

[B03 §4](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md#4-proposed-commands-dtos-and-historical-readback)
says “First execution requires current HUMAN OWNER or RESEARCHER”. B03 §11.1
says “Only existing HUMAN writer roles. No new agent authority.” Landed
`discussion_hypothesis.py`, `_authorize`, checks `row["actor_type"] == "HUMAN"`;
the B03 owner suite asserts AGENT admission is `FORBIDDEN`.

Decision needed: retain B03 HUMAN-only G4 and test AGENT denial, or authorize a
separate B03 authority change. G2 HUMAN/AGENT policy parity is not disputed:
B02 §3 invariant 5 explicitly says “Human and Agent follow identical policy.”
Pending: G4 positive AGENT admission. Existing legacy request_promotion denials
for both caller types remain exercised.

## AQ-S3-02 — G2/G4 duplicate-candidate and actor-scope error categories

S3 §11.2 `IDEMPOTENCY_CONFLICT` includes a target “already promoted under a
different command/request ID”. S3 §12.4 G2 also requires this error for
“different actor, or second command ID”; G4 requires it for “different
`request_id` for the same `(session_id, turn_id, candidate_hash)`”.

[B02 §11.2](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md#112-pinned-error-mappings)
assigns `DUPLICATE_CONTENT` to “Different command ID reuses the same
capture/selector/index.” Its `FORBIDDEN` row includes “other-actor replay”.
[B03 §11.2](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md#112-pinned-error-mappings)
assigns `DUPLICATE_CONTENT` to “Same candidate already admitted under another
request.” Both landed services implement these owner rules. B03 receipt identity
is actor-scoped; another actor cannot replay the original receipt as their own.

Decision needed: preserve owner duplicate/authorization categories or separately
authorize their change. Pending: distinct-ID duplicate and duplicate-loser race
assertions in G2/G4, plus disputed other-actor replay errors. Exact original-actor
replay and changed-payload IDEMPOTENCY_CONFLICT remain runnable.

## AQ-S3-03 — G4 DRAFT scientific hash

S3 §5 explicitly requires the “created `HypothesisVersion.content_hash`” computed
from a literal containing `status: "DRAFT"`. S3 §12.4 G4 case 3 repeats
“independently computed `candidate_hash` and `HypothesisVersion.content_hash`”.

[B03 §3 invariant 4](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md#3-invariants-and-conservative-judgments)
says “content_hash, hash_scheme, frozen_at are null” and “Do not alter Phase 1
hypothesis hash payloads.” B03 §5.1 says “No scientific hash is added to a DRAFT”.
B02 §3 invariant 7 likewise says “Scientific `content_hash`, `hash_scheme` and
`frozen_at` remain NULL.” The landed owner suites assert null scientific hashes.

Decision needed: remove S3's populated DRAFT scientific-hash assertion or authorize
an architecture/Phase 1 compatibility change separately. This explicit S3 literal
is a G4 requirement; §4's broader readback wording also affects G2. Pending:
scientific DRAFT hash assertions. Version 1, DRAFT, unfrozen creation and CAS
artifact byte hashes remain exercised without silently inventing a draft hash.

## AQ-S3-04 — G2/G4 independent receipt hash literals

S3 §5 names B02 `domain='StrategyCandidateCapture'`, `schema_version=1` (and
corresponding question/hypothesis domains). B02 §5.2's exhaustive literal instead
uses `type:'StrategyCandidateCapture', material_version:1` and analogous admission
type tags. These different JSON keys produce different digests.

S3 §5's exhaustive B03 candidate material is
`{expected_direction, rationale, research_question_version_id, session_id,
statement, transcript_artifact_version_id, turn_id}`. B03 §5.2's literal also
contains `schema:"discussion_hypothesis_candidate_v1"`, `project_id`, and
`success_criteria:null`. The landed hash builders follow the owner literals.

Decision needed: identify the exact canonical literal to use as the independent
oracle; this is hash semantics, not renaming a Python identifier. Pending:
independent admission/capture/candidate hash literal assertions. Independent CAS
byte digests and exact immutable readback still run.

## AQ-S3-05 — G4 receipt and turn provenance layout

S3 §12.1 requires PROMOTE_HYPOTHESIS receipt fields
“nonnull `result_session_id, result_turn_id, result_artifact_version_id`”. S3 §3
invariant 5 requires equality with “`turn.transcript_artifact_version_id`”.

B03 §12.1 specifies “Resolve the only output via the relation's
hypothesis_version_id (no output column on the receipt).” Its DDL retains
“(command_name='APPEND_TURN')=(result_turn_id IS NOT NULL)”, requiring null for
PROMOTE_HYPOTHESIS. The landed receipt has no result_artifact_version_id, and the
turn has no transcript_artifact_version_id. B03 verifies the **session-bound**
transcript and selected turn through existing typed inputs/citations and the
admission's concrete FKs, not the proposed turn field.

Decision needed: retain B03's existing typed receipt/admission/session closure or
authorize a separate schema change. Pending: the nonexistent field assertions
and mismatched-turn-transcript gate. Bound session/turn composition and CAS
closure checks remain exercised using owning Application commands.

## AQ-S3-06 — G2/G4 advisory key hashing

S3 §12.2 lines 440–442 spells advisory locks with `hashtext(...)` for B02 and
B03. B02 §12.2 line 495 specifies
`SELECT pg_advisory_xact_lock(hashtextextended(:key,0))`; B03 §12.2 line 461
also explicitly specifies `pg_advisory_xact_lock(hashtextextended(:key,0))`.
Both landed owners use the latter. The 32-bit and 64-bit hash functions produce
different lock keys, so they are not equivalent spellings of one protocol.

Decision needed: retain the owner's lock key hashing or separately authorize a
coordinated production protocol change. Pending: the conflicting advisory hash
assertions. First-statement SHARE inventories, READ COMMITTED write isolation,
lock-free read-only REPEATABLE READ, real blocked credential revocation and
same-request G4 serialization are independently exercised.

## AQ-S3-07 — G2 optional question parent versus frozen input; disclosure gates

S3 §12.4 line 486 requires `FROZEN_REFERENCE_REQUIRED` for an “unfrozen
question”. Its positive composition simultaneously admits a question as DRAFT
and links the adapted hypothesis to that new question. B02 §5.1 line 208 calls
this an “optional question identity as organizational parent (not frozen question
basis)”; B03's following line separately requires a frozen session question.
Landed B02 accordingly accepts the DRAFT parent created by the immediately
preceding question-admission command. G2's linked/unlinked happy-path tests
exercise that explicitly prescribed composition, without claiming the conflicting
unfrozen-question rejection passed.

S3 §12.4 also asks `FROZEN_REFERENCE_REQUIRED` for an unlinked G2 source and
`NOT_FOUND` for a missing G4 transcript. B02 §11.2 line 332 instead includes
“inaccessible source” under `FORBIDDEN`; the landed new-write source gate denies
access before disclosure. B03 §11.2 line 313 assigns `FROZEN_REFERENCE_REQUIRED`
to “Question not admitted/frozen or candidate's exact context mismatched.” A transcript ID different from
the session binding reaches this check before any artifact existence query.

Decision needed: distinguish G2 organizational parent from G4 frozen basis,
and reconcile precise authorization/context precedence in these three negative
cases. Missing session/turn/question/receipt, invalid selector, OPEN/unbound
session and corrupt CAS cases remain exercised with their undisputed errors.

## AQ-S3-08 — G2 AGENT fixture admission boundary

B02 §3 invariant 5 explicitly permits “Human and Agent follow identical policy”.
S3 §3 invariant 6 calls for the corresponding proven bound AGENT, while Start here
requires “Every fixture fact comes through its owning Application command in a
separate transaction.” The current identity Application provisions HUMAN actors,
requires HUMAN for legacy subject binding (`src/researchbase/application/phase2_identity.py:1374`),
and requires HUMAN for new project membership enrollment (`:630`). The existing owner AGENT tests use a direct actor-type
UPDATE, not an Application-created bound AGENT. S3 explicitly excludes that
fixture shortcut.

Decision needed: identify an existing authorized Application fixture path for a
bound AGENT, or authorize a separate identity capability. Do not SQL-forge an
AGENT binding to claim S3 parity. The HUMAN G2 positive composition and both
legacy G4 caller-type denials remain exercised; no positive AGENT admission is
claimed as S3 acceptance.

## Substitutions and implementation boundary

- Planned `test_b02_strategy_promotion.py` resolves to the existing split owner
  suites `test_b02_strategy_{capture,admission,replay,concurrency,schema}.py`.
- Planned `test_b03_discussion_promotion.py` resolves to
  `test_b03_discussion_hypothesis.py` and its `_guards.py` companion.
- `B03_SNAPSHOT_SQL` is the existing full SHARE statement; `S` and
  `B03_SNAPSHOT_TABLES` are the existing owner inventory constants. Tests use
  independent literal inventories with SQL observations.
- No new migrations or schema changes. No governing contract is silently edited.
- Dependency inventory records both landed owners as available and separately
  retains G2/G4 acceptance blockers for these questions. Availability remains
  informational and cannot pass the gate.
