# M1 Manuscript Revision and Reconsideration Contract — DRAFT

**Status:** APPROVED by owner 2026-10-20 — first slice authorized for implementation; S2 authorized 2026-10-20

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

## 14. M1-S1 implementation record (2026-10-20)

Only S1 is implemented by this change. S2 remains separately authorized work.
The forward migration is `0074_m1_manuscript_revision`, following the actual
`0073_b02_strategy_admission` head. Accepted migrations are unchanged; no tables
or columns are added.

Recorded substitutions and transaction interpretation:

- The active revision shape constraint is `ck_b23_revision_shape`, the successor
  of `revision_action_shape`; the guide's `ck_b06_revision_action_shape` does not
  exist. Its complete seven-result XOR and B23 novelty arm are preserved under
  `ck_m1_revision_action_shape`.
- The existing manuscript-basis completion trigger is `b11_complete_manuscript`.
  S1 forces this trigger alongside the existing B07 completion inventory.
- “One UoW per command” means one **write** UoW per attempt: all command writes
  commit or roll back together. Replay discovery is a separate lock-free
  REPEATABLE READ, READ ONLY query, followed on a miss by the prescribed
  lock-first READ COMMITTED writer. This follows the existing B14a/B14 query and
  command pattern and §7's explicit replay-read requirement. A successful replay
  opens no writer. No writes are split across transactions; consumption retains
  its existing SERIALIZABLE protocol. SQL-capture tests distinguish query and
  writer transactions and assert the first writer statement separately.

Successor sealing retains the original Publication entry event and manuscript;
that event proves entry into INTERNAL_REVIEW, while later admission independently
verifies the selected current frozen manuscript. Earlier same-Publication
OPEN/BLOCKING manuscript issues participate in admission without becoming
current-target affirmative review evidence. Historical seal verification does
not require the current pointer; newly sealed rows must complete the pointer
advance atomically.

Read-only source review identified two database bypasses during implementation:
seal without pointer advancement and BLOCKING manuscript change without a
REQUIRE_CHANGE decision. Both guards were corrected and normal-role PostgreSQL
regression tests were added. This record makes no Phase 2 exit or S2 acceptance claim.


### 14.1 Focused verification evidence

Commands use the existing repository virtual environment and PostgreSQL 18.6
through the supplied `DATABASE_URL` / `RB_TEST_ADMIN_URL`. Integration fixtures
create and drop disposable databases. No whole-suite run was performed.

```sh
VENV=/Users/fengwang/Documents/ResearchBaseProject/.venv/bin
"$VENV/ruff" format --check .
"$VENV/ruff" check .
"$VENV/pyright"
PYTHONPATH=src "$VENV/python" -m pytest tests/unit tests/architecture --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m1_concurrency.py --tb=short
PYTHONPATH=src "$VENV/alembic" heads
git diff --check
```

| Check | Observed result |
|---|---|
| Ruff format | 789 files already formatted |
| Ruff lint | All checks passed |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Unit and architecture | 6,204 passed; 55 warnings; 158.87 seconds |
| New M1 PostgreSQL suites | 19 passed; 68 warnings; 84.96 seconds |
| Alembic head | `0074_m1_manuscript_revision (head)` |
| Diff whitespace | exit 0; no output |

The final new suites include direct-SQL sealing/decision bypass rejection,
canonical saved basis re-derivation, v1/v2 revision and NO_CHANGE workflows,
readiness/approval/consumption, historical lock-free reads, disjoint lock waits,
fresh post-wait credentials, same/different-request competing successor drafts,
and all three placement insert/freeze/replay races. The 55/68 warnings above
are the existing Alembic `path_separator` deprecation and established connection
execution-option warning; they are retained as warnings, not reported as absent.

An intermediate unit run had 6,203 passes and one static-gate failure from the
new parametrized race test's callable union typing. Explicit test annotations
fixed it; the final complete unit/architecture run above passed all 6,204.

### 14.2 Neighboring PostgreSQL regression evidence

