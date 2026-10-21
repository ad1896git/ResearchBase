# Remaining PR2-19 Rows, Third Slice (B30-S3) Contract — DRAFT

**Status: APPROVED by owner 2026-10-20 — first slice authorized for implementation**

## Start here (for the implementer)

This is a test-only continuation of [B30](B30_PR2-19_Remaining_Rows_Contract_DRAFT.md)
and [B30-S2](B30S2_PR2-19_Remaining_Rows_Contract_DRAFT.md), not approval to
implement it. B30 S1 and S2 stay intact. Owner-approved
[ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md),
[B02](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md) and
[B03](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md) are being
implemented now to supply explicit candidate-admission receipts for native
strategy output and bound discussion turns. Once B02 and B03 land, the G2 and G4
suffixes in §2 become runnable, not passed. Every other blocked PR2-19 row
after B30-S2 is inventoried in §2 with its unblocking owner. The full PR2-19
gate remains BLOCKED.

After separate owner authorization (and after B02 and B03 land):

1. Reconcile `G2` and `G4` in `tests/integration/phase2/test_pr2_19_dependencies.py`;
   preserve `HISTORICAL_BLOCKED_ROWS`, `availability_is_acceptance = False` and
   fail-closed `require_full_gate`. Keep every remaining blocker in §2.2 explicit.
2. Reuse `tests/integration/phase2/pr2_19_support.py`, `b30_observations.py`,
   `b02_support.py` (when B02 lands) and the PR2-10 discussion fixtures. Extend
   `test_pr2_19_candidates.py` and `test_pr2_19_discussion.py`; do not build a
   second scenario/report framework or treat owner unit/integration suites alone
   as PR2-19 E2E acceptance evidence.
3. Compose G2 (`capture_native_strategy` → `promote_strategy_question` /
   `promote_strategy_hypothesis` → exact readback) and G4 (bound session/turn →
   `promote_discussion_to_hypothesis` → `get_discussion_hypothesis_admission`),
   retaining the negative candidate-isolation and `request_promotion` denial
   controls. Every fixture fact comes through its owning Application command in
   a separate transaction.
4. Observe the exact lock protocols in §12.2, independently constructed
   `sha256-cjson-v1` digests and CAS bytes, fresh service readback after restart,
   and command-level `StateDelta` counts. Verify that read paths take zero table,
   advisory or row locks inside one read-only `REPEATABLE READ` snapshot.
5. Run focused checks and record exact commands, counts and remaining blockers.
   Stop at these two suffixes; the loop runs the full test suite.

Review rules: candidate output and discussion turns are never scientific truth
by themselves; promotion creates only `DRAFT` `ResearchQuestion` or `Hypothesis`
roots (`version_number = 1`, `frozen_at IS NULL`) plus an immutable admission
receipt, never `Claim`, `literature_evidence`, `ScientificConclusionVersion` or
approval/release state. No SQL-forged captures, turns, bindings or admissions.
No production code, migration, dependency, fault hook or other document changes
belong to this slice. A passing suffix cannot pass an unrun or still-blocked row.

## 1. Purpose, authority and inspected baseline

Read `AGENTS.md`, architecture 01 → 02 → 03 → 08 → 05, Harness 09, then the
[PR2-19 catalog](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md),
[B30](B30_PR2-19_Remaining_Rows_Contract_DRAFT.md),
[B30-S2](B30S2_PR2-19_Remaining_Rows_Contract_DRAFT.md),
[ADR-0020](../architecture/adr/ADR-0020-candidate-promotion-admission.md),
[B02](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md) and
[B03](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md). The post-B30-S2
blocker inventory is grounded directly in
`B30S2_PR2-19_Remaining_Rows_Contract_DRAFT.md`,
`NEXT_STAGE_PLAN_DRAFT.md`, `test_pr2_19_dependencies.py` and the current
`src/researchbase/application/` tree. This draft uses the Start here / §§1–13
structure of the approved PR2-17, PR2-18 and B30-S2 drafts; §14 records
documentation verification.

| Authority under `docs/architecture/` | Binding requirement |
| --- | --- |
| `01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`, §§3, 7–9; `02_Final_Architecture_Correction_Addendum_v1.0.md`; `03_Global_Schema_and_Contract_Registry_v1.0.md` | Deterministic facts outrank authority; one canonical owner per fact; `Hypothesis != Claim`; candidate/discussion artifacts are not canonical science. |
| `08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`; `05_Phase2_Development_Specification_v1.1_Harness_Integrated.md`, §§19–28, 42–43/PR2-19 | Preserve Phase 1 contracts; native strategy and discussion remain candidate-only until explicit Application promotion. |
| `12_Phase2_Architecture_and_Contract_Correction_v1.0.md`; `15_Phase2_Hash_Payload_Contract_R2_v1.0.md`, §§2, 6, 8 | Candidate generation and discussion turns perform zero implicit promotion; frozen transcripts/captures use `sha256-cjson-v1` and CAS verification. |
| `18_Phase2_Design_R3_Targeted_Remediation_v1.0.md`, §5; `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md`, §§1, 4–5; `adr/ADR-0020-candidate-promotion-admission.md` | First-statement `LOCK TABLE ... IN SHARE MODE` on `READ COMMITTED` snapshot writes, post-wait DB-clock rechecks, lock-free `REPEATABLE READ` reads, and dedicated B02/B03 admission tables instead of polymorphic links or silent `DRAFT` creation. |

Inspected baseline in this checkout:

- `tests/integration/phase2/test_pr2_19_candidates.py` and
  `test_pr2_19_discussion.py` currently exercise only the negative prefixes of
  G2 (native `NativeResearchStrategy.execute` writes zero canonical rows) and G4
  (bound discussion session/turn round-trip plus `DiscussionService.request_promotion`
  denying with `FORBIDDEN`).
- `tests/integration/phase2/test_pr2_19_dependencies.py` still marks `G2` and
  `G4` `BLOCKED` in `SUBCASES` because B02 (`strategy_candidate_promotion.py`)
  and B03 (`discussion_hypothesis.py`) have not yet merged into `src/researchbase/`.
- B19 (`0066_b19_close_prior_art_basis.py`), B21 (`0068_b21_unresolved_capture.py`)
  and B22 (`0065_b22_prior_art_correction.py`) are present in
  `src/researchbase/application/novelty.py`, while B20
  (`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` at `novelty.py`) and
  `RevisionActionService` `MANUSCRIPT_CHANGE` (`revision_action.py`) remain
  unimplemented.

Reference status after repository audit: every B02/B03 module, DTO, service,
command/query and admission/capture table below is **(new, planned by B02/B03)**.
This label also applies to their fields, hash-domain names, SQLSTATEs, constraints,
indexes, triggers and lock-inventory constants in §§5, 10–12; these are proposed
contract spellings, not verified production definitions. Existing discussion
receipts and research/artifact tables are already present; only their B03
extensions are new. In particular, `b02_support.py`,
`strategy_candidate_promotion.py`, `strategy_candidate_promotion_repository.py`,
`discussion_hypothesis.py`, `discussion_hypothesis_repository.py`,
`tests/integration/phase2/test_b02_strategy_promotion.py` and
`tests/integration/phase2/test_b03_discussion_promotion.py` are
**(new, planned by B02/B03)** and must not be included in a current-checkout test
command. The `S` and `B03_SNAPSHOT_TABLES` inventories in §12.2 are likewise
**(new, planned by B02/B03)**. Reconcile all proposed names against the landed
owner implementations before S3 execution; this reference audit does not approve
the proposed field layouts or protocols.

Existing code uses `NativeResearchStrategy.execute`, `ResearchStrategyResult`,
`DiscussionService.create` / `append` / `close` / `bind_transcript`,
`ApplicationService.create_research_question` / `create_hypothesis`,
`ContentAddressedFilesystemArtifactStore`, `ArtifactStore.put_verified`, and
`COMMANDS` / `SCENARIO_COMMANDS`. Discussion input bindings are supplied to
`create`; `bind_transcript` binds a frozen session transcript. Artifact roles are
`research_brief` and `discussion_transcript`; evidence rows use
`literature_evidence`. Credential validity comes from `CredentialVerifier` and
`VerifiedPrincipal`, not a credential table. These corrections name existing
repository boundaries; candidate admission still awaits B02/B03.

The canonical labels `SourceVersion`, `ScientificConclusionVersion`,
`NoveltyAssessment` and `RevisionAction` denote existing persistence concepts,
not Python class imports: use `source_versions`, `scientific_conclusion_versions`,
`novelty_assessments` and `revision_actions`, respectively.

| Absent owner definitions | Repository status for every use below |
| --- | --- |
| `StrategyCandidatePromotionService`, `CaptureNativeStrategyCommand`, `PromoteStrategyQuestionCommand`, `PromoteStrategyHypothesisCommand`, `ExactStrategyQuery`, `CaptureReadback`, `StrategyCandidateCapture`, `StrategyQuestionAdmission`, `StrategyHypothesisAdmission`; `capture_native_strategy`, `promote_strategy_question`, `promote_strategy_hypothesis`, `get_strategy_capture`, `get_strategy_question_promotion`, `get_strategy_hypothesis_promotion` | (new, planned by B02/B03), B02-owned; `StrategyCandidateCapture` is a proposed record/hash-domain label. |
| `DiscussionHypothesisService`, `DiscussionHypothesisCandidate`, `PromoteDiscussionHypothesisCommand`, `DiscussionHypothesisAdmission`; `promote_discussion_to_hypothesis`, `get_discussion_hypothesis_admission` | (new, planned by B02/B03), B03-owned. |
| `strategy_candidate_captures`, `strategy_candidate_sources`, `strategy_question_admissions`, `strategy_hypothesis_admissions`, `discussion_hypothesis_admissions`; `PROMOTE_HYPOTHESIS`, `result_artifact_version_id` receipt extension | (new, planned by B02/B03); all associated fields and named guards in §12.1 carry this status. |

