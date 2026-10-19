# M1 Manuscript Revision and Reconsideration Contract — DRAFT

**Status:** DRAFT — awaiting owner approval; not authorized for implementation

## Start here (for the implementer)

Both workflows are mandatory for Phase 2 (§1). B06/B07 defer manuscript revisions;
B10 implements release-purpose reconsideration only. These implementation limits
do not narrow the architecture.

Proposed first slices:

- **S1:** manuscript v1→v2, revision decision/action, re-review and issue disposition.
- **S2:** B10 corrected-review reconsideration for both manuscript approval purposes.
  Revised-target reconsideration remains deferred mandatory work (§12.5).

Build S1 through the existing B04/B06/B07/B08 paths, verify it, then separately
authorize S2 through B10 and the normal approval gates. §11 pins choices and DTOs;
§12 gives DDL, paths, lock order and tests. Neither slice establishes Phase 2 exit.

Five review rules:

1. Preserve frozen manuscript bytes, placements, hashes and history.
2. A completed RevisionAction does not dispose an issue; B08 records that event.
3. Keep rejected history and cover every earlier project/purpose rejection.
4. Use one lock-first READ COMMITTED write UoW; read in one lock-free snapshot.
5. Keep Review, Decision, Approval and lifecycle effects separate.

This document requires owner approval and separate implementation authorization.

## 1. Purpose, authority and current baseline

Read `AGENTS.md`, architecture `01`, `02`, `03`, `08`, `05`, corrections
`17`–`20`, and the Harness specification. Architecture paths below are under
`docs/architecture/`.

### 1.1 Architecture passages and determination

**Manuscript revision is mandatory.** `05_Phase2_Development_Specification_v1.1_Harness_Integrated.md`
§52 requires both:

> [ ] Internal Review → Issue → Decision → Revision PASS
> [ ] Basic Approval frozen target / blocking gate PASS

Its §42.6 gives the manuscript-specific path:

```text
Manuscript v1 FROZEN
→ Review
→ blocking issue
→ Decision
→ Manuscript v2
→ re-review
```

It then states: “v1 remains unchanged.” §22 similarly requires a new draft,
freeze and targeted re-review; §41.8 says “revision creates new ManuscriptVersion。”
`17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md` §4 pins
`MANUSCRIPT_CHANGE` to `result_manuscript_version_id`: “Exact FROZEN ManuscriptVersion
with placement closure.” §5 requires: “Revision tests must cover all seven action
types, every wrong result combination and frozen/terminal provenance.”

**Manuscript rejection reconsideration is mandatory.** `17` §1 includes
READY_FOR_SUBMISSION and PREPARE_SUBMISSION in the complete finite purpose policy.
§2 requires:

> After any REJECT in that Project/purpose, a later request requires a **new**
> `DecisionRecord.decision_type=RECONSIDER_REJECTION` before request creation.

The scope is every target in the same project/purpose, regardless of Publication,
lineage, UUID, version, content hash or wording. Ground (b) permits S2:

> a new independent ReviewRecord with an exact frozen basis and a reasoned
> correction of a specific factual or assessment error in the earlier review.

`18_Phase2_Design_R3_Targeted_Remediation_v1.0.md` §1 says:
“`DecisionRecord.basis` is a finite, nonempty **set of typed exact frozen references**,
not an ordered list.” `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md`
§6 preserves “publication/governance purpose tuples”; §1 requires final authorization
after blocking locks using fresh trusted DB time. Neither removes reconsideration.
`20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md` §1 says:
“Only `record_decision(INTERNAL_SCIENTIFIC_RELEASE, PROCEED)` is specified here.”
Its §7 defers no-change dismissal to a separate contract. These are command-scope
deferrals, not Phase 2 exit exemptions. The later corrections refine the §52 checklist.

### 1.2 Inspected source baseline — database NOT VERIFIED

These are source findings, not live-catalog or runtime guarantees:

- `src/researchbase/domain/revision_action.py` has all seven result keys, including
  MANUSCRIPT_CHANGE. `application/revision_action.py:_supported` denies the type.
- B04 (`migrations/versions/0048_b04_manuscript_freeze.py`) and
  `application/publication.py` admit initial manuscripts only. B06 migration 0051
  excludes manuscript results; B07 0052 and B08 0053 exclude manuscript concerns.
- B10 (`0056_b10_reconsideration.py`, `application/decision.py`) supports release
  reconsideration only. B12/B14r deny manuscript successors after rejection.
- Existing decision_basis_manuscripts/reviews/approval_decisions/revision_actions
  and the two successor-request FKs provide typed persistence. No new entity is needed.
- The source migration head is `0068_b21_unresolved_capture`; accepted migrations
  remain unchanged. Database head, constraints and enforcement are NOT VERIFIED.

## 2. Proposed scope and non-goals