The commands below use `VENV` from §14.1. Counts overlap between runs and must
not be added into a unique-test total. All invocations set `PYTHONPATH=src`.

```sh
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m1_concurrency.py tests/integration/phase2/test_b14a_publication_entry.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_b14r_ready_approval.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b23_novelty_revision.py --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b23_schema.py tests/integration/phase2/test_b25_manuscript_audit.py --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_b07_schema.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b07_concern_carry_forward.py tests/integration/phase2/test_b07_concurrency.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b08_issue_history.py tests/integration/phase2/test_b08_concurrency.py tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_b10_reconsideration_schema.py tests/integration/phase2/test_b10_reconsideration_concurrency.py tests/integration/phase2/test_b11_readiness_decision.py tests/integration/phase2/test_b12_prepare_decision.py tests/integration/phase2/test_b25_manuscript_validity.py tests/integration/phase2/test_b25_manuscript_read_races.py --tb=short -q
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_b07_concurrency.py tests/integration/phase2/test_b08_concurrency.py tests/integration/phase2/test_b04_manuscript_races.py --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b04_manuscript_races.py --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b04_manuscript_races.py -k mixed_existing_repository_lock_protocols --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b08_concurrency.py::test_correction_and_disposition_both_commit_orders_without_action_lock_cycle --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b08_concurrency.py::test_new_mapping_and_disposition_never_invert_action_and_issue_locks --tb=short
PYTHONPATH=src "$VENV/python" -m pytest tests/integration/phase2/test_b04_manuscript_migration.py::test_deferred_seal_requires_pointer_and_frozen_insert_is_denied tests/integration/phase2/test_b04_manuscript_races.py::test_concurrent_freezes_first_sql_and_stable_replay tests/integration/phase2/test_b06_revision_action.py::test_incomplete_result_shapes_stay_closed tests/integration/phase2/test_b06_revision_concurrency.py::test_write_and_uuid_replay_first_statement_exact_inventory_and_no_scientific_row_lock tests/integration/phase2/test_b06_revision_concurrency.py::test_claim_source_witness_commits_during_inventory tests/integration/phase2/test_b07_concurrency.py::test_all_writes_and_replays_begin_with_inventory tests/integration/phase2/test_b08_concurrency.py::test_creation_and_uuid_replay_begin_with_exact_share_inventory 'tests/integration/phase2/test_b07_concern_carry_forward.py::test_explicit_attestation_never_inherits_other_action_links[REJECT-True]' --tb=short
```

| Invocation above | Exact observed result |
|---|---|
| Entry/readiness/approval/novelty selection | 160 passed; 575 warnings; 741.30 seconds |
| B23 schema and B25 audit | 61 passed; 165 warnings; 243.91 seconds |
| Required neighboring regression selection, started before fixes | 519 progress marks: 503 passed, 14 failed, 1 skipped, 1 setup error; double-quiet output did not print a numeric summary |
| Intermediate lock regression selection | 125 passed, 14 failed; 420 warnings; 862.85 seconds |
| B04 races after writer-pause correction | 23 passed, 3 failed; 79 warnings; 119.64 seconds |
| B04 compatible-owner focused rerun | 3 passed, 23 deselected; 10 warnings; 9.98 seconds |
| B08 correction/disposition focused rerun | 2 passed; 6 warnings; 20.47 seconds |
| B08 mapping/disposition focused rerun | 2 passed; 6 warnings; 19.26 seconds |
| Final exact-node repair/error rerun | 11 passed; 33 warnings; 43.62 seconds |

Every failed/error node in the two earlier selections passed a subsequent
focused run. The exact-node rerun includes the formerly failing normal-role
seal-without-pointer test and the predicate-lock-memory setup error. The latter
was an inherited SERIALIZABLE fixture exhausting PostgreSQL shared predicate-lock
memory while several selected suites overlapped; the final isolated rerun
passed without database configuration changes.