## 2. Scope, dependency boundaries and non-goals

### 2.1 Newly runnable suffixes in B30-S3 (once B02 and B03 land)

G4's CLOSED-only admission rule follows [B03](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md)
§2 (scope) and §3 invariant 2 (first admission requires CLOSED). B03 §11.2
assigns `INVALID_STATE_TRANSITION` to a non-CLOSED session or unbound transcript;
§12.4 lists OPEN-session negative tests. These owner-contract sections support
CLOSED positive admission and OPEN rejection in §12.4 and the §10 glossary.
This is owner-contract evidence, not an inference from repository names.

These are the **only newly runnable suffixes selected for S3**. Preserve all
original row IDs and S1/S2 evidence. Test artifacts live under
`tests/integration/phase2/`.

| Original row / bounded suffix | Runnable B02/B03 commands and fixture construction | Required result; remaining boundary |
| --- | --- | --- |
| G2 (`candidate-admission`) | Seed `pr219_candidate_env` (`pr2_19_support.py`) and `b02_support.py` (`ScriptedRAG`, ingested project-linked `SourceVersion`s, independent researcher/reader actors). Run `StrategyCandidatePromotionService.capture_native_strategy(principal, CaptureNativeStrategyCommand)`, then `promote_strategy_question(principal, PromoteStrategyQuestionCommand)` and `promote_strategy_hypothesis(principal, PromoteStrategyHypothesisCommand)`, then fresh `get_strategy_capture`, `get_strategy_question_promotion`, and `get_strategy_hypothesis_promotion`. | Capture persists `research_brief` `ArtifactVersion` + `strategy_candidate_captures` + `strategy_candidate_sources` with zero question/hypothesis rows. Question promotion creates `ResearchQuestion` + `ResearchQuestionVersion` v1 (`DRAFT`, `frozen_at IS NULL`) + `strategy_question_admissions`. Hypothesis promotion records explicit researcher adaptation of `research_brief_candidate.sections[candidate_index]` (requiring nonnull `answer_candidate`) into `Hypothesis` + `HypothesisVersion` v1 (`DRAFT`, `frozen_at IS NULL`) + `strategy_hypothesis_admissions`. Zero `Claim` or `literature_evidence` writes. Note: native `candidate-v1` emits `hypothesis_candidates == ()`; genuinely emitted native strategy hypotheses remain outside B02/Phase 2. |
| G4 (`discussion-admission`) | Seed `pr219_discussion_env` (`pr2_19_support.py` + `test_pr2_10_discussion_persistence.py` / `test_pr2_10_binding_contract.py`): create frozen `SourceVersion`, `ResearchQuestionVersion`, `ClaimVersion`; run `DiscussionService.create`, `append`, `close`, `bind_transcript` (binding the frozen `discussion_transcript` `ArtifactVersion`). Keep `DiscussionService.request_promotion` negative check (`FORBIDDEN`), then invoke `DiscussionHypothesisService.promote_discussion_to_hypothesis(principal, PromoteDiscussionHypothesisCommand)` and fresh `get_discussion_hypothesis_admission(principal, project_id, receipt_id)`. | Legacy `request_promotion` still raises `FORBIDDEN` with zero writes. `promote_discussion_to_hypothesis` verifies bound session/turn/question and exact CAS transcript payload, then atomically writes `Hypothesis` + `HypothesisVersion` v1 (`DRAFT`, `frozen_at IS NULL`, `success_criteria=None`) + `discussion_command_receipts` (`command_name='PROMOTE_HYPOTHESIS'`) + `discussion_hypothesis_admissions`. Fresh readback after service restart matches exact hashes and IDs; zero `Claim`, `literature_evidence`, `ResearchQuestion` or review/decision/approval mutations occur. |

### 2.2 Complete inventory of PR2-19 rows and subcases still BLOCKED after B30-S2

Every PR2-19 row or subcase that remained `BLOCKED` after B30-S2 is listed below
together with its disposition in B30-S3 and the exact owning slice that unblocks
it. Blocking items must remain explicit `BLOCKED` entries (never silent skips,
xfails or fake passes):

| Row / subcase (`test_pr2_19_dependencies.py` / B30-S2 §2) | Status in B30-S3 | Current code / contract blocker | Owning slice that unblocks it |
| --- | --- | --- | --- |
| `G2` (`candidate-admission`) | **Unblocked by B02; runnable in B30-S3** (open-question promotion + researcher-adapted brief-section hypothesis promotion) | Until B02 lands, `NativeResearchStrategy.execute` has no persistence/promotion owner (`test_pr2_19_candidates.py` stops at zero-write check). Native `candidate-v1` also sets `hypothesis_candidates = ()` (`native_research_strategy.py`). | **[B02](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md)** (`ADR-0020`) unblocks G2 in B30-S3. (A future strategy-version contract outside Phase 2 would be required if native strategy ever emits non-empty `hypothesis_candidates`.) |
| `G4` (`discussion-admission`) | **Unblocked by B03; runnable in B30-S3** | Until B03 lands, `DiscussionService.request_promotion` unconditionally raises `FORBIDDEN` (`discussion.py`) and `discussion_command_receipts` only allows `CREATE_SESSION`/`APPEND_TURN`/`CLOSE_SESSION`/`BIND_TRANSCRIPT`. | **[B03](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md)** (`ADR-0020`) unblocks G4 in B30-S3 while keeping `DiscussionService.request_promotion` permanently denied. |
| `G6` (`manuscript-cycle`) and `F6` (`manuscript-result`, seventh `RevisionAction` type `MANUSCRIPT_CHANGE`) | **Still BLOCKED after B30-S3** | `RevisionActionService._supported` (`revision_action.py`) and migration `0051_b06_revision_action.py` allow only six action types and reject `MANUSCRIPT_CHANGE` with `INVALID_STATE_TRANSITION`; no manuscript concern-resolution cycle owner exists. | Unblocked only by a future **B06 manuscript-result follow-up slice** (`B06_RevisionAction_Full_Contract_DRAFT.md` §2) plus manuscript revision-cycle contract (explicitly outside current Phase 2 slices; note [B23](B23_Novelty_Review_Revision_Contract_DRAFT.md) owns novelty reassessment, not `MANUSCRIPT_CHANGE`). |
| `G7` (`strong-novelty`: positive & negative screening + novelty review/non-gating) | **Still BLOCKED after B30-S3** | B19 (`CLOSE_PRIOR_ART_FOUND`), B21 and B22 have landed in `novelty.py`, but negative `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` is still denied at `novelty.py` (`INVALID_STATE_TRANSITION`), and novelty review/reassessment (`B23`) plus non-gating E2E composition (`B24`) are still pending. | **[B20](B20_Screening_Negative_Probe_Contract_DRAFT.md)** unblocks `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` (with **[B19](B19_Close_Prior_Art_Basis_Contract_DRAFT.md)** already supplying `CLOSE_PRIOR_ART_FOUND`); **[B23](B23_Novelty_Review_Revision_Contract_DRAFT.md)** unblocks `NoveltyAssessment` review/reassessment; **[B24 / H2](H2_Phase2_Hardening_Followups_Contract_DRAFT.md)** (`§2.2` / `§2.3`) unblocks the G7 stronger-novelty and non-gating E2E proof. |
| `G7` (`lock-free-completed-command-replay` for novelty commands) | **Still BLOCKED after B30-S3** | `NoveltyService._once` (`novelty.py`) calls `repo.prepare(...)` (acquiring `LOCK TABLE ... IN SHARE MODE`, `pg_advisory_xact_lock`, and `claim_versions FOR UPDATE`) before `repo.parent(kind, c.id)` replay return. (`AuthorshipService._get` was already remediated via `prepare_read` and reconciled in B30-S2 §2.) | Unblocked by the **B30 §13 / PR2-18 owner disposition** (either a bounded `NoveltyService` read-only `REPEATABLE READ` replay preflight slice or explicit owner scoping in **[H2](H2_Phase2_Hardening_Followups_Contract_DRAFT.md) / [B31](PR2-20_Hardening_Plan_DRAFT.md)**). |
| `F1` (`automatic finding/impact propagation` from source correction/retraction) | **Still BLOCKED after B30-S3** (deterministic validity projection suffix is already in B30-S2) | [B25](B25_Manuscript_Validity_Contract_DRAFT.md) and [B26](B26_Finding_Impact_Propagation_Contract_DRAFT.md) (`finding_impact.py`) provide deterministic read projections and explicit `ImpactAssessment` commands, but source `CORRECTED`/`RETRACTED` transitions do not automatically write `AuditFinding` or `ImpactAssessment` rows. | Unblocked only if the owner authorizes a separate **automatic source-to-finding/impact write contract**; otherwise disposed as by-design explicit-command-only in **[B26](B26_Finding_Impact_Propagation_Contract_DRAFT.md) / [B31](PR2-20_Hardening_Plan_DRAFT.md)**. |
| `F5c` (`manuscript-reconsideration` for `READY_FOR_SUBMISSION` / `PREPARE_SUBMISSION`) | **Still BLOCKED after B30-S3** | `DecisionService.record_rejection_reconsideration` (`B10_Rejection_Reconsideration_Contract_DRAFT.md`) and `ApprovalService._successor_gate` remain restricted to `INTERNAL_SCIENTIFIC_RELEASE` (`ScientificConclusionVersion`). [B32](B32_Other_Approval_Purposes_Contract_DRAFT.md) §1 explicitly leaves manuscript reconsideration out of B32 S1. | Unblocked by a future **B10 / B32 manuscript-purpose reconsideration extension** (`READY_FOR_SUBMISSION` and `PREPARE_SUBMISSION` successor-decision rules). |
| `F9` (`scheduled role expiry` across an already-held lock wait, from B30-S2 §12.4 / `NEXT_STAGE_PLAN_DRAFT.md` §1) | **Still BLOCKED / owner-scoped** | `Phase2IdentityService.assign_project_role` (`phase2_identity.py`) sets `effective_from` with `effective_until = None`, and `close_project_role` closes immediately at `database_time()` (`phase2_identity.py`) while blocking on `project_role_assignments` `SHARE` locks; no Application command schedules a future `effective_until` without forbidden direct SQL. | Unblocked either by a bounded **`Phase2IdentityService` scheduled-role-expiry (`effective_until`) command/parameter** or by **owner disposition in B30-S2/S3** restricting post-wait temporal expiry tests to scheduled credential `expires_at`, grant `expires_at`, and pre-lock `CloseProjectRole`. |
| Full `PR2-19` gate (`require_full_gate`) and Phase 2 exit (`PR2-20`) | **Still BLOCKED after B30-S3** | Requires execution of B30-S2 and B30-S3 plus resolution/disposition of the rows above, [B28](B28_PaperQA2_Intake_Assessment_DRAFT.md) (owner-deferred to Phase 3 as recorded exit gap), and [H2](H2_Phase2_Hardening_Followups_Contract_DRAFT.md). | **[H2](H2_Phase2_Hardening_Followups_Contract_DRAFT.md)** and **[B31](PR2-20_Hardening_Plan_DRAFT.md)** (Phase 2 exit gate and hardening report). |