S1 permits successor drafts/freezes in DRAFTING or INTERNAL_REVIEW and extends
B06/B07/B08 manuscript decisions, MANUSCRIPT_CHANGE/NO_CHANGE, re-review and disposition.
S2 permits CORRECTED_REVIEW reconsideration for READY_FOR_SUBMISSION in INTERNAL_REVIEW
and PREPARE_SUBMISSION in READY, followed by a separate successor approval request.

Preserve existing release behavior and normal approval gates. READY revision,
revised-target reconsideration and package/send behavior are outside these slices.
Optional editor UI or automated correction suggestions have no implementation.

## 3. Invariants and manuscript closure

- Create contiguous v(k+1) in the same Publication, at most one DRAFT. Freeze seals
  that draft and advances the current pointer by CAS. Frozen predecessors, their
  row_version and placements remain unchanged; historical reads need no current pointer.
- A manuscript concern accepts MANUSCRIPT_CHANGE to a later same-Publication frozen
  result, or NO_CHANGE with ACCEPT_NO_CHANGE and rationale. BLOCKING changes require
  REQUIRE_CHANGE. Upstream scientific actions retain their own concerns.
- Re-review targets the exact result (original manuscript for NO_CHANGE), independently
  of material authors and action author. Require review time ≥ action time and link
  time ≥ review time. B08 disposition additionally requires ACCEPT/MINOR_REVISION and
  no open re-review blocker. Only B08's authorized event disposes the issue.
- Current b11_closure/b11_applicable_reviews covers the selected manuscript and its
  scientific dependencies. Proposed S1 admission also carries earlier same-Publication
  OPEN/BLOCKING manuscript issues until disposition. Old reviews do not become
  affirmative v2 evidence. Freeze may precede closure; readiness/approval may not.
  Retained upstream placements retain their concerns. This policy needs owner approval.

## 4. Proposed commands, closed DTOs and readback

Extend existing services and DTOs (§11.2). PublicationService.create_draft takes
named arguments and returns DraftReadback; no new draft-command DTO is needed.
RevisionDecisionReadback and ConcernReReviewReadback gain an optional manuscript target.

S2 adds RecordManuscriptRejectionReconsiderationCommand and record/get methods beside
B10's release command, preserving its required conclusion argument. Extend the
readback with an optional manuscript ID and nullable conclusion ID, exactly-one XOR.

Thin adapters in `src/researchbase/api/routes.py` and `cli/commands/governance.py`
expose project-scoped POST/GET suffix `manuscript-rejection-reconsiderations` and
CLI `record-manuscript-rejection-reconsideration` / `get-manuscript-rejection-reconsideration`.
Accept only the closed DTO; identity/time come from trusted context.

## 5. Persistence/schema proposal — future forward migrations

Future S1/S2 forward migrations replace guards and add constraints/indexes (§12.1),
with **no new tables or columns**. Keep UUID RESTRICT FKs, VARCHAR enums, INTEGER
versions/ordinals, TIMESTAMPTZ times and CHAR(64) hashes. Add no receipt or hash scheme.
This documentation PR implements no migration.

## 6. Proposed error contract

Reuse existing ErrorCode values and the source-checked HTTP/CLI mappings in §11.3.
Return no protected existence, raw SQL or credential diagnostics. Unsupported
reconsideration grounds fail closed.

## 7. Concurrency, transactions and replay

Writes use one synchronous READ COMMITTED UoW and §12.2's literal first SHARE SQL,
before SELECT/SET LOCAL/advisory/row locks. Configure connection limits before SQL
or issue SET LOCAL after the first lock. All approval/reconsideration writers share
the project/purpose advisory scope; reread the complete rejection set after waiting.
Architecture 17 §2 describes SERIALIZABLE; the current B10 protected READ COMMITTED
protocol proposed here needs owner approval and proof of equivalent insertion safety.

Exact replay needs current read entitlement, matching actor/project/normalized command,
and saved basis verification. Changed material conflicts; a new UUID is a new command.
Retry the entire attempt after serialization/deadlock; never reuse authorization.

All reads—including draft/placement trace, manuscript audit, decision/action/history,
reconsideration and replay lookup—use one REPEATABLE READ, READ ONLY snapshot, with
no table, advisory or row locks and no constraint forcing. Saved hashes and current
validity diagnostics stay separate. Recheck authority at fresh clock_timestamp()
after the last blocking wait and immediately before writes (19 §1).

## 8. Architecture and adversarial tests to add later — NOT IMPLEMENTED

§12.4 covers direct SQL bypasses and Application/API/CLI behavior. Race evidence
must show actual backend waits, both commit orders, post-wait expiry denial and
atomic rollback. A sleep alone proves no coordination.

## 9. Dependencies, acceptance criteria and stop boundary