Updated old expectations reflect the mandated protocols: query replay discovery
is lock-free; writers begin with their expanded exact inventory; disposition
waits first on relation locks; B04 pause hooks wait until the writer has acquired
its inventory rather than pausing its replay query. Legacy owner probes whose
SHARE inventories are compatible with S1 freeze now prove they finish while the
freezer is paused, instead of demanding the removed project advisory/row lock.
The former unavailable-MANUSCRIPT_CHANGE test now checks an unresolved result
UUID as NOT_FOUND; scientific-target/manuscript-action incompatibility remains
covered by domain and M1 acceptance cases. B23 active function/constraint
inventories append the 0074 overrides and preserve the B23 novelty branch.

Final post-edit static acceptance recheck:

```sh
PYTHONPATH=src "$VENV/python" -m pytest tests/unit/phase2/test_pr2_04_static_acceptance.py --tb=short
```

Observed: **1 passed, 1 warning in 10.33 seconds**. Ruff format and lint were
also rerun after the last test-expectation edit: **789 files already formatted**
and **All checks passed**. `git diff --check` remained clean.

### 14.3 Review correction and R2 verification

The owner's review rejected the R1 check: the changed-file pre-check stopped at
`test_revision_action.py::test_claim_change_exact_successor` with **1 failed,
467 passed**, so R1 did not establish a passing gate. The earlier selected-suite
reruns did not cover this legacy file's complete current lock behavior.

The reproduced cause was test synchronization, not malformed PL/pgSQL. B09's
required inventory includes `claim_versions`. The old test paused the recorder
after SHARE acquisition, then waited for an UPDATE to finish before releasing
the recorder. That UPDATE now correctly waits for a RowExclusiveLock. The test
now proves the PostgreSQL wait on `claim_versions`, releases the recorder in
`finally`, and verifies the immutable-row guard rejects the UPDATE with 23514.
A second legacy overlap test now observes the earlier `claim_versions` UPDATE
wait rather than expecting the later `claims` UPDATE. The required lock
inventory was preserved.

The new outer manuscript/scientific branch in `b07_validate_revision` closes
before correction-chain traversal. The existing scientific result-validation
block is unchanged. The [full installed function](evidence/M1-S1-function-review/b07_validate_revision.sql)
and [32 individual function diffs against the actual 0073 catalog](evidence/M1-S1-function-review/README.md)
are provided without truncation. Regenerate them with
`uv run python -m scripts.m1_sql_review`; this uses a disposable database.
The upgrade smoke test executes the installed validator and checks its specific
empty-basis rejection. The valid legacy claim-successor test additionally calls
the function directly on its saved RevisionAction.

Repository snapshot preparation now requests READ COMMITTED options only for a
fresh Session. Configured UoWs retain their existing isolation without a
redundant, ignored `connection(execution_options=...)` call. Runtime PostgreSQL
probes run after first SQL and assert READ COMMITTED for repository writers,
REPEATABLE READ / READ ONLY for historical Application reads, and SERIALIZABLE
for the READY consumption writer. Tests promote SAWarning to an error for both
repository entry points with fresh and already-configured Sessions. The B05
architecture Session stub implements `in_transaction()` as the real API does;
its exact-first-SQL assertions are unchanged.