## 3. Invariants and conservative judgments

1. **Candidate and discussion isolation**: `NativeResearchStrategy.execute` and
   `DiscussionService` (`create`, `append`, `close`,
   `bind_transcript`, `request_promotion`) never create or mutate
   `ResearchQuestion`, `Hypothesis`, `Claim`, `literature_evidence` or governance rows.
   `DiscussionService.request_promotion` remains unconditionally `FORBIDDEN`.
2. **Explicit single-candidate admission only**: B02 promotes one persisted
   strategy candidate item per command (`PromoteStrategyQuestionCommand` or
   `PromoteStrategyHypothesisCommand`). B03 promotes one bound discussion-turn
   hypothesis candidate per command (`PromoteDiscussionHypothesisCommand`).
   Neither batch-promotes nor creates `Claim`s (`Hypothesis != Claim`).
3. **Draft-only canonical outputs**: Every promoted `ResearchQuestionVersion` or
   `HypothesisVersion` is created at `version_number = 1`, `status = 'DRAFT'`,
   `frozen_at = NULL`, with parent `current_version_id` pointing to that `DRAFT`
   version. Subsequent freezing or status changes use existing research commands.
4. **Honest native strategy provenance (B02)**: Because native `candidate-v1`
   emits `hypothesis_candidates == ()`, `promote_strategy_hypothesis` is tested
   and recorded as an explicit researcher adaptation of
   `research_brief_candidate.sections[candidate_index]` (requiring nonnull
   `answer_candidate` and verified section citations), never as a fabricated
   native hypothesis list.
5. **CAS and frozen-input closure**: B02 capture and promotion verify every cited
   `SourceVersion` is frozen (`frozen_at IS NOT NULL`), linked to the project in
   `literature_source_project_links`, and has non-withdrawn `SourceDocument` (new, planned by B02/B03)
   CAS bytes matching `content_hash`. B03 promotion verifies the session and
   turn belong to `project_id`, `research_question_version_id` is bound in
   `discussion_session_question_inputs`, and `transcript_artifact_version_id`
   equals `turn.transcript_artifact_version_id` (new, planned by B02/B03) with intact CAS JSON matching
   `turn_id`, `session_id`, `actor_id` and `content_hash`.
6. **Human and Agent parity**: Both `ActorType.HUMAN` and `ActorType.AGENT`
   callers use the same B02/B03 Application commands and must hold current active
   project membership, active research write role (`OWNER`, `RESEARCHER`), and proven `actor_subject_bindings` for the authenticated
   principal at both pre-check and final pre-commit DB clock reads.

## 4. Proposed commands, DTOs and historical readback

B30-S3 introduces **no new product commands, DTOs, HTTP routes or CLI
commands**. Tests invoke the closed Application services and dataclasses owned
by B02 (`src/researchbase/application/strategy_candidate_promotion.py`), B03
(`src/researchbase/application/discussion_hypothesis.py`), PR2-08
(`native_research_strategy.py`), PR2-10 (`discussion.py`) and Phase 1 research
(`commands.py`), pinned in §11.3.

After every successful promotion, denied promotion, or injected mid-UoW fault,
tests must construct fresh service instances over a new session/UoW and verify:

- B02 `get_strategy_capture`, `get_strategy_question_promotion` and
  `get_strategy_hypothesis_promotion` return the exact `CaptureReadback`,
  `StrategyQuestionAdmission` and `StrategyHypothesisAdmission` records;
- B03 `get_discussion_hypothesis_admission` returns the exact
  `DiscussionHypothesisAdmission` record;
- Phase 1 research readers confirm the newly created `ResearchQuestionVersion`
  or `HypothesisVersion` (`version_number == 1`, `status == 'DRAFT'`,
  `frozen_at is None`) and exact `content_hash`;
- Table row counts before and after each step match expected `StateDelta`s.

## 5. Schema and literal hash proposal — no migration

**DO NOT ADD SCHEMA.** B30-S3 has an empty DDL delta. §12.1 inventories the
tables, constraints and triggers owned by B02 and B03 that B30-S3 tests must
observe once those migrations land.

All hash assertions in B30-S3 tests must independently compute `sha256-cjson-v1`
digests (per `docs/architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md` §2,
B02 §5.2 and B03 §5.2) in test code without calling the production hash builder
under test:

- B02 `CaptureReadback.content_hash` (`domain='StrategyCandidateCapture'`,
  `schema_version=1`), `StrategyQuestionAdmission.content_hash`
  (`domain='StrategyQuestionAdmission'`, `schema_version=1`), and
  `StrategyHypothesisAdmission.content_hash`
  (`domain='StrategyHypothesisAdmission'`, `schema_version=1`);
- B03 `DiscussionHypothesisAdmission.candidate_hash` (`sha256-cjson-v1` over
  `{expected_direction, rationale, research_question_version_id, session_id,
  statement, transcript_artifact_version_id, turn_id}`) and created
  `HypothesisVersion.content_hash` (`sha256-cjson-v1` over
  `{assumption_notes: [], expected_direction, project_id, rationale,
  research_question_id, statement, status: "DRAFT", success_criteria: null,
  version_number: 1}`).

## 6. Error contract — existing categories only

Use existing `ErrorCode` values in `src/researchbase/foundation/errors.py` and the
exact adapter mappings in §11.2. No new error codes or transport layers are
added. Each negative case in §12.4 pins one specific `ErrorCode` (never a vague
`pytest.raises(Exception)` or multi-code wildcard):

- Authorize the caller before disclosing project-scoped existence or state.
  Unentitled callers receive `FORBIDDEN` (or `AUTHENTICATION_REQUIRED` /
  `SUBJECT_BINDING_UNPROVEN`), never `NOT_FOUND` or `IDEMPOTENCY_CONFLICT`.
- Distinguish absent requested roots (`NOT_FOUND` / `SOURCE_VERSION_NOT_FOUND`)
  from broken frozen-input/CAS/citation closure on a resolved root
  (`PROVENANCE_CLOSURE_VIOLATION` or `FROZEN_REFERENCE_REQUIRED`).
- Assert direct SQL guard probes against exact PostgreSQL SQLSTATE / constraint
  or trigger names (`P22B1` / `P22B2` for B02, `P17D1` / `P17D3` / `23505` /
  `23514` for B03) as well as mapped Application `ErrorCode`s.

## 7. Transactions, concurrency and failure recovery

1. **One command, one transaction**: Every setup command, capture, promotion and
   readback executes in its own UoW. Never wrap a scenario in an outer shared
   transaction.
2. **B02 capture two-phase boundary**: `capture_native_strategy` runs a
   lock-free `REPEATABLE READ` preflight (`READ ONLY`), executes
   `NativeResearchStrategy.execute` and `ArtifactStore.put_verified` outside any DB
   transaction, and then opens one `READ COMMITTED` write UoW whose first SQL
   statement is `LOCK TABLE <S> IN SHARE MODE` (§12.2). Tests must verify via
   `b30_observations` that no DB transaction is held open while the strategy
   adapter executes.
3. **Snapshot-consistent writes**: B02 write UoWs (`capture_native_strategy`
   commit phase, `promote_strategy_question`, `promote_strategy_hypothesis`) and
   B03 `promote_discussion_to_hypothesis` run in `READ COMMITTED` with
   `LOCK TABLE ... IN SHARE MODE` as the **first transactional statement**,
   followed by `SET LOCAL lock_timeout = '10s'`,
   `SET LOCAL statement_timeout = '30s'`, deterministic `pg_advisory_xact_lock`,
   fresh DB-clock authority checks, closure checks, inserts,
   `SET CONSTRAINTS ALL IMMEDIATE`, and final pre-commit DB-clock authority and
   source/session state rechecks.