S1 depends on B04–B08 and current manuscript/approval validity gates; S2 on
B09/B10/B12/B14r. S2's unchanged-target correction does not require creating v2.
Acceptance needs PostgreSQL 18.x migration, saved-hash, v1→v2, corrected-review
successor and race evidence. Preserve B10 release tests. No future M1 acceptance
is claimed; after documentation verification, stop for owner review.

### 9.1 Verification — NOT PASS

Source inspection is not PostgreSQL acceptance. New M1 tests are NOT IMPLEMENTED.
The following commands check the unchanged baseline; results are recorded here
without converting failed checks into PASS.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check .
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check .
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit tests/architecture --tb=short
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@/postgres?host=/private/tmp' DATABASE_URL='postgresql+psycopg://researchbase:researchbase@/researchbase?host=/private/tmp' PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_b10_reconsideration_schema.py tests/integration/phase2/test_b10_reconsideration_concurrency.py --tb=short
git diff --check
test -z "$(git status --porcelain -- . ':!docs/proposals' ':!.pipeline')"
```

| Check | Observed result | Status |
|---|---|---|
| Ruff format/lint; Pyright | 736 files formatted; lint clean; 0 errors/0 warnings/0 informations | PASS |
| Unit/architecture: candidate and clean HEAD source snapshot | Each: 5618 passed, 5 failed, 14 errors, 9 warnings; identical 19 failure/error nodes and causes | FAILED |
| Selected PostgreSQL suites | 0 passed, 2 failed, 211 errors; database connection denied | FAILED |
| Whitespace and documentation-only scope | Both commands exit 0 | PASS |

Database head, catalog and enforcement remain NOT VERIFIED. Overall verification
is **NOT PASS**. Clean-HEAD parity identifies inherited failures; it does not make
either run successful. The comparison used untouched `git archive HEAD` sources
and a separate HEAD-only index, with the same interpreter and environment.

## 10. Glossary

| Term | Meaning |
|---|---|
| ManuscriptVersion | Exact document artifact plus frozen scientific/citation/artifact placements. |
| Current pointer | Publication navigation to the latest sealed manuscript; never historical provenance. |
| RevisionAction | Immutable completed result bound to a concern/decision; not an issue disposition. |
| REVISION_RESPONSE | B07 choice REQUIRE_CHANGE or ACCEPT_NO_CHANGE for one exact issue. |
| Re-review | Independent immutable review of the action's exact result, linked through B07. |
| Disposition | B08 event moving OPEN to ADDRESSED or DISMISSED after verifying action and re-review. |
| Reconsideration | New independent HUMAN APPROVER DecisionRecord addressing immutable rejection history. |
| Scope | All rejections in one (project_id, approval_purpose), across Publication lineages. |
| Corrected review | Fresh independent assessment explaining an identified error in a cited earlier review. |
| Successor request | New ApprovalRequest with prior_rejected_request_id and reconsideration_decision_id. |
| S1 / S2 | Proposed first manuscript revision / corrected-review reconsideration slices. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Both workflows are mandatory (§1). S1 preserves B06/B07/B08 result, decision,
re-review and disposition semantics while adding manuscript lineage. Writers retain
existing role requirements; S2 requires HUMAN APPROVER independent of every cited
rejector, new target authors, corrected/fresh reviewers and successor requester.
A subsequent approval still requires its own independent HUMAN approver.

S2 admits only CORRECTED_REVIEW. Cite every earlier scoped rejection and every
eligible fresh independent exact-target review, all committed before this command;
fresh reviews postdate the latest rejection. Each rejection must have a cited
corrected review from its saved request review set. Rationale names the rejection
and corrected review UUIDs and explains the specific error, with B10's existing
correction_explanation checks. Fresh summaries contain the reasoned correction.
Question is exactly `Reconsider rejection for READY_FOR_SUBMISSION` or
`Reconsider rejection for PREPARE_SUBMISSION`, never caller input.

The target is frozen, currently VALID and current, with no applicable OPEN/BLOCKING
issue, in the purpose's required lifecycle. A successor has the same project,
purpose and target/hash as reconsideration, cites the deterministic B10 prior
request, covers the complete rejection set again at request time, and uniquely
consumes the reconsideration via uq_b10_successor_reconsideration. A concurrent
new rejection invalidates incomplete coverage. Reconsideration creates no grant.

### 11.2 DTO fields, types, limits and enums

All IDs are strict uuid.UUID, times are aware UTC datetime, hashes lowercase
64-hex str and hash_scheme is Literal['sha256-cjson-v1']. Principal is resolved by
the adapter, not a DTO field. Frozen dataclasses and API extra='forbid' follow the
current services. Python tuple UUID sets become JSON arrays; reject duplicates,
sort canonical UUID text, and compare normalized material on replay.

| Surface | Pinned fields and bounds |
|---|---|
| Existing manuscript draft arguments | project, publication_id, document_id, request_id: UUID; title: NFC nonblank str ≤2000; abstract: NFC str or None (nonblank when present; proposed first-slice ceiling 100000); change_class: INITIAL for v1, EDITORIAL/SCIENTIFIC_MINOR/SCIENTIFIC_MATERIAL for successors. Server computes version_number: int 1..2147483647. |
| Freeze/GetManuscriptVersionQuery | project_id, publication_id, manuscript_version_id: UUID; FreezeManuscriptCommand also requires expected_placement_set_hash and expected_content_hash: lowercase 64-hex str, verified against server recomputation. No caller timestamp override. |
| RecordRevisionDecisionCommand | Existing id, project_id, review_issue_id: UUID; question/rationale: NFC nonblank str ≤16000 without NUL; decision_type: REVISION_RESPONSE; decision: REQUIRE_CHANGE or ACCEPT_NO_CHANGE. |
| RevisionDecisionReadback addition | manuscript_version_id: UUID or None = None; XOR with existing claim_version_id/scientific_conclusion_version_id. Retain actor/time, exact target hash, basis tuple and basis/content hashes. |
| RecordRevisionActionCommand | Retain all fields; action_type admits MANUSCRIPT_CHANGE; result_manuscript_version_id: UUID or None, required exclusively for that action. NO_CHANGE has seven null result fields and a required decision_record_id. |
| RecordConcernReReviewCommand / disposition | Existing project_id, revision_action_id, internal_review_record_id: UUID; ConcernReReviewReadback gains manuscript_version_id: UUID or None = None; existing disposition command/event with ADDRESSED or DISMISSED, NFC nonblank rationale ≤16000. No mutable review body. |
| Manuscript reconsideration command | id, project_id, manuscript_version_id: UUID; approval_purpose: Literal['READY_FOR_SUBMISSION','PREPARE_SUBMISSION']; decision: Literal['CORRECTED_REVIEW']; rationale: NFC nonblank str ≤16384, no NUL. rejected_approval_decision_ids, fresh_review_ids, corrected_review_ids: tuple[UUID,...], each 1..100, pairwise distinct fresh/corrected IDs. revision_action_ids: tuple[UUID,...] = (), must be empty. |
| Reconsideration exact read | project_id, decision_id: UUID plus trusted principal; no write authority required when current read entitlement survives. |
| Reconsideration readback | Existing id/project/type/decision/question/rationale/actor/time, target_content_hash, basis: tuple[DecisionBasisReference,...], basis_set_hash/content_hash/hash_scheme, supersedes_decision_id: UUID or None (always None here); scientific_conclusion_version_id: UUID or None; manuscript_version_id: UUID or None = None; approval_purpose: str; successor_request_id: UUID or None; cited_rejected_request_ids: tuple[UUID,...]; current_coverage_complete: bool; rejections: tuple[RejectedApprovalReference,...]. |

The finite enums remain: manuscript status DRAFT/FROZEN; Publication lifecycle
DRAFTING/INTERNAL_REVIEW/READY; issue status OPEN/ADDRESSED/DISMISSED; severity
INFO/MINOR/MAJOR/BLOCKING; action NEW_EXPERIMENT/ANALYSIS_CHANGE/CLAIM_CHANGE/
CONCLUSION_CHANGE/MANUSCRIPT_CHANGE/SOURCE_CHANGE/NO_CHANGE. Review recommendations
remain ACCEPT/MINOR_REVISION/MAJOR_REVISION/REJECT/UNCERTAIN; only the first two can
support B08 disposition. S2's decision type is RECONSIDER_REJECTION and its only
outcome CORRECTED_REVIEW; B10 release keeps REVISED_TARGET and CORRECTED_REVIEW.

Each basis reference is (type: str, id: UUID, content_hash: str, ordinal: int).
Use 18 §1 canonical type/id/hash sorting and re-derived ordinals on reads; S2's
allowed types are ApprovalDecision, InternalReviewRecord and exactly one
ManuscriptVersion. No RevisionAction basis is admitted by S2. Existing R2 hash
payloads remain unchanged. Manuscript placements retain the domain's 10000 total
occurrence ceiling and INTEGER ordinals; B25's bounded audit reads remain bounded.
Exceeding complete-evidence limits fails closed, never truncates a gate's evidence.

### 11.3 Error-code transport mappings

Side-by-side `grep -n "ErrorCode.<code>:"` output, with indentation removed:
all 17 pinned rows match both files. These source matches pin the mappings. REVIEW_TARGET_NOT_FROZEN
remains the repository's provisional mapping. Existing UoW normalization is reused:
P04M1/P17F1 → IMMUTABLE_RECORD; P04M2 → INVALID_STATE_TRANSITION;
P17F2 → PROVENANCE_CLOSURE_VIOLATION; P16B1 → DECISION_BASIS_INVALID;
P16R1 → REJECTION_RECONSIDERATION_REQUIRED. New checks use these categories.

| api/errors.py output (HTTP) | cli/errors.py output (exit) | Application condition |
|---|---|---|
| `38:ErrorCode.AUTHENTICATION_REQUIRED: 401,` | `35:ErrorCode.AUTHENTICATION_REQUIRED: 3,` | Unverified principal. |
| `39:ErrorCode.FORBIDDEN: 403,` | `36:ErrorCode.FORBIDDEN: 3,` | No current membership/role or protected cross-project access. |
| `42:ErrorCode.CONFLICT_OF_INTEREST: 403,` | `39:ErrorCode.CONFLICT_OF_INTEREST: 3,` | Author/reviewer/rejector/decider independence fails. |
| `37:ErrorCode.NOT_FOUND: 404,` | `34:ErrorCode.NOT_FOUND: 3,` | Authorized exact record absent. |
| `36:ErrorCode.VALIDATION_ERROR: 422,` | `33:ErrorCode.VALIDATION_ERROR: 2,` | Closed DTO, enum, shape or bound violation. |
| `46:ErrorCode.FROZEN_REFERENCE_REQUIRED: 409,` | `46:ErrorCode.FROZEN_REFERENCE_REQUIRED: 5,` | Result/document/dependency is not frozen. |
| `41:ErrorCode.REVIEW_TARGET_NOT_FROZEN: 409,` | `38:ErrorCode.REVIEW_TARGET_NOT_FROZEN: 4,` | Review target is not frozen. |
| `51:ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 409,` | `47:ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 5,` | Saved hash, complete basis or frozen closure corrupt. |
| `50:ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 409,` | `48:ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 5,` | Missing concrete FK (23503). |
| `47:ErrorCode.IMMUTABLE_RECORD: 409,` | `43:ErrorCode.IMMUTABLE_RECORD: 4,` | Attempt to rewrite sealed history or unsafe downgrade. |
| `44:ErrorCode.INVALID_STATE_TRANSITION: 409,` | `41:ErrorCode.INVALID_STATE_TRANSITION: 4,` | READY revision, wrong lineage, unsupported ground or closed issue. |
| `31:ErrorCode.DECISION_BASIS_INVALID: 409,` | `28:ErrorCode.DECISION_BASIS_INVALID: 4,` | Incomplete/cyclic/wrong-purpose rejection or revision basis. |
| `32:ErrorCode.APPROVAL_TARGET_STALE: 409,` | `29:ErrorCode.APPROVAL_TARGET_STALE: 4,` | Current target invalid, stale or wrong lifecycle. |
| `30:ErrorCode.APPROVAL_GATE_FAILED: 409,` | `27:ErrorCode.APPROVAL_GATE_FAILED: 4,` | Applicable OPEN/BLOCKING concern. |
| `33:ErrorCode.REJECTION_RECONSIDERATION_REQUIRED: 409,` | `30:ErrorCode.REJECTION_RECONSIDERATION_REQUIRED: 4,` | Successor lacks valid complete reconsideration. |
| `57:ErrorCode.IDEMPOTENCY_CONFLICT: 409,` | `54:ErrorCode.IDEMPOTENCY_CONFLICT: 4,` | Same UUID/different material, reused reconsideration or competing draft. |
| `48:ErrorCode.CONCURRENT_MODIFICATION: 409,` | `44:ErrorCode.CONCURRENT_MODIFICATION: 4,` | Failed CAS, timeout, deadlock or serialization failure after bounded retry. |

## 12. Implementation guide — future authorization required

### 12.1 DDL sketch and guard inventory

Tentative migrations: `migrations/versions/0069_m1_manuscript_revision.py`, then
`0070_m1_manuscript_reconsideration.py`; rebase numbering on the actual head before
authorization. Do not edit 0035/0042/0048/0051–0056/0058/0063/0064/0068.
No columns or tables are added. Existing result_manuscript_version_id is UUID with
a concrete ON DELETE RESTRICT FK already (migration 0044); preserve it.

```sql
-- S1; existing manuscript_versions columns: publication_id UUID,
-- version_number INTEGER, semantic_change_class VARCHAR, status VARCHAR.
ALTER TABLE manuscript_versions ADD CONSTRAINT ck_m1_manuscript_change_class CHECK (
 (version_number = 1 AND semantic_change_class = 'INITIAL') OR
 (version_number > 1 AND semantic_change_class IN
   ('EDITORIAL','SCIENTIFIC_MINOR','SCIENTIFIC_MATERIAL')));