Focused R2 commands (with `UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache` because the
sandbox cannot write the user's default uv cache):

```sh
uv run pytest tests/integration/phase2/test_revision_action.py -x
uv run pytest tests/integration/phase2/test_revision_action.py::test_claim_change_exact_successor --tb=short
uv run pytest tests/architecture/test_m1_boundaries.py
uv run pytest tests/architecture/test_m1_boundaries.py tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m1_concurrency.py --tb=short
```

Observed: **55 passed, 173 warnings in 194.25 seconds** for the complete legacy
revision-action file; **1 passed, 3 warnings in 3.19 seconds** for the explicit
valid-function call; **2 passed in 0.44 seconds** for M1 architecture; **26 passed,
79 warnings in 83.41 seconds** for architecture plus the new M1 PostgreSQL suites.
The latter comprises 2 architecture + 7 schema + 4 revision + 13 concurrency
cases: **24 new M1 PostgreSQL cases**. Its warnings are Alembic deprecations;
no ignored-isolation SAWarnings remain in that run.

Lock evidence exists in `test_m1_disjoint_final_mode_edit_inventory`,
`test_s1_two_writer_table_lock_order`, the post-wait credential and competing
successor tests, and the updated legacy revision races. Read-lock rejection is
asserted in `test_manuscript_revision_decision_action_re_review_disposition` and
`test_historical_placement_trace_and_replay_after_successor_are_lock_free`.

The complete R2 unit/architecture run also passed: **6,204 passed, 54 warnings
in 173.10 seconds** (`uv run pytest tests/unit tests/architecture --tb=short`).
The read-only SQL review of all 32 actual-catalog diffs found no P0/P1 and
confirmed retained scientific/B23 dispatch and no S2 behavior. The first R2
checker attempt stopped at the outdated B05 Session stub (**1 failed, 8 passed**);
that stub was corrected, and the full unit/architecture run above passed.

The requested R2 check was rerun exactly, with only the uv cache redirected to
an allowed temporary path:

```sh
export UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

| Stage | R2 observed result |
|---|---|
| Pyright | 0 errors, 0 warnings, 0 informations |
| Ruff format | 790 files already formatted |
| Ruff lint | All checks passed |
| `git diff --check HEAD` | exit 0, no output |
| Runner's 42-file changed-test pre-check | **2,898 passed, 1,366 warnings in 1,868.72 seconds (31:08)** |
| Six full-suite shards | **NOT RUN: sandbox filesystem blocker** |
| Overall requested check | **NOT PASS / BLOCKED**; stopped the runner's retry loop, command exit 1 |

After its successful pre-check the unmodified runner could not acquire its
shared mutex. It emitted `Operation not permitted` for both
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock`
and `full_suite.lock2` (including their `pid` files). These shared runner paths,
and its `test_durations.json`, are outside the session's writable repository and
temporary-directory roots. Read-only `os.access(..., os.W_OK)` checks also
returned false. No runner or governing Harness file was modified to bypass this
restriction. The waiting retry loop was interrupted only after the pre-check
finished and the filesystem errors were observed.

The user was asked asynchronously to enable those runner paths or supply the
outer pipeline's check output. Full-suite acceptance remains pending that
external execution/access change. The successful focused and pre-check results
above do not constitute a full-suite PASS.


### 14.4 Director regression repair

The director reproduced 18 deterministic regressions in the R2 tree. The
[repair record](evidence/M1-S1-regression-repair.md) lists one cause per test,
exact verification commands/results, the installed validator's IF/END IF pairing,
and 0074 upgrade/downgrade evidence.

The director's compatibility instruction limits the new M1 editing inventory to
successor paths. INITIAL creation and initial-version placement/freeze preserve
their PR2-12/B04 protocols, including B04's project coordination on freeze replay.
The dedicated successor preparation still takes §12.2's M1-A then disjoint M1-B.
This supersedes earlier implementation notes describing initial freezes as M1
writers or asserting that compatible owner probes no longer wait on the project.

Revision decision/action/re-review still use full B09; disposition uses precisely
§12.2's B09 minus the two written issue tables. Admission retains the existing
applicable-review query and adds earlier same-Publication blockers using relations
available at predecessor schemas. Retained blocker review verification checks saved
seals without readmitting bytes. Exact-target affirmative basis and final trusted-time
authorization are preserved. S2 and the director's full-suite gate remain separate.

Final focused repair evidence: exact regressions **18 passed**; complete M1
PostgreSQL suites **31 passed**; unit/architecture **6216 passed**; **275 existing**
selected PostgreSQL neighbors passed. The neighbor run's sole new-test observer
failure was corrected and is included in the passing final 31-case M1 run.
Ruff reports **790 files formatted** and clean lint; Pyright reports **0 errors,
0 warnings, 0 informations**; `git diff --check HEAD` passes. The linked repair
record retains intermediate failures and exact commands/counts. The whole suite
was not run; that check remains with the director's loop.