4. **Lock-free reads**: `get_strategy_capture`,
   `get_strategy_question_promotion`, `get_strategy_hypothesis_promotion` and
   `get_discussion_hypothesis_admission` each use a single `REPEATABLE READ`
   read-only transaction with zero `LOCK TABLE`, zero `pg_advisory_xact_lock`,
   and zero `FOR UPDATE` / `FOR SHARE` clauses (and B03 reads never call
   `DiscussionService._authorize`, which takes `projects FOR SHARE`).
5. **Concurrency and barriers**: Concurrency cases use two real database
   connections, `threading.Barrier` synchronization, and `pg_locks` /
   `pg_blocking_pids` observations (`LockEvent`s), never timing sleeps.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 specifies the exact files and test cases. All integration tests run
against disposable real PostgreSQL 18.x at the current migration head with a
real local `ContentAddressedFilesystemArtifactStore` and deterministic `ScriptedRAG` /
discussion fixtures. Never fabricate frozen `SourceVersion`, `ArtifactVersion`,
`discussion_sessions`, `discussion_turns` or admission rows via raw SQL in workflow
tests (raw SQL is used only in dedicated constraint/trigger probes after a
valid command commit). Fault-injection cases use test-only repository/UoW
wrappers that execute the real write or `SET CONSTRAINTS ALL IMMEDIATE` and
then raise before commit; no production fault hooks are permitted.

## 9. Acceptance criteria and evidence boundary

Acceptance of B30-S3 is bounded to the G2 and G4 suffixes in §2.1 after B02 and
B03 land and after separate owner authorization and execution of §12.4's tests,
with all B30-S1 and B30-S2 runnable evidence preserved and zero open P0/P1
findings.

- In `tests/integration/phase2/test_pr2_19_dependencies.py`:
  - `HISTORICAL_BLOCKED_ROWS` remains frozen at `("G2", "G4", "G6", "G7", "F1", "F5", "F6", "F9")`;
  - `G2` (`candidate-admission`) and `G4` (`discussion-admission`) move from
    `BLOCKED` to runnable only when B02 and B03 modules are present and their
    extended PR2-19 E2E tests in `test_pr2_19_candidates.py` and
    `test_pr2_19_discussion.py` execute and pass;
  - All other rows/subcases in §2.2 remain `BLOCKED`, `availability_is_acceptance`
    remains `False`, and `require_full_gate` continues to fail closed.
- Never turn `not run`, `setup error` (such as unset `RB_TEST_ADMIN_URL`),
  `skipped`, or owner-suite unit tests into PR2-19 E2E `PASS`.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| `StrategyCandidateCapture` | B02 immutable record binding a native `candidate-v1` `research_brief` `ArtifactVersion` and its exact project-linked `SourceVersion` set. |
| `StrategyQuestionAdmission` / `StrategyHypothesisAdmission` | B02 immutable admission receipts linking one `capture_id` + `candidate_index` to a newly created `DRAFT` `ResearchQuestionVersion` v1 or researcher-adapted `DRAFT` `HypothesisVersion` v1. |
| Researcher-adapted section hypothesis | B02's explicit promotion of `research_brief_candidate.sections[candidate_index]` (requiring nonnull `answer_candidate`) into a `DRAFT` `Hypothesis`, because `candidate-v1` emits `hypothesis_candidates == ()`. |
| `DiscussionHypothesisAdmission` | B03 immutable admission row (1:1 with a `PROMOTE_HYPOTHESIS` `discussion_command_receipts` row) binding a closed bound session turn (B03 §§2, 3.2), frozen transcript `ArtifactVersion`, and bound `ResearchQuestionVersion` to a newly created `DRAFT` `HypothesisVersion` v1. |
| `candidate_hash` | B03 `sha256-cjson-v1` digest over the normalized discussion hypothesis candidate tuple, enforced unique per `(session_id, turn_id, candidate_hash)`. |
| Unblocking slice | The specific Phase 2 backlog contract (`B02`, `B03`, `B20`, `B23`, `B24/H2`, future `B06`/`B10` follow-ups, `B31`) that owns the production capability needed by a blocked PR2-19 row. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

1. **Bind G2 and G4 strictly to B02 and B03**: G2 uses
   `StrategyCandidatePromotionService` (`B02`) and G4 uses
   `DiscussionHypothesisService` (`B03`). Neither bypasses admission via
   `ApplicationService.create_research_question` or
   `ApplicationService.create_hypothesis` directly, and `DiscussionService.request_promotion`
   remains a required negative control (`FORBIDDEN`) inside G4.
2. **Preserve honest native strategy semantics in G2**: G2 tests both
   `promote_strategy_question` (from `open_question_candidates[candidate_index]`)
   and `promote_strategy_hypothesis` (from `research_brief_candidate.sections[candidate_index]`
   with nonnull `answer_candidate` and caller `statement`/`rationale`), and
   explicitly asserts `batch.hypothesis_candidates == ()`.
3. **Complete post-B30-S2 blocker accounting**: Every PR2-19 row/subcase still
   blocked after B30-S2 is accounted for in §2.2 with its owning slice. No
   production work for those remaining blockers is smuggled into B30-S3.
4. **Fail-closed test oracle**: If B02 or B03 implementation diverges from its
   contract when B30-S3 runs, record the failure against B02/B03 rather than
   weakening B30-S3 assertions or mutating production code in this slice.

### 11.2 Pinned error mappings

Values match `src/researchbase/api/errors.py:_STATUS` and
`src/researchbase/cli/errors.py:CLI_EXIT_CODES`.

| Code | HTTP | CLI | Selected B30-S3 oracle (G2 / B02 and G4 / B03) |
| --- | ---: | ---: | --- |
| `VALIDATION_ERROR` | 422 | 2 | Blank/overlong `topic`, `statement`, `rationale` or `expected_direction`; `source_version_ids` empty, >100 or duplicate; `max_evidence_candidates` outside `1..100`; negative `candidate_index`; `candidate_index` out of range for `open_question_candidates` / `sections` or section `answer_candidate is None`; non-UUID fields. |
| `AUTHENTICATION_REQUIRED` | 401 | 3 | Missing, revoked or expired `VerifiedPrincipal` credential at `database_time()`. |
| `SUBJECT_BINDING_UNPROVEN` | 403 | 3 | Authenticated principal lacks active `actor_subject_bindings` row for `(deployment_id, subject_kind, subject_value, actor_id)` or actor is inactive. |
| `FORBIDDEN` | 403 | 3 | Caller lacks active project membership or active research write role (`OWNER`, `RESEARCHER`), or lacks read role on replay/readback, or calls legacy `DiscussionService.request_promotion`. |
| `NOT_FOUND` | 404 | 3 | Entitled caller requests missing `capture_id`, `research_question_id`, `session_id`, `turn_id`, `transcript_artifact_version_id`, `research_question_version_id`, or `receipt_id`, or row belongs to another project. |
| `SOURCE_VERSION_NOT_FOUND` | 404 | 3 | B02 `capture_native_strategy` references a `source_version_id` absent from `source_versions`. |
| `FROZEN_REFERENCE_REQUIRED` | 409 | 5 | B02 `SourceVersion.frozen_at IS NULL`, `SourceVersion` not linked to `project_id`, or `ResearchQuestion.current_version_id IS NULL`; B03 `ResearchQuestionVersion.frozen_at IS NULL` or `artifact_versions.frozen_at IS NULL`. |
| `PROVENANCE_CLOSURE_VIOLATION` | 409 | 5 | B02/B03 CAS blob missing or digest mismatch; B02 `SourceDocument` (new, planned by B02/B03) `WITHDRAWN` or candidate citations missing from `strategy_candidate_sources`; B03 `artifact_type != 'discussion_transcript'`, `turn.transcript_artifact_version_id` (new, planned by B02/B03) mismatch, transcript JSON `turn_id`/`session_id`/`actor_id`/`content_hash` mismatch, question not bound in `discussion_session_question_inputs`, or deferred completeness trigger (`P22B2` / `P17D3`). |
| `IDEMPOTENCY_CONFLICT` | 409 | 4 | Same command `id` (B02) or `(project_id, actor_id, 'PROMOTE_HYPOTHESIS', request_id)` (B03) replayed with different normalized payload or by a different actor, or B02 target `(capture_id, candidate_index)` / B03 target `(session_id, turn_id, candidate_hash)` already promoted under a different command/request ID. |
| `IMMUTABLE_RECORD` | 409 | 4 | Direct SQL `UPDATE`/`DELETE` on B02 capture/source/admission tables (`P22B1`) or B03 `discussion_hypothesis_admissions` (`P17D1`). |
| `CONCURRENT_MODIFICATION` | 409 | 4 | Lock timeout (`55P03`), statement timeout (`57014`), serialization failure (`40001`) or deadlock (`40P01`). |
| `INTERNAL_ERROR` (fallback, not `ErrorCode`) | 500 | 1 | Sanitized unexpected failure with zero partial writes. |

### 11.3 DTO fields, Python types, limits and enums

All identity fields are strict `uuid.UUID`; timestamps are timezone-aware UTC
`datetime`; hashes are `ContentHash` (`sha256:[0-9a-f]{64}`). Callers never pass
`actor_id` or timestamps inside command DTOs; actor authority comes exclusively
from `principal: VerifiedPrincipal`.