CREATE UNIQUE INDEX uq_m1_one_draft_manuscript
 ON manuscript_versions(publication_id) WHERE status = 'DRAFT';
-- Preflight legacy duplicate drafts; fail with actionable diagnostics, never delete.
-- Preserve ck_b04_manuscript_status/seal, all RESTRICT FKs and version uniqueness.

-- Replace ck_b06_revision_action_shape with ck_m1_revision_action_shape:
-- retain every B06 arm/common guard verbatim; remove the global manuscript ban;
-- add this arm, and require result_manuscript_version_id IS NULL in other arms:
-- action_type='MANUSCRIPT_CHANGE' AND result_manuscript_version_id IS NOT NULL
-- AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
-- result_statistical_result_id,result_claim_version_id,
-- result_scientific_conclusion_version_id,result_source_version_id)=0
CREATE INDEX ix_m1_revision_manuscript ON revision_actions(result_manuscript_version_id)
 WHERE result_manuscript_version_id IS NOT NULL;

-- S2 replaces ck_b10_text_bounds, retaining its NFC/rationale bound expression.
-- Allowed questions for RECONSIDER_REJECTION become exactly these three strings:
-- Reconsider rejection for INTERNAL_SCIENTIFIC_RELEASE
-- Reconsider rejection for READY_FOR_SUBMISSION
-- Reconsider rejection for PREPARE_SUBMISSION
-- ck_b10_decision_pair and ck_b10_request_links remain; manuscript CORRECTED_REVIEW
-- membership and target XOR are enforced by the deferred validator, not free text.

-- S2 attach the existing complete validator to manuscript basis INSERTs, following
-- migration 0042's pr215_complete_* deferred constraint-trigger pattern:
CREATE CONSTRAINT TRIGGER m1_complete_manuscript
 AFTER INSERT ON decision_basis_manuscripts DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION b10_complete();
CREATE CONSTRAINT TRIGGER b10_no_basis_cycle
 AFTER INSERT ON decision_basis_manuscripts DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();
```

Forward function replacement inventory (preserve unrelated branches):

| Slice | Existing functions/guards to extend | Required database guarantee |
|---|---|---|
| S1 | pr212_draft_guard; B04 seal/placement guards | Contiguous successor under locked parent, one draft, permitted lifecycle, current-pointer CAS, no frozen predecessor update. |
| S1 | b06_validate_revision; b07_validate_revision; b07_validate_decision; b07_validate_re_review; b08_check_history; B11/B12 manuscript-basis dispatch guards | Same-project manuscript concern/result/decision, frozen closure, independence, exact re-review, disposition evidence and immutable hashes. Preserve existing completion triggers. |
| S1 | B11/B12/B14r/B14 blocker checks and matching Application queries | Include earlier same-Publication OPEN/BLOCKING manuscript issues in admission only; exact-target review basis remains exact. |
| S2 | b10_refs; b10_validate; b10_child_check; b10_basis_guard; b10_material_gate; b10_review_verify; B11/B12 manuscript-basis dispatch guards | Include exactly one typed manuscript basis; derive purpose from finite question plus cited rejection purposes; verify manuscript/review seals and complete CORRECTED_REVIEW evidence, not conclusion-specific functions. |
| S2 | b10_edges; b10_facts; b10_no_basis_cycle | Include manuscript basis edge and exact frozen manuscript facts; reject typed graph cycles at deferred completion. No generic persisted graph. |
| S2 | b10_successor_check and active B12/B14r pr216 request/decision guards | Admit complete manuscript correction successors; recheck all earlier scoped rejections, exact purpose/target and unique successor use. Retain release branch. |

Force existing/new completion constraints before commit against the complete
candidate graph. Historical verifiers must not call locking admission validators.
Reuse SQLSTATE normalization; map uq_m1_one_draft_manuscript specifically to
IDEMPOTENCY_CONFLICT in uow.py.

Each downgrade refuses with P17F1 if it would remove guarantees over committed
successor manuscripts, manuscript revision/disposition/basis history or manuscript
reconsiderations/successor requests. Otherwise restore predecessor functions,
constraints and triggers exactly. Never delete, rewrite or rehash scientific history.

### 12.2 Exact lock order and transactions

S1 draft/placement/freeze uses these **two disjoint sets**, in this order:

```sql
-- S1-A: first SQL statement; 38 tables, no target/placement table.
LOCK TABLE
  actor_subject_bindings, actors, artifact_versions,
  artifacts, audit_findings, claim_versions,
  claims, correction_records, dataset_snapshots,
  datasets, evidence_relations, experiment_spec_versions,
  experiment_specs, impact_assessments, impact_targets,
  literature_evidence, literature_evidence_relations, literature_evidence_review_events,
  literature_source_project_links, literature_sources, literature_support_snapshots,
  measurements, metric_definition_versions, metric_definitions,
  project_membership_events, project_memberships, project_role_assignments,
  projects, run_artifact_inputs, run_dataset_inputs,
  runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs,
  scientific_conclusion_versions, scientific_conclusions, source_versions,
  statistical_result_inputs, statistical_results