| Owner module & frozen dataclass | Exact fields, types and bounds |
| --- | --- |
| `strategy_candidate_promotion.CaptureNativeStrategyCommand` | `id: UUID`, `project_id: UUID`, `topic: str` (trimmed `1..500`), `source_version_ids: tuple[UUID, ...]` (`1..100` distinct UUIDs, canonically sorted by UUID text), `max_evidence_candidates: int = 20` (`1..100`, `bool` rejected). |
| `strategy_candidate_promotion.PromoteStrategyQuestionCommand` | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `candidate_index: int` (`>= 0`, `< len(open_question_candidates)`, `bool` rejected), `rationale: str` (trimmed `1..2000`). |
| `strategy_candidate_promotion.PromoteStrategyHypothesisCommand` | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `candidate_index: int` (`>= 0`, `< len(research_brief_candidate.sections)` with nonnull `answer_candidate`, `bool` rejected), `rationale: str` (trimmed `1..2000`), `statement: str` (trimmed `1..2000`), `research_question_id: UUID | None = None`. |
| `strategy_candidate_promotion.ExactStrategyQuery` | `id: UUID`, `project_id: UUID`. Used by `get_strategy_capture`, `get_strategy_question_promotion`, `get_strategy_hypothesis_promotion`. |
| `strategy_candidate_promotion.CaptureReadback` | `id: UUID`, `project_id: UUID`, `artifact_id: UUID`, `artifact_version_id: UUID`, `created_by: UUID`, `created_at: datetime`, `topic: str`, `source_version_ids: tuple[UUID, ...]`, `max_evidence_candidates: int`, `strategy_name: Literal['native']`, `strategy_version: Literal['candidate-v1']`, `batch_content_hash: ContentHash`, `content_hash: ContentHash`, `batch: ResearchStrategyResult`. |
| `strategy_candidate_promotion.StrategyQuestionAdmission` | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `candidate_index: int`, `research_question_id: UUID`, `research_question_version_id: UUID`, `created_by: UUID`, `created_at: datetime`, `question: str`, `rationale: str`, `supporting_source_version_ids: tuple[UUID, ...]`, `content_hash: ContentHash`. |
| `strategy_candidate_promotion.StrategyHypothesisAdmission` | `id: UUID`, `project_id: UUID`, `capture_id: UUID`, `candidate_index: int`, `research_question_id: UUID | None`, `hypothesis_id: UUID`, `hypothesis_version_id: UUID`, `created_by: UUID`, `created_at: datetime`, `section_heading: str`, `statement: str`, `rationale: str`, `supporting_source_version_ids: tuple[UUID, ...]`, `content_hash: ContentHash`. |
| `discussion_hypothesis.DiscussionHypothesisCandidate` | `turn_id: UUID`, `transcript_artifact_version_id: UUID`, `research_question_version_id: UUID`, `statement: str` (trimmed `1..4000`), `expected_direction: str | None = None` (trimmed `1..1000` if nonnull), `rationale: str | None = None` (trimmed `1..4000` if nonnull). (`success_criteria` is derived `None`.) |
| `discussion_hypothesis.PromoteDiscussionHypothesisCommand` | `project_id: UUID`, `session_id: UUID`, `request_id: UUID`, `candidate: DiscussionHypothesisCandidate`. |
| `discussion_hypothesis.DiscussionHypothesisAdmission` | `receipt_id: UUID`, `project_id: UUID`, `session_id: UUID`, `turn_id: UUID`, `transcript_artifact_version_id: UUID`, `research_question_version_id: UUID`, `candidate_hash: ContentHash`, `statement: str`, `expected_direction: str | None`, `rationale: str | None`, `hypothesis_id: UUID`, `hypothesis_version_id: UUID`, `admitted_by: UUID`, `admitted_at: datetime`. |

Report dataclasses in `tests/integration/phase2/pr2_19_support.py`
(`ScenarioSpec`, `ScenarioObservation`, `StateDelta`, `VerifiedHash`,
`LockEvent`) keep their existing schemas and bounds from B30/B30-S2 (§11.3 of
B30-S2). Extend `COMMANDS` and the relevant `SCENARIO_COMMANDS` entries in
`pr2_19_support.py` only with the concrete
B02 and B03 command/query names in §12.3.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Empty DDL change set in B30-S3. All B02/B03 names in this inventory are
**(new, planned by B02/B03)**, including additions to existing receipts.
Observe these proposed tables, columns, constraints
and triggers introduced by B02 and B03; do not add migrations or alter schema in
B30-S3.

| Owner contract & tables | Column types and named constraints / triggers to observe in B30-S3 tests |
| --- | --- |
| **B02** `strategy_candidate_captures` & `strategy_candidate_sources` | `strategy_candidate_captures`: `id, project_id, artifact_version_id, created_by UUID`, `created_at TIMESTAMPTZ`, `topic VARCHAR(500)`, `max_evidence_candidates INTEGER`, `strategy_name VARCHAR(32)`, `strategy_version VARCHAR(32)`, `batch_content_hash VARCHAR(71)`, `content_hash VARCHAR(71)`. Constraints: `pk_b02_capture`, `fk_b02_capture_project`, `fk_b02_capture_artifact`, `fk_b02_capture_actor`, `uq_b02_capture_artifact`, `ck_b02_capture_topic`, `ck_b02_capture_limit`, `ck_b02_capture_strategy`, `ck_b02_capture_hash`. `strategy_candidate_sources`: `(capture_id, ordinal INTEGER, source_version_id UUID)`, `pk_b02_sources`, `uq_b02_source_member`, `fk_b02_source_capture`, `fk_b02_source_version`, `ck_b02_source_ordinal`. Triggers: `b02_capture_immutable`, `b02_sources_immutable`, `b02_source_insert_guard` (`SQLSTATE 'P22B1'`), deferred `b02_capture_complete` and `b02_sources_complete` (`SQLSTATE 'P22B2'`). |
| **B02** `strategy_question_admissions` & `strategy_hypothesis_admissions` | `strategy_question_admissions`: `id, project_id, capture_id, research_question_id, research_question_version_id, created_by UUID`, `candidate_index INTEGER`, `created_at TIMESTAMPTZ`, `question VARCHAR(2000)`, `rationale VARCHAR(2000)`, `content_hash VARCHAR(71)`; `pk_b02_q`, `uq_b02_q_candidate(capture_id, candidate_index)`, `uq_b02_q_version(research_question_version_id)`, `fk_b02_q_project`, `fk_b02_q_capture`, `fk_b02_q_entity`, `fk_b02_q_version`, `fk_b02_q_actor`, `ck_b02_q_index`, `ck_b02_q_text`, `ck_b02_q_hash`, triggers `b02_q_immutable` (`P22B1`) and deferred `b02_q_complete` (`P22B2`). `strategy_hypothesis_admissions`: analogous `pk_b02_h`, `uq_b02_h_candidate(capture_id, candidate_index)`, `uq_b02_h_version(hypothesis_version_id)`, `fk_b02_h_project`, `fk_b02_h_capture`, `fk_b02_h_question`, `fk_b02_h_entity`, `fk_b02_h_version`, `fk_b02_h_actor`, `ck_b02_h_index`, `ck_b02_h_text`, `ck_b02_h_hash`, triggers `b02_h_immutable` (`P22B1`) and deferred `b02_h_complete` (`P22B2`). |
| **B03** `discussion_command_receipts` & `discussion_hypothesis_admissions` | `discussion_command_receipts`: `ck_b03_receipt_command` (adding `'PROMOTE_HYPOTHESIS'` with nonnull `result_session_id, result_turn_id, result_artifact_version_id`) and `uq_b03_receipt_context UNIQUE (id, project_id, result_session_id)`. `discussion_hypothesis_admissions`: `receipt_id, project_id, session_id, turn_id, transcript_artifact_version_id, research_question_version_id, hypothesis_id, hypothesis_version_id, admitted_by UUID`, `candidate_hash VARCHAR(71)`, `statement VARCHAR(4000)`, `expected_direction VARCHAR(1000) NULL`, `rationale VARCHAR(4000) NULL`, `admitted_at TIMESTAMPTZ`; `pk_b03_admission`, `fk_b03_receipt`, `fk_b03_session`, `fk_b03_turn`, `fk_b03_question`, `fk_b03_transcript`, `fk_b03_hv`, `uq_b03_output(hypothesis_version_id)`, `uq_b03_candidate(session_id, turn_id, candidate_hash)`, `ck_b03_hash`, `ck_b03_statement`, `ck_b03_direction`, `ck_b03_rationale`, index `ix_b03_admission_project_receipt`. Triggers: `b03_admission_immutable` (`SQLSTATE 'P17D1'`) and deferred `b03_complete_receipt` + `b03_complete_admission` (`SQLSTATE 'P17D3'`). |

### 12.2 Exact lock order and transactions

For all B02 and B03 `READ COMMITTED` snapshot writes, `LOCK TABLE <inventory> IN SHARE MODE`
is the **FIRST transactional statement** in the UoW before `SET LOCAL`,
authority queries, `pg_advisory_xact_lock`, or row locks. Read paths use one
read-only `REPEATABLE READ` snapshot and never acquire table, advisory or row
locks.

- **B02 lexical `SHARE` table inventory `S`** (`strategy_candidate_promotion_repository.py`):
  `actor_subject_bindings, actors, artifact_versions, artifacts, hypotheses, hypothesis_versions, literature_source_project_links, literature_sources, project_membership_events, project_memberships, project_role_assignments, projects, research_question_versions, research_questions, source_versions, strategy_candidate_captures, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_question_admissions`.
- **B03 lexical `SHARE` table inventory `B03_SNAPSHOT_TABLES`** (`discussion_hypothesis_repository.py`):
  `actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, discussion_session_claim_inputs, discussion_session_question_inputs, discussion_session_source_inputs, discussion_sessions, discussion_turn_claim_citations, discussion_turn_source_citations, discussion_turns, literature_source_project_links, literature_sources, project_membership_events, project_memberships, project_role_assignments, projects, research_question_versions, research_questions, source_versions`
  (excludes write targets `hypotheses`, `hypothesis_versions`,
  `discussion_command_receipts`, `discussion_hypothesis_admissions`).