IN SHARE MODE;
-- S1-B: second locking statement; five tables, each at its final mode.
LOCK TABLE manuscript_artifact_placements, manuscript_citation_placements,
  manuscript_claim_placements, manuscript_versions, publications IN EXCLUSIVE MODE;
```

Confirmed against `src/researchbase/persistence/manuscript_freeze_repository.py`:
B04_SNAPSHOT_TABLES contains 41 tables, including the three placement tables but
neither manuscript_versions nor publications. S1-A explicitly excludes all five
S1-B names; their intersection is empty. No SHARE-to-EXCLUSIVE upgrade occurs.
EXCLUSIVE still permits ordinary SELECT. Sorted below means lexical name/UUID order.
B09_SHARE_SQL and B09_DECIDE_SHARE_SQL refer to the literal inventories in
`src/researchbase/persistence/approval_repository.py`. No read path takes any lock.

| Command | Ordered acquisitions (first snapshot statement included) |
|---|---|
| create_draft | S1-A → S1-B → advisory `pr212:draft:{identity}` → project FOR SHARE → Publication FOR UPDATE → current predecessor FOR SHARE → document ArtifactVersion/Artifact FOR SHARE → insert draft. Replay before allocating next number. |
| placement append (all three kinds) | S1-A → S1-B → advisory `pr213:citation:{identity}`, `pr213:claim-placement:{identity}` or `pr213:artifact-placement:{identity}` for its kind → project FOR SHARE → Publication FOR UPDATE → draft ManuscriptVersion FOR UPDATE → exact referenced target locks already required by publication_repository; insert only into that draft. |
| freeze_manuscript_version | S1-A → S1-B → Publication FOR UPDATE → selected draft FOR UPDATE → predecessor FOR SHARE → verify B04 closure → seal draft/pointer CAS → force constraints. No update to predecessor. |
| record_revision_decision | First B09_SHARE_SQL; its tables are read-only for this command → advisory `pr215:decision:{id}` → exact manuscript reviews ORDER BY id FOR SHARE → concern issue FOR UPDATE → insert typed decision/basis → force B07 and manuscript completion constraints. |
| record_revision_action | Same first inventory as revision decision → advisory `pr215:revision:{id}` → original review FOR SHARE → issue FOR SHARE → predecessor action FOR UPDATE if supplied → verify frozen result → insert action → b06_revision_complete IMMEDIATE. |
| record_concern_re_review | Same first inventory → advisory `b07:re-review:{action_id}:{review_id}` → original/result reviews sorted FOR SHARE → original issue FOR SHARE → action FOR UPDATE → insert link → b07_complete_re_review IMMEDIATE. |
| record_issue_disposition | First SHARE on sorted B09_SNAPSHOT_TABLES minus review_issues and review_issue_events (they are written here) → advisory `b08:disposition:{id}` → reviews sorted FOR SHARE → all affected issue UUIDs sorted, concerned issue FOR UPDATE and re-review issues FOR SHARE → event insert/status projection → constraints immediate. |
| record_manuscript_rejection_reconsideration | First B09_SHARE_SQL from approval_repository.py → advisory `pr215:decision:{id}` → scope advisory `pr216:scope:{project}:{purpose}` → target manuscript FOR UPDATE → Publication FOR SHARE (approval.lock_target order) → read complete rejection/review sets → write decision/typed basis → all completion constraints immediate. No manuscript/publication mutation. |
| successor request_approval | First B09_SHARE_SQL → advisory `pr216:uuid:{request_id}` → same project/purpose scope advisory → target manuscript FOR UPDATE → Publication FOR SHARE → reread rejection coverage and reconsideration uniqueness → insert request/reviews → existing constraints immediate. |
| decide_approval on successor | First B09_DECIDE_SHARE_SQL → publications IN SHARE ROW EXCLUSIVE MODE (existing deciding protocol) → existing request UUID advisory and project/purpose scope → target manuscript FOR UPDATE → Publication FOR SHARE → saved request FOR UPDATE → affected grants sorted FOR UPDATE → normal approval/rejection writes. |

Revision commands read frozen targets/parent navigation without extra row locks
under B09's protected snapshot; use read-only closure adapters for nested verification.
After every blocking wait, reread state and use fresh DB time for final authorization.
No lock upgrade is permitted. SQL-capture and pairwise race tests must prove this order.

### 12.3 Ordered build steps and module paths

All paths below are under `src/researchbase/`, except migrations/tests.

1. After authorization, check head/data and add the S1 forward migration (§12.1).
2. Extend lineage/correspondence in `domain/revision_action.py`, revision choice in
   `domain/decision.py` and disposition in `domain/internal_review.py`. Keep hashes unchanged.
3. Extend `application/ports.py`; existing `persistence/publication_repository.py`,
   `manuscript_freeze_repository.py`, `revision_action_repository.py`,
   `decision_repository.py`, `internal_review_repository.py`; wire `persistence/uow.py`.
4. Extend `application/publication.py`, `manuscript_placement.py`, `manuscript_freeze.py`,
   `decision.py`, `revision_action.py`, `internal_review.py`, `approval.py` for S1.
   Preserve B25 bounded historical reads; remove locking read authorization. Replay
   verifies saved draft fields even after freeze. Add S1 serializers in `api/routes.py`
   and `cli/commands/governance.py`; run S1 evidence.
5. Separately authorize S2 and its migration. Extend `domain/decision.py`,
   `application/{decision,approval,ports}.py`, `persistence/{decision_repository,approval_repository,uow}.py`.
   Reuse B04/B05/B11/B12 manuscript/review verification; add the closed API/CLI adapters.
6. Run §12.4 checks, retain release regressions, record exact evidence and stop.

### 12.4 Test artifacts and required cases

New test files below are planned, not present or executed by this documentation task.

| Planned file | Required cases |
|---|---|
| `tests/unit/phase2/test_m1_manuscript_revision.py` | Same/later/cross-Publication lineage; MANUSCRIPT_CHANGE result XOR; NO_CHANGE choice; disposition; unchanged canonical hash vectors; canonical basis order independent of stored ordinals. |
| `tests/unit/phase2/test_m1_manuscript_reconsideration.py` | Both purposes; strict UUID/text/tuple limits and unknown fields; only CORRECTED_REVIEW; additive readback XOR; exact HTTP/CLI code table. |
| `tests/architecture/test_m1_boundaries.py` | Application-only writes, no ORM DTOs/new canonical tables, first SQL is required SHARE, no read lock or validator invoking locks, one UoW per command. |
| `tests/integration/phase2/test_m1_schema.py` | Upgrade 0068→S1→S2, clean downgrade/re-upgrade, refusal with history; actual catalog FK/check/index/deferred-trigger names; direct SQL wrong shape/lineage/basis/purpose/cycle/partial insert; rollback leaves no history. |
| `tests/integration/phase2/test_m1_manuscript_revision.py` | Full 05 §42.6 v1 BLOCKING→decision→v2 draft/freeze→action→re-review→ADDRESSED→readiness/approval; NO_CHANGE→DISMISSED; frozen v1 bytes/row_version unchanged; v2 cannot bypass open v1 blocker; retained upstream blockers persist; historical reads after v2 are lock-free. |
| `tests/integration/phase2/test_m1_manuscript_reconsideration.py` | For each purpose reject→fresh correction review→independent reconsideration→successor request→separate approve; unchanged target accepted only with correction evidence; all project/purpose rejections across lineages cited; missing/wrong review, self-review, rejector/author/requester conflicts deny; reused decision denies; exact UUID replay survives loss of write role with read entitlement; other-project and changed replay deny. |
| `tests/integration/phase2/test_m1_concurrency.py::test_s1_two_writer_table_lock_order` | Both backends acquire S1-A, then request S1-B. Capture the disjoint table sets; show the second waits before any row/advisory lock. Release the first; both complete without 40P01 or upgrade, in both commit orders. |
| `tests/integration/phase2/test_m1_concurrency.py` | Competing drafts/freeze, freeze vs review/readiness, revision/issue/link/disposition orders, reconsideration vs rejection and successor vs new rejection, same/different UUID writers, rollback/restart; actual blocking evidence, no 40P01 loop, post-wait role/credential expiry denial and no partial records. |

Regression suites: existing unit/architecture B04/B06/B07/B08/B10 contracts;
PostgreSQL `test_b04_manuscript_{freeze,migration,races}.py`,
`test_b05_manuscript_review.py`, `test_b06_revision_{action,concurrency}.py`,
`test_b07_{schema,revision_decisions,concern_carry_forward,concurrency}.py`,
`test_b08_{schema,issue_disposition,issue_history,concurrency}.py`,
`test_b10_reconsideration{,_schema,_concurrency}.py`,
`test_b11_readiness_decision.py`, `test_b12_prepare_decision.py`, and B25 manuscript
validity/read races. New acceptance tests remain NOT IMPLEMENTED.

### 12.5 Not in this slice

- No implementation in this PR; no migration execution authorized by this draft.
- No manuscript REVISED_TARGET reconsideration: a later contract must compare
  material beyond UUID/version/hash changes, prove a relevant committed action for
  every rejection and specify any needed READY lifecycle extension. This is deferred
  mandatory coverage under 17 §2, not an optional Phase 2 feature.
- No other action types on manuscript concerns, no new manuscript SUPERSEDED state,
  no mutation of frozen history, no automatic disposition from action/reconsideration.
- No new package/send/consent behavior, broader approval purposes, UI or agent workflow.

## 13. Open questions for the owner — override register

Awaiting approval: earlier-manuscript blocker admission, serialized S1 editing's
second EXCLUSIVE lock, and S2's corrected-review-first protected READ COMMITTED scope.
Changing §1's mandatory determination requires an explicit architecture amendment.

Owner approval of this document does not authorize either implementation slice.