| Exercised command / query | Exact owner lock and transaction protocol to assert with `b30_observations` |
| --- | --- |
| B02 `capture_native_strategy` | **Phase 1 (preflight)**: read-only `REPEATABLE READ` UoW (`SET LOCAL lock_timeout='10s'`, `statement_timeout='30s'`, zero locks); verify clock/principal/write role and frozen project-linked `SourceVersion`s + CAS bytes; close preflight UoW. **Phase 2 (compute & CAS)**: run `NativeResearchStrategy.execute` and `ArtifactStore.put_verified` outside any DB transaction. **Phase 3 (commit)**: `READ COMMITTED`; FIRST statement `LOCK TABLE <S> IN SHARE MODE`; `SET LOCAL lock_timeout='10s'`, `statement_timeout='30s'`; `pg_advisory_xact_lock(hashtext('b02:capture:' \|\| id::text))`; fresh DB clock + principal/read check; replay lookup on `strategy_candidate_captures.id`; writer role check; re-verify frozen project-linked `SourceVersion`s; insert `artifacts`, `artifact_versions` (`research_brief`, `frozen_at=database_time()`), `strategy_candidate_captures`, `strategy_candidate_sources`; `SET CONSTRAINTS ALL IMMEDIATE`; final DB-clock principal/role/source recheck; `COMMIT`. |
| B02 `promote_strategy_question` / `promote_strategy_hypothesis` | `READ COMMITTED`; FIRST statement `LOCK TABLE <S> IN SHARE MODE`; `SET LOCAL lock_timeout='10s'`, `statement_timeout='30s'`; `pg_advisory_xact_lock(hashtext('b02:question:' \|\| id::text))` (or `'b02:hypothesis:' \|\| id::text`); fresh DB clock + principal/read check; replay lookup by `id`; writer role check; load capture + verify CAS `research_brief` payload + candidate index + cited `SourceVersion`s non-withdrawn (and optional `research_question_id` in same project with nonnull `current_version_id`); check `uq_b02_q_candidate` / `uq_b02_h_candidate`; insert `ResearchQuestion` + `ResearchQuestionVersion` v1 (`DRAFT`, `frozen_at=NULL`) + `strategy_question_admissions` (or `Hypothesis` + `HypothesisVersion` v1 `DRAFT` + `strategy_hypothesis_admissions`); `SET CONSTRAINTS ALL IMMEDIATE`; final DB-clock principal/role/source recheck; `COMMIT`. |
| B03 `promote_discussion_to_hypothesis` | `READ COMMITTED`; FIRST statement `LOCK TABLE <B03_SNAPSHOT_TABLES> IN SHARE MODE`; `SET LOCAL lock_timeout='10s'`, `statement_timeout='30s'`; plain reads on `actor_subject_bindings`, `actors`, `projects`, `project_memberships`, `project_role_assignments` + `SELECT clock_timestamp()`; `pg_advisory_xact_lock(hashtext('discussion-receipt:' \|\| deployment_id \|\| ':' \|\| project_id \|\| ':' \|\| actor_id \|\| ':PROMOTE_HYPOTHESIS:' \|\| request_id))`; current read check + receipt lookup (if found, verify actor/payload/CAS and return `DiscussionHypothesisAdmission`); writer role check; `pg_advisory_xact_lock(hashtext('b03:discussion-hypothesis:' \|\| session_id \|\| ':' \|\| turn_id \|\| ':' \|\| candidate_hash))`; check `(session_id, turn_id, candidate_hash)` uniqueness; verify session/turn/bound `research_question_version_id` and `transcript_artifact_version_id` + CAS transcript bytes; fresh writer recheck; insert `Hypothesis`, `HypothesisVersion` v1 (`DRAFT`, `frozen_at=NULL`), update `hypotheses.current_version_id`, insert `discussion_command_receipts` (`PROMOTE_HYPOTHESIS`) and `discussion_hypothesis_admissions`; `SET CONSTRAINTS ALL IMMEDIATE`; final DB-clock writer check; `COMMIT`. |
| B02 `get_strategy_*` and B03 `get_discussion_hypothesis_admission` | Single read-only `REPEATABLE READ` UoW (`SET LOCAL lock_timeout='10s'`, `statement_timeout='30s'`); verify principal + current project read entitlement at `clock_timestamp()`, read saved rows and verify CAS bytes, recheck `clock_timestamp()` before return; **zero** `LOCK TABLE`, **zero** `pg_advisory_xact_lock`, **zero** `FOR UPDATE`/`FOR SHARE`. |

### 12.3 Ordered build steps and module paths

1. Extend `tests/integration/phase2/pr2_19_support.py`:
   - Add B02 and B03 command/query names (`capture_native_strategy`,
     `promote_strategy_question`, `promote_strategy_hypothesis`,
     `get_strategy_capture`, `get_strategy_question_promotion`,
     `get_strategy_hypothesis_promotion`, `promote_discussion_to_hypothesis`,
     `get_discussion_hypothesis_admission`) to `COMMANDS` and the G2/G4 entries in `SCENARIO_COMMANDS`.
   - Include `strategy_candidate_captures`, `strategy_candidate_sources`,
     `strategy_question_admissions`, `strategy_hypothesis_admissions`, and
     `discussion_hypothesis_admissions` in table count delta helpers when B02/B03
     tables exist.
2. Update `tests/integration/phase2/test_pr2_19_dependencies.py`:
   - Reconcile `G2` (`candidate-admission`) and `G4` (`discussion-admission`) in
     `SUBCASES` against `researchbase.application.strategy_candidate_promotion`
     and `researchbase.application.discussion_hypothesis`.
   - Keep all remaining rows in §2.2 `BLOCKED`, keep
     `HISTORICAL_BLOCKED_ROWS` unchanged, and keep `availability_is_acceptance = False`
     and `require_full_gate` fail-closed.
3. Extend `tests/unit/phase2/test_pr2_19_report_contract.py` and
   `tests/architecture/test_pr2_19_boundaries.py`:
   - Unit-test the new command allowlist entries and report validation.
   - Add architecture boundary assertions that B02 and B03 services/repositories
     preserve candidate isolation, use `LOCK TABLE ... IN SHARE MODE` first on
     writes, and use lock-free `REPEATABLE READ` on reads.
4. Extend `tests/integration/phase2/test_pr2_19_candidates.py` (G2) and
   `tests/integration/phase2/test_pr2_19_discussion.py` (G4) with the required
   cases in §12.4 using `b30_observations.py` (`sql_protocol`,
   `assert_first_share`, `assert_snapshot_read`).
5. Run the focused static, unit, architecture, and touched PostgreSQL suites in
   §12.4, record exact counts and remaining blockers under
   `artifacts/pr_evidence/PR2-19`, and stop without running the full suite.

### 12.4 Test artifacts and required cases

Paths below are under `tests/integration/phase2/` (plus unit/architecture paths
named explicitly). These are planned post-authorization extensions once B02 and
B03 land, not claims of executed S3 tests today.

| File | Required cases |
| --- | --- |
| `test_pr2_19_candidates.py` (extend for G2) | **G2 positive & negative suffix**: (1) retain PR2-08 candidate-only check (`NativeResearchStrategy.execute` writes 0 DB rows, `batch.hypothesis_candidates == ()`); (2) `capture_native_strategy` persists `research_brief` `ArtifactVersion` + `strategy_candidate_captures` + `strategy_candidate_sources` with 0 `research_questions`/`hypotheses`/`claims`/`literature_evidence` rows and no open DB tx during strategy compute; (3) `promote_strategy_question` creates `ResearchQuestion` + `ResearchQuestionVersion` v1 (`DRAFT`, `frozen_at is None`) + `strategy_question_admissions`; (4) `promote_strategy_hypothesis` promotes `research_brief_candidate.sections[idx]` (with nonnull `answer_candidate`) into `Hypothesis` + `HypothesisVersion` v1 (`DRAFT`, `frozen_at is None`) + `strategy_hypothesis_admissions` (both with and without `research_question_id`), leaving `claims` and `literature_evidence` at 0; (5) fresh service restart + `get_strategy_capture`, `get_strategy_question_promotion`, `get_strategy_hypothesis_promotion` verify independently computed `sha256-cjson-v1` hashes, CAS bytes, and single-snapshot lock-free `REPEATABLE READ` execution (`assert_snapshot_read(..., snapshots=1)`); (6) `assert_first_share` on capture commit and both promotion commands; (7) exact idempotent replay (including after write-role revocation when read role remains) vs `IDEMPOTENCY_CONFLICT` on mutated payload, different actor, or second command ID for the same `(capture_id, candidate_index)`; (8) negative gates: `VALIDATION_ERROR` (out-of-range index, section with `answer_candidate=None`), `FROZEN_REFERENCE_REQUIRED` (unlinked/unfrozen source or unfrozen question), `PROVENANCE_CLOSURE_VIOLATION` (corrupted/missing CAS blob, withdrawn `SourceDocument` (new, planned by B02/B03), deferred trigger `P22B2`), `IMMUTABLE_RECORD` (`P22B1`), two-connection barrier race on same `(capture_id, candidate_index)` yielding 1 winner + 1 `IDEMPOTENCY_CONFLICT`, post-wait credential/role expiry, and mid-UoW fault rollback leaving 0 orphan question/hypothesis rows. |
| `test_pr2_19_discussion.py` (extend for G4) | **G4 positive & negative suffix**: (1) retain bound session/turn creation (`create`, `append`, `close`, `bind_transcript`) and verify `DiscussionService.request_promotion` still raises `FORBIDDEN` with 0 writes for both HUMAN and AGENT callers; (2) `promote_discussion_to_hypothesis` on CLOSED bound sessions (B03 §§2, 3.2; OPEN rejection with `INVALID_STATE_TRANSITION` per B03 §§11.2, 12.4) creates `Hypothesis` + `HypothesisVersion` v1 (`DRAFT`, `frozen_at is None`, `success_criteria is None`) + `discussion_command_receipts` (`PROMOTE_HYPOTHESIS`) + `discussion_hypothesis_admissions`, with 0 `claims`/`literature_evidence`/`research_questions` writes (testing both HUMAN and AGENT actors); (3) fresh service restart + `get_discussion_hypothesis_admission` verifies independently computed `candidate_hash` and `HypothesisVersion.content_hash`, CAS transcript integrity, and lock-free `REPEATABLE READ` execution (`assert_snapshot_read(..., snapshots=1)`); (4) `assert_first_share` confirms `LOCK TABLE <B03_SNAPSHOT_TABLES> IN SHARE MODE` is the first SQL statement in `promote_discussion_to_hypothesis`; (5) exact `request_id` replay (including after write-role loss with read role retained) vs `IDEMPOTENCY_CONFLICT` on changed candidate payload or different `request_id` for the same `(session_id, turn_id, candidate_hash)`; (6) negative gates: `NOT_FOUND` (cross-project/missing session, turn, question, transcript, receipt), `FROZEN_REFERENCE_REQUIRED` (unfrozen question/transcript), `PROVENANCE_CLOSURE_VIOLATION` (unbound `research_question_version_id`, mismatched `turn.transcript_artifact_version_id` (new, planned by B02/B03), corrupted/missing transcript CAS bytes, deferred trigger `P17D3`), `IMMUTABLE_RECORD` (`P17D1`), two-connection barrier race on same `request_id` (both return same admission) and distinct `request_id`s for same `(session_id, turn_id, candidate_hash)` (1 winner + 1 `IDEMPOTENCY_CONFLICT`), post-wait credential/role revocation across held `SHARE` lock, and mid-UoW fault rollback before commit leaving 0 orphan `hypotheses`/`hypothesis_versions`/receipts. |
| `test_pr2_19_dependencies.py`, `tests/unit/phase2/test_pr2_19_report_contract.py`, `tests/architecture/test_pr2_19_boundaries.py` (extend) | Reconcile `G2` and `G4` subcase entries once B02/B03 land; verify `HISTORICAL_BLOCKED_ROWS` and remaining §2.2 blockers stay fail-closed; validate new `COMMANDS` labels and B02/B03 architecture boundary rules. |

Focused implementation verification (after B02, B03 and B30-S3 authorization;
not present results). The two B02/B03 test paths in the last command are
**(new, planned by B02/B03)**; the current-checkout commands are recorded in §14:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/architecture/test_pr2_19_boundaries.py
uv run pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_b02_strategy_promotion.py tests/integration/phase2/test_b03_discussion_promotion.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_10_binding_contract.py
```

PostgreSQL runs require explicit `RB_TEST_ADMIN_URL` pointing to a disposable
local PostgreSQL 18.x admin database. Do not run the full test suite manually;
the loop runner executes it after implementation.

### 12.5 Not in this slice

- No B02 or B03 production service, domain, repository, API, CLI or Alembic
  migration implementation (owned by B02 and B03).
- No implementation or unblocking of the remaining blocked rows in §2.2: G6/F6
  (`MANUSCRIPT_CHANGE` / manuscript concern cycle), G7 stronger novelty
  (`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` in B20, novelty review in B23, non-gating
  in B24/H2), G7 lock-free novelty command replay, F1 automatic finding/impact
  write propagation, F5c manuscript-purpose reconsideration, or F9 scheduled
  role-expiry commands.
- No changes to B30-S1 or B30-S2 scenarios, no new dependencies, and no Phase 3
  runtime/provider work (`B28`).

## 13. Open questions for the owner — override register

No architecture exceptions are proposed. The draft adopts the following defaults
unless the owner records an override before authorizing implementation:

1. **G2 and G4 scope**: Adopt the exact B02 (`StrategyCandidatePromotionService`)
   and B03 (`DiscussionHypothesisService`) command names, DTOs, hash domains and
   lock protocols in §§11–12, including B02's explicit researcher-adapted
   brief-section hypothesis promotion while native `candidate-v1` emits
   `hypothesis_candidates == ()`.
2. **Post-B30-S2 blocker register (§2.2)**: Keep `G6`/`F6` (`MANUSCRIPT_CHANGE`),
   `G7` (`strong-novelty` until B20/B23/B24 land), `G7` (`lock-free-completed-command-replay`
   for novelty), `F1` (`automatic finding/impact propagation`), `F5c`
   (`manuscript-reconsideration`), `F9` (`scheduled role expiry` without a
   scheduled `effective_until` command), and the full `PR2-19` gate explicitly
   `BLOCKED` with the owning slices named in §2.2.

## 14. Documentation verification note

Reviewer-remediation revision on 2026-10-19 changes only this draft and preserves
its status line. No production code, migrations, tests or dependencies changed.
The focused-run results below remain the results observed during this revision's
preceding documentation turn; no full suite was run or PostgreSQL PASS inferred.

The CLOSED-only G4 rule is supported by B03 §§2, 3 invariant 2, 11.2 and 12.4,
not by a repository name check. The following exact command and stdout establish
that owner-contract basis (unrelated matches are retained to preserve stdout):

```sh
rg -n -i 'open|closed' docs/proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md
```

```text
9:It retains the exact closed transcript, selected turn, question version and
18:3. Add closed candidate/command DTOs and reuse research's creation rules inside
51:  project roles, scoped command receipts, closed-session derivation and exact
78:turn from a CLOSED, transcript-bound session and one admitted question version.
92:2. First admission requires CLOSED, a bound exact transcript and a question
115:A candidate is the closed DTO in §11.3, not a new canonical entity. Its identity
208:material is closed and versioned; no provider metadata or opaque JSON semantics.
234:fails closed; missing transcript bytes is PROVENANCE_CLOSURE_VIOLATION, including
255:Dependencies already represented in code are PR2-10 closed discussion/exact
260:B02 and B03 should use the same owning-research admission convention: closed
270:static/type/architecture checks, and recorded counts. No open P0/P1 findings.
279:| Transcript | Exact bound ArtifactVersion bytes rendered from the closed discussion. |
308:| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/bounds/unknown field failure. |
312:| INVALID_STATE_TRANSITION | 409 | 4 | Session not CLOSED or transcript not bound. |
326:Immutable, closed DTOs; exact UUID values at Application boundary, canonical UUID
347:required session `CLOSED`, initial output `DRAFT`, and existing role sets in §4;
420:CLOSED session and matching bound transcript, same-project question parent and
451:These are read dependencies for current authorization, closed rendering and exact
479:   Add closed DTOs and pure candidate hash builder in proposed
508:- `tests/unit/phase2/test_b03_discussion_hypothesis_contract.py`: closed types,
514:  OPEN/unbound/missing/corrupt/wrong-role transcript; wrong bytes/hash; foreign
526:  READ and fail closed on corrupt saved provenance.
549:## 13. Open questions for the owner — override register
```

Command exit: 0.

For the other proposed spellings, B02 §3 invariant 2 specifies
`artifact_type='research_brief'`; B03 §3 invariant 2 specifies transcript role
`discussion_transcript`; B03 §12.1's proposed SQL uses `command_name`.
These owner-contract citations support retaining those three names. The exact
commands and stdout are recorded below. `SourceDocument` and
`turn.transcript_artifact_version_id` have instead been restored and explicitly
marked **(new, planned by B02/B03)**; this edit does not substitute new provenance
semantics for those unresolved proposed names.

```sh
rg -n "artifact_type='research_brief'" docs/proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md
rg -n 'role `discussion_transcript`|CHECK\(command_name' docs/proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md
```

```text
109:2. Frozen capture artifact is project-owned, `artifact_type='research_brief'`,
94:   role `discussion_transcript`, media type `application/json`, frozen metadata,
364:  CHECK(command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION',
```

Both commands exited 0.

All Python source line-number citations in the contract were removed. Module and
method names remain, so no unverified line or line range is offered as evidence.

Seven distinct planned files are absent. The audit prints nine unmatched path
spellings because the two Application modules also occur with their full paths:

- `tests/integration/phase2/b02_support.py` (new, planned by B02/B03)
- `src/researchbase/application/strategy_candidate_promotion.py` (new, planned by B02/B03)
- `src/researchbase/persistence/strategy_candidate_promotion_repository.py` (new, planned by B02/B03)
- `src/researchbase/application/discussion_hypothesis.py` (new, planned by B02/B03)
- `src/researchbase/persistence/discussion_hypothesis_repository.py` (new, planned by B02/B03)
- `tests/integration/phase2/test_b02_strategy_promotion.py` (new, planned by B02/B03)
- `tests/integration/phase2/test_b03_discussion_promotion.py` (new, planned by B02/B03)

The following command audits links, paths, identifier tokens and class/function
definitions. Its complete stdout is retained below, including every absent
identifier and planned path. Basename tokens resolve to repository files; the
four conceptual labels in §1 map to existing tables rather than Python classes.

```sh
python3 - <<'PY'
import pathlib, re, subprocess
p = pathlib.Path("docs/proposals/B30S3_PR2-19_Remaining_Rows_Contract_DRAFT.md")
s = p.read_text().split("## 14. Documentation verification note")[0]
files = subprocess.check_output(["rg", "--files", "--hidden", "-g", "!.git/**"], text=True).splitlines()
links = sorted(set(re.findall(r"\]\(([^)]+)\)", s)))
print("Links:", len(links), "resolved:", sum((p.parent / x).exists() for x in links))
for x in sorted(set(re.findall(r"[\w./-]+\.(?:py|md)", s))):
    if not ((p.parent / x).exists() or any(f == x or f.endswith("/" + x) for f in files)):
        print("PLANNED PATH:", x)
tokens = sorted({t for c in re.findall(r"`([^`\n]+)`", s)
                 for t in re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", c)
                 if "_" in t or re.search(r"[a-z][A-Z]", t)})
absent = []
for t in tokens:
    r = subprocess.run(["rg", "--hidden", "--no-ignore", "-l", "-w", "-F", t,
                        "src", "tests", "migrations"], capture_output=True, text=True)
    if r.returncode == 1:
        absent.append(t)
    elif r.returncode != 0:
        raise RuntimeError(r.stderr)
print("Identifiers checked:", len(tokens))
print("Absent identifiers for manual planned-name review:", ", ".join(absent))
for t in sorted({t for t in tokens if re.fullmatch(r"[A-Z][A-Za-z0-9]+", t)}):
    r = subprocess.run(["rg", "-n", r"(class|def) " + t + r"\b", "src", "tests"],
                       capture_output=True, text=True)
    if r.returncode == 1:
        print("NO CLASS/FUNCTION DEFINITION:", t)
PY
```

```text
Links: 15 resolved: 15
PLANNED PATH: b02_support.py
PLANNED PATH: discussion_hypothesis.py
PLANNED PATH: discussion_hypothesis_repository.py
PLANNED PATH: src/researchbase/application/discussion_hypothesis.py
PLANNED PATH: src/researchbase/application/strategy_candidate_promotion.py
PLANNED PATH: strategy_candidate_promotion.py
PLANNED PATH: strategy_candidate_promotion_repository.py
PLANNED PATH: tests/integration/phase2/test_b02_strategy_promotion.py
PLANNED PATH: tests/integration/phase2/test_b03_discussion_promotion.py
Identifiers checked: 286
Absent identifiers for manual planned-name review: B03_SNAPSHOT_TABLES, B06_RevisionAction_Full_Contract_DRAFT, B10_Rejection_Reconsideration_Contract_DRAFT, B30S2_PR2, CaptureNativeStrategyCommand, CaptureReadback, DiscussionHypothesisAdmission, DiscussionHypothesisCandidate, DiscussionHypothesisService, ExactStrategyQuery, NEXT_STAGE_PLAN_DRAFT, PROMOTE_HYPOTHESIS, PromoteDiscussionHypothesisCommand, PromoteStrategyHypothesisCommand, PromoteStrategyQuestionCommand, SourceDocument, StrategyCandidateCapture, StrategyCandidatePromotionService, StrategyHypothesisAdmission, StrategyQuestionAdmission, admitted_at, admitted_by, b02_capture_complete, b02_capture_immutable, b02_h_complete, b02_h_immutable, b02_q_complete, b02_q_immutable, b02_source_insert_guard, b02_sources_complete, b02_sources_immutable, b02_support, b03_admission_immutable, b03_complete_admission, b03_complete_receipt, batch_content_hash, candidate_hash, candidate_index, capture_id, capture_native_strategy, ck_b02_capture_hash, ck_b02_capture_limit, ck_b02_capture_strategy, ck_b02_capture_topic, ck_b02_h_hash, ck_b02_h_index, ck_b02_h_text, ck_b02_q_hash, ck_b02_q_index, ck_b02_q_text, ck_b02_source_ordinal, ck_b03_direction, ck_b03_hash, ck_b03_rationale, ck_b03_receipt_command, ck_b03_statement, discussion_hypothesis, discussion_hypothesis_admissions, discussion_hypothesis_repository, fk_b02_capture_actor, fk_b02_capture_artifact, fk_b02_capture_project, fk_b02_h_actor, fk_b02_h_capture, fk_b02_h_entity, fk_b02_h_project, fk_b02_h_question, fk_b02_h_version, fk_b02_q_actor, fk_b02_q_capture, fk_b02_q_entity, fk_b02_q_project, fk_b02_q_version, fk_b02_source_capture, fk_b02_source_version, fk_b03_hv, fk_b03_question, fk_b03_receipt, fk_b03_session, fk_b03_transcript, fk_b03_turn, get_discussion_hypothesis_admission, get_strategy_, get_strategy_capture, get_strategy_hypothesis_promotion, get_strategy_question_promotion, ix_b03_admission_project_receipt, pk_b02_capture, pk_b02_h, pk_b02_q, pk_b02_sources, pk_b03_admission, promote_discussion_to_hypothesis, promote_strategy_hypothesis, promote_strategy_question, section_heading, strategy_candidate_captures, strategy_candidate_promotion, strategy_candidate_promotion_repository, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_name, strategy_question_admissions, supporting_source_version_ids, test_b02_strategy_promotion, test_b03_discussion_promotion, test_pr2_19_report_contract, uq_b02_capture_artifact, uq_b02_h_candidate, uq_b02_h_version, uq_b02_q_candidate, uq_b02_q_version, uq_b02_source_member, uq_b03_candidate, uq_b03_output, uq_b03_receipt_context
NO CLASS/FUNCTION DEFINITION: CaptureNativeStrategyCommand
NO CLASS/FUNCTION DEFINITION: CaptureReadback
NO CLASS/FUNCTION DEFINITION: DiscussionHypothesisAdmission
NO CLASS/FUNCTION DEFINITION: DiscussionHypothesisCandidate
NO CLASS/FUNCTION DEFINITION: DiscussionHypothesisService
NO CLASS/FUNCTION DEFINITION: ExactStrategyQuery
NO CLASS/FUNCTION DEFINITION: NoveltyAssessment
NO CLASS/FUNCTION DEFINITION: PromoteDiscussionHypothesisCommand
NO CLASS/FUNCTION DEFINITION: PromoteStrategyHypothesisCommand
NO CLASS/FUNCTION DEFINITION: PromoteStrategyQuestionCommand
NO CLASS/FUNCTION DEFINITION: RevisionAction
NO CLASS/FUNCTION DEFINITION: ScientificConclusionVersion
NO CLASS/FUNCTION DEFINITION: SourceDocument
NO CLASS/FUNCTION DEFINITION: SourceVersion
NO CLASS/FUNCTION DEFINITION: StrategyCandidateCapture
NO CLASS/FUNCTION DEFINITION: StrategyCandidatePromotionService
NO CLASS/FUNCTION DEFINITION: StrategyHypothesisAdmission
NO CLASS/FUNCTION DEFINITION: StrategyQuestionAdmission
```

Audit exit: 0; 286 identifiers checked; 15/15 links resolved.

Focused runs used the existing shared repository virtualenv read-only because
this lane has no local virtualenv. In the table, expand `$V` as
`/Users/fengwang/Documents/ResearchBaseProject/.venv/bin`; the actual invocations
used that absolute prefix. No dependency installation was performed.

| Exact command (with the prefix expansion above) | Observed result |
| --- | --- |
| `$V/ruff check .` | `All checks passed!` |
| `$V/ruff format --check .` | `736 files already formatted` |
| `$V/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0: `0 errors, 0 warnings, 0 informations`. Static command batch exited 0. |
| `PYTHONPATH=src $V/python -m pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py --tb=no` | Exit 0: `103 passed in 2.14s`. |
| `PYTHONPATH=src $V/python -m pytest tests/architecture/test_pr2_19_boundaries.py --tb=no` | Exit 1: `1 passed, 14 errors in 2.07s`. PostgreSQL setup unavailable; not PASS. |
| `PYTHONPATH=src $V/python -m pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_10_binding_contract.py --tb=no` | Exit 1: `3 passed, 25 errors in 0.52s`. Dependency inventory passed; PostgreSQL setups unavailable, not PASS. |
| `PYTHONPATH=src $V/python -m pytest tests/integration/phase2/test_pr2_19_candidates.py -x --tb=short` | Exit 1: `1 error in 0.40s`. Diagnostic rerun confirmed `tests/disposable_postgres.py:34` fails with “Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL”. |

`RB_TEST_ADMIN_URL` is unset in this shell; no PostgreSQL server session was
executed. The B02/B03 owner suites do not exist yet and were not invoked.
No full test suite was run; its evidence belongs to the loop's subsequent check.
The full PR2-19 gate remains BLOCKED.


Reviewer scope checks (re-run after remediation):

```sh
git status --porcelain
git diff --stat HEAD
test -z "$(git status --porcelain -- . ':!docs/proposals' ':!.pipeline')"
git diff --check
```

`git status --porcelain` stdout (exit 0):

```text
 M docs/proposals/B30S3_PR2-19_Remaining_Rows_Contract_DRAFT.md
```

`git diff --stat HEAD` stdout (exit 0):

```text
 .../B30S3_PR2-19_Remaining_Rows_Contract_DRAFT.md  | 355 +++++++++++++++++----
 1 file changed, 290 insertions(+), 65 deletions(-)
```

The exact `test -z` scope check exited 0 with no stdout. `git diff --check`
exited 0 with no stdout. The status-line comparison against HEAD also passed;
only the originally requested draft is modified.


## §14 Director reconciliation 2026-10-20

The director resolved AQ-S3-01..07 using the landed B02/B03 contracts as the
canonical source under S3 §13 item 1. Their conflicting S3 wording is superseded;
see [the decision record](B30S3_Architecture_Questions_2026-10-20.md).
AQ-S3-08 remains OPEN: G2 positive AGENT admission is pending an authorized
Application fixture path. No SQL-forged AGENT binding is permitted.
