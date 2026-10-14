# PR2-19 E2E + Failure Injection Test Plan — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only. This plan is not an architecture freeze,
ADR, execution pack, migration authorization, PR acceptance or Phase 2 exit
declaration. No tests, production commands, schema or governing files are changed.
Owner approval of this plan requires separate engineering authorization before
implementation. Unavailable prerequisites remain BLOCKED, never PASS.

## 1. Purpose, authorities and inspected baseline

Propose reproducible evidence that the Phase 2 literature, discussion, publication
and governance paths preserve exact scientific provenance under success,
misleading candidate output, upstream correction, forbidden promotion and
approval bypass. Assertions concern durable facts and observable denial, not
whether generated prose sounds plausible.

| Authority | Constraint carried into this plan |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–9, 22–26, 37 | Fact precedence, immutable history, frozen closure, distinct Review/Decision/Approval/Command/ExternalEffect and shared Application boundary. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A2–A5, A10, A18–A23 | LiteratureSearchExecution naming, concrete FKs, R2/R3/R4 precedence, temporal evidence and bounded Decision command. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 rows | Existing canonical owners; no new test-result scientific entity; citation placement differs from support. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 40–41, 52 | Preserve Phase 1 hashes/semantics, stable errors, exact references, golden regression and external Harness boundaries. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§42–43, PR2-19 and §49 | Six golden paths, five failure families and thirteen mandatory architecture tests. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 4, 6–7 | PreparedSubmissionVersion is prepared only; typed provenance, current validity, independent approval and transaction boundaries. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md) | Literal hash material; finite approval tuples, rejection scope, receipts and fresh post-lock authorization. |
| [PR2-15 base](PR2-15_RevisionAction_Contract_DRAFT.md), [PR2-16 base](PR2-16_Basic_Approval_Contract_DRAFT.md) | Owner-approved bases, per task instruction, approved 2026-10-14 and being implemented; completed RevisionAction, bounded request/decision/grant slice and explicit deferred paths. |

The base files retain DRAFT banners and earlier verification dates in this
checkout. Their owner approval is supplied by the task, not inferred from those
banners or implementation presence. Treat their contract choices as the base;
do not rewrite their status or claim their implementations are accepted. This
PR2-19 proposal itself has no approval. Higher-authority scientific invariants
retain precedence.

Inspected code provides these concrete starting points:

- [SourceVersionService](../../src/researchbase/application/source_version.py)
  has typed correction/retraction lineage and frozen references;
  [LiteratureEvidenceService](../../src/researchbase/application/literature_evidence.py)
  separates document import, evidence creation, independent verification and
  LiteratureSupportSnapshot. Source identity or retrieval alone is not evidence.
- [ScientificConclusionService](../../src/researchbase/application/scientific_conclusion.py)
  consumes exact Claim/snapshot or direct literature inputs, verifies current
  support at admission and projects later invalidity separately from history.
- [DiscussionService](../../src/researchbase/application/discussion.py) records
  sessions/turns and binds derived artifacts; `request_promotion` explicitly
  returns FORBIDDEN. Successful scientific promotion is not available here.
- [PublicationService](../../src/researchbase/application/publication.py) supplies
  identity/draft commands; [placement services](../../src/researchbase/application/manuscript_placement.py)
  and [ManuscriptScientificTraceService](../../src/researchbase/application/manuscript_scientific_trace.py)
  expose exact persisted paths. Citation semantics are `CITATION_ONLY` and
  other placements `PLACEMENT_ONLY`, not inferred scientific support.
- [InternalReviewService](../../src/researchbase/application/internal_review.py)
  records Claim/conclusion reviews and initial OPEN Issues.
  [DecisionService](../../src/researchbase/application/decision.py) implements
  only INTERNAL_SCIENTIFIC_RELEASE/PROCEED, complete saved review basis and no
  replacement. Initial OPEN Issue history is not disposition authority.

No Basic Approval or RevisionAction Application implementation is present in
this inspected baseline. Manuscript freeze/review, successful promotion, Issue
disposition and consuming effects must be checked against their eventual
authorized contracts, not manufactured in E2E fixtures. PR2-19 cannot repair
missing prerequisites by implementing later functionality.

## 2. Scope and non-goals

Future PR2-19 adds test orchestration, deterministic provider doubles, isolated
fixtures, fault injection and evidence reporting for accepted Application paths.
Every golden path must cross multiple owning services, persist to real
PostgreSQL 18.x, then read through a new UoW/service instance. API/CLI parity is
tested only where an authorized adapter exists; missing routes are not invented.

Exclude production semantics/schema changes, new runtime dependencies, live LLM
grading as a gate, provider activation, venue send, ExternalEffect, general Agent
Runtime, automatic Issue resolution, new Decision purposes and full authority
engine. PR2-17 prepared-package and PR2-18 novelty checks are dependency coverage,
not authorization to implement those PRs. PR2-09 optional adapter deferral follows
its existing policy; it cannot excuse mandatory native-strategy coverage.

## 3. Invariants and evidence oracle

1. Deterministic facts outrank confidence, ranking, review, PROCEED and approval.
   Invalid closure cannot become valid through a Human click or generated text.
2. SourceVersion, LiteratureEvidence, verified support, citation placement and
   manuscript wording remain distinct. A citation-only path may be legitimate
   presentation but never counts as support for the statement.
3. Every admitted formal reference resolves to an exact ID/hash with typed FK
   closure. New current pointers cannot move historical edges. SUPERSEDED alone
   does not invalidate frozen historical bytes; correction/retraction adds lineage
   and validity/impact history rather than overwriting old content.
4. Phase 1 Claim content/support hashes and EvidenceRelation semantics are
   unchanged. Phase 2 LiteratureSupportSnapshot owns literature support; do not
   insert literature into the frozen Phase 1 support hash to make a test pass.
5. Strategy/RAG/search/discussion output is candidate state. Explicit authorized
   owning commands validate any admission. No Phase 3 AgentPromotionRecord or
   fabricated AgentExecution is created to test a Phase 2 candidate.
6. Review evaluates, Decision chooses, RevisionAction records completed change,
   Approval authorizes and a consuming command performs a separately contracted
   effect. None disposes an Issue or changes scientific material implicitly.
7. Failed commands roll back all of their protected canonical writes. Already
   committed predecessor commands survive. A scenario is not one giant transaction.
8. Same authenticated Application boundary applies to Human and Agent. HUMAN
   approver/independent reviewer requirements remain enforced; OWNER and
   acting_on_behalf_of do not substitute. Cross-project access is deny by default.
9. Test evidence is operational, not canonical scientific truth. Report actual
   assertion counts, skipped/blocked prerequisites, exact source revision and
   evidence locations. A caught exception without durable-state assertions is
   insufficient failure evidence.

For each scenario capture pre/post exact IDs, own and binding hashes, relation
sets, lifecycle/event counts, applicable validity projections and artifact digest
verification. Read committed state on a separate connection after success or
rollback. Also assert absence of unintended tables/rows/events/effects. Use
known fixture bytes and independent expected relation sets/hash vectors instead
of obtaining the expected answer from the command under test.

## 4. Commands, DTOs and orchestration proposal

No new product command or API DTO is proposed. Test code calls the existing
closed command DTOs or owning service inputs with verified-principal context;
principal, clock and role are never caller assertions. Tests must not bypass
authorization with an ORM object or a fake canonical result.

| Boundary | Inputs/results to exercise |
| --- | --- |
| Source/evidence/conclusion | Existing CreateSourceVersion/TransitionSourceVersion; evidence import/create/review/snapshot; ClaimInputRequest/LiteratureInputRequest; conclusion create/revise/freeze/read. Verify exact references and independent review events. |
| Search/strategy/RAG | Existing provider-neutral request/response and candidate DTOs; fixed corpus, limits and adapter fingerprints. Promotion uses a separately accepted owning command, never provider persistence. |
| Discussion/publication/trace | Existing session/turn/close/bind calls; publication draft and placement calls; DiscussionReadback and ManuscriptScientificTrace. Preserve CITATION_ONLY and separate experiment/literature paths. |
| Review/Decision | ReviewIssueRequest and immutable review readback; RecordDecisionCommand/DecisionReadback restricted to the accepted purpose/value and complete basis. |
| PR2-15 RevisionAction base | Future RecordRevisionActionCommand/RevisionActionReadback: exact Issue/eligible Decision, seven finite result fields and predecessor. NO_CHANGE and decision-only paths stay unavailable without revision-purpose contract. |
| PR2-16 Approval base | Future RequestApprovalCommand/DecideApprovalCommand and exact-ID request/decision/grant reads. INTERNAL_SCIENTIFIC_RELEASE only in the bounded slice; grant creation creates no consumption/effect. |

Propose immutable **test-only** `ScenarioSpec` fields: scenario ID, authority
clause, prerequisite IDs/contracts, actor arrangement, fixture case, ordered
command steps, one finite fault point and expected outcomes. `ScenarioObservation`
records step index, command identity, result IDs/error code, state deltas, verified
hashes, transaction/lock observations and evidence paths. These are Python test
records or report structures, never Application/persistence entities. No generic
JSON execution DSL, arbitrary SQL hook from a caller, test HTTP route or new
scientific content hash is required. Canonical UUID replay and normalized payload
comparison remain owned by each command's existing contract.

## 5. Schema proposal — proposal only, no migration

**DO NOT ADD SCHEMA.** PR2-19 needs no new canonical tables, columns, enum,
Alembic revision or test receipt in PostgreSQL. Reuse the accepted Entity,
Relation, Assessment, Snapshot and Event structures via owning commands.
RevisionAction and Approval tables belong to their separately authorized PRs;
this plan neither admits nor migrates them. No TestRun, FaultInjectionRecord,
universal target pair or canonical evidence-report entity is proposed.

Fixtures normally enter through Application commands. Normal-role direct SQL is
reserved for constraint/immutability adversarial probes on disposable databases,
with rollback and explicit expected rejection. Privileged corruption setup, if
needed to test defensive readers, is confined to a separately identified isolated
case and is never evidence that normal writers can perform that mutation.
Verify concrete FKs, XOR targets, same-project/parent constraints, RESTRICT,
sealed relations and immutable guards from the accepted catalog. Existing
migrations/hashes are not edited. Future acceptance exercises clean install and
frozen Phase 1 upgrade; populated-history downgrade must preserve data or refuse
as contracted. Broader performance/inventory hardening stays with PR2-20.

## 6. Golden paths to add later — NOT IMPLEMENTED

All paths include restart/readback and an exact replay or command-specific
duplicate check. A partial implemented prefix does not satisfy the complete row.

| ID / 05 reference | Steps | Required oracle and dependency limit |
| --- | --- | --- |
| G0 / 08 §41 G1 | Hypothesis → exact Spec → sealed Run → Measurement/StatisticalResult → frozen Claim | Existing Phase 1 golden remains green; snapshot/artifact/metric inputs and historical hashes unchanged after Phase 2 operations. |
| G1 / §42.1 | Frozen question/search plan → LiteratureSearchExecution/query/results → explicitly resolved frozen SourceVersion → evidence creation → independent verification → conclusion inputs/freeze | Complete source/locator/review/Claim-or-literature closure. Search result alone creates no evidence; unsupported and contradictory inputs remain visible. |
| G2 / §42.2 | Native strategy → deterministic query/candidate output → ResearchBrief Artifact → explicit question/hypothesis draft admission | Identifiable strategy/adapter revisions; candidate artifact alone changes no scientific state. Successful promotion suffix blocked until authorized promotion contract exists. |
| G3 / §42.3 | Exact project corpus → ScientificRAG/PaperQA candidate → source/locator/excerpt resolution → evidence creation → independent verification | Corpus scope, bytes and citation resolution checked independently; no tool confidence becomes VERIFIED. Offline doubles are mandatory; pinned adapter compatibility remains distinct from live-provider availability. |
| G4 / §42.4 | Discussion turns → close → transcript/concept-map artifact → hypothesis candidate → explicit HypothesisVersion DRAFT promotion | Transcript/references/attribution retained; no Claim/Decision or support created implicitly. Current code tests denial only; positive promotion suffix remains BLOCKED. |
| G5 / §42.5 | Frozen Claim/conclusion → manuscript draft → Claim/conclusion/citation/artifact placements → manuscript freeze → scientific trace | Separate citation/support paths; exact IDs/locators/ordinals/hashes and CAS bytes. Frozen suffix requires manuscript freeze contract; never freeze a fixture by SQL to claim E2E success. |
| G6 / §42.6 + bases | Old target → independent Review/OPEN Issue → completed new result → RevisionAction → new exact-target review → eligible Decision → ApprovalRequest/Decision/Grant | Preserve old target/review/Issue/action trace. Recording action leaves Issue OPEN. Issue disposition, manuscript review and revision-purpose Decision suffixes need separate contracts. Separately test no-blocker conclusion PROCEED → request → approval → one grant without release. |
| G7 / PR2-17/18 dependencies | Ready manuscript → prepared package/authorship/current consent; Claim → prior art/search coverage/novelty | PreparedSubmissionVersion proves no send; novelty never establishes universal priority. Run only accepted contracts; unavailable dependencies block their row and full required coverage. |

Use distinct author, independent evidence verifier/reviewer, Decision decider,
requester and HUMAN approver where the base requires independence. Use canonical
Actor IDs to prove each prohibited equality as a negative case. Do not silently
make one test actor satisfy incompatible duties by assigning multiple roles.

## 7. Failure injection matrix — NOT IMPLEMENTED

Each negative case has a paired valid control proving the test reaches the
intended gate. Inject exactly one fault initially; add finite combined cases
only to prove precedence, such as unauthorized cross-project corrupt targets
remaining nondisclosing. Missing prerequisites are BLOCKED, not expected denials.

| ID / authority | Fault and observation | Required durable outcome |
| --- | --- | --- |
| F1 / §43 F1 | After G1/G5, create/freeze same-source RETRACTED or CORRECTED successor with exact predecessor and frozen correction basis; append authorized AuditFinding/ImpactAssessment as required by owning contracts | Old SourceVersion/evidence/conclusion/manuscript bytes, hashes and FKs remain unchanged/readable. Current affected conclusion/manuscript validity becomes STALE/INVALID as contracted; unaffected paths stay valid. First new formal admission/approval denies invalid support. Do not claim automatic finding creation unless its source writer contract requires it. |
| F1b / lineage | Missing/wrong-parent/unfrozen predecessor or correction basis; race two corrections | Stable lineage/frozen-reference denial, no partial version/current-pointer/event writes; one accepted lineage under coordinated races. |
| F2 / §43 F2 | Strategy/RAG candidate invents DOI/source UUID, points outside corpus/project, quotes absent paragraph or substitutes another source's excerpt | Candidate warning/rejection at resolution boundary; no fabricated SourceVersion, evidence, VERIFIED event or support edge. Missing citation and resolvable-but-wrong quotation are separate cases. A provider warning is not a fabricated new ErrorCode. |
| F2b / integrity | CAS bytes missing/corrupt; changed stored hash; unresolved formal FK in privileged corruption fixture | Owning read/admission fails closed; no silent latest fallback or warning upgraded to formal success. Secrets/raw provider exception chains absent from diagnostics. |
| F3 / §43 F3 | Add a valid citation placement for a source that does not support the exact statement; omit typed support, or use another Claim/version's support | Trace reports CITATION_ONLY with no invented support path. Audit identifies unsupported assertion if audit contract exists; ordinary citation placement need not itself fail. Independent support admission cannot rely on bibliography appearance. Phase 1 hashes remain unchanged. |
| F4 / §43 F4 | Human/Agent DiscussionTurn asserts truth or embeds “approve/promote” instructions; close/bind artifact; call current request_promotion | Zero new Claim/Hypothesis/Decision/support/scientific-placement rows from discussion alone; current promotion returns FORBIDDEN. Future explicit valid promotion creates only contracted DRAFT output; unfounded freeze/support and duplicate changed payload deny. |
| F5 / §43 F5 + approval base | OPEN/BLOCKING exact-target Issue at request and again at decision; old PROCEED/favorable subset/override flag/lifecycle toggle attempted | Gate denies with zero new request or zero decision/grant/events, respectively; committed earlier history persists. Unknown bypass fields deny. Manuscript READY bypass row requires manuscript contracts; conclusion row tests bounded slice independently. |
| F5b / facts and authority | Stale/retracted support, hash mismatch, wrong project/target/purpose/command; Agent APPROVER, OWNER-only, on-behalf-of, every forbidden actor equality, expired/revoked credential/role | Denial without disclosure or mutation; deterministic invalidity cannot be overridden by prior approval. Complete basis includes unfavorable/UNCERTAIN reviews and all current applicable blockers. |
| F5c / rejection | Same-project/purpose REJECT then changed UUID/hash/version/approver; pre-created request decided after another target's rejection | REJECTION_RECONSIDERATION_REQUIRED; no grant. Existing replay remains historical read. RevisionAction/PROCEED cannot serve as reconsideration or Issue dismissal. |
| F6 / completed revision | Planned/DRAFT/wrong-project/unrelated result, invalid Spec/Run pair, NO_CHANGE with only Issue or minimal PROCEED; supersession fork | No action row/hash/history. All seven finite accepted shapes tested when result/relevance contracts exist; valid action creates no Issue disposition, approval or scientific result. |
| F7 / command atomicity | Inject after parent insert, relation insert, event insert, decision insert and before grant/event completion, or before commit | Failed command's entire write set rolls back. Prior committed scenario steps remain; CAS orphan bytes are not canonical success and follow existing storage cleanup policy. |
| F8 / recovery | Lost response after durable commit, identical concurrent UUID, changed payload, service restart; serialization/deadlock faults | Exact entitled replay returns saved IDs once, no duplicate events/effects; changed material conflicts. Bounded whole-command retry exhausts without partial state. Denied historical reads do not execute mutation. |
| F9 / consuming effects dependency | Wrong/expired/stale/consumed grant, concurrent use, role loss/new blocker, completed receipt replay after authority loss | Only separately authorized consuming command may produce one scoped consumption/result atomically. Exact completed replay uses current read entitlement, not renewed effect authorization; denied replay creates no new effect. Current grant creation alone cannot PASS this row. |

For F1 explicitly test direct literature conclusion inputs and Claim-linked
LiteratureSupportSnapshot independently. Retraction evidence must traverse typed
SourceVersion dependencies, not a title match. Assert projected downstream
manuscript validity only through an accepted validity/audit query; if absent,
that obligation remains blocked rather than adding a persisted status in tests.

## 8. Error expectations and compatibility

Pin exact expected codes per owning command in the future execution matrix.
No PR2-19 error enum or transport mapping is proposed. Authenticate and establish
entitlement before protected existence/hash/conflict diagnostics; compare
sanitized bounded public diagnostics, not driver exceptions or SQL strings.

| Codes / standing | Scenario expectation |
| --- | --- |
| Existing AUTHENTICATION_REQUIRED, FORBIDDEN, CONFLICT_OF_INTEREST | Missing principal, project/read/write/temporal authority and actor independence; current discussion promotion uses FORBIDDEN. |
| Existing VALIDATION_ERROR, NOT_FOUND, SOURCE_VERSION_NOT_FOUND | Closed DTO errors and authorized absence at the actual owning boundary; do not homogenize source-specific absence codes. |
| Existing FROZEN_REFERENCE_REQUIRED, VERSION_NOT_FROZEN, REVIEW_TARGET_NOT_FROZEN, SOURCE_VERSION_NOT_FREEZABLE, INVALID_SOURCE_VERSION_LINEAGE | Owning frozen-state/lineage checks; expected code depends on tested command. |
| Existing PROVENANCE_CLOSURE_VIOLATION, REFERENTIAL_INTEGRITY_ERROR, IMMUTABLE_RECORD, SOURCE_VERSION_IMMUTABLE | Corrupt or unresolved closure, strong-reference or immutable-write attempts. HASH_MISMATCH in design text is not an implemented ErrorCode member here. |
| Existing IDEMPOTENCY_CONFLICT, CONCURRENT_MODIFICATION, INVALID_STATE_TRANSITION | Changed replay, bounded concurrency exhaustion and unavailable lifecycle transition. No automatic retry of permanent denial. |
| Design/base APPROVAL_GATE_FAILED, DECISION_BASIS_INVALID, APPROVAL_TARGET_STALE, APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, REJECTION_RECONSIDERATION_REQUIRED, GRANT_INVALID, GRANT_STALE | Require PR2-16/effect implementation's approved exact enums/mappings before tests freeze. These are not implemented ErrorCode members in this baseline. |

Candidate-level unresolved citations may produce a structured rejection/warning
rather than a command error. Capture the actual candidate contract and zero
canonical delta. Retry transient infrastructure errors only under the owning
retry contract; changing UUID or shopping approvers is not recovery.

## 9. Concurrency and transaction proof

One synchronous Application command equals one PostgreSQL 18.x UoW transaction,
except already approved search external-call reservation/completion patterns.
Do not hold a scientific transaction across provider/LLM network work. Use
provider doubles to observe transaction closure at call time and retain separate
execution/query/result history; timeout/cancel/unknown outcome is not success.

Test the accepted shared lock matrix rather than inventing PR2-19 lock order.
PR2-15 request coordination → exact target → sorted SHARE-table snapshot and
PR2-14 target-coordinated writers must remain compatible with approved
PR2-16 rejection-scope/authority/target coordination. Inventory all participating
writers before future tests freeze. A missing participant is a P1 finding in its
owning PR, not permission for test code to add an Application-only safety lock.

Mandatory two-session schedules: review/Issue versus Decision/request/approval
in both commit orders (including zero-Issue review INSERT); upstream invalidity
versus formal admission; approval versus role loss; APPROVE versus REJECT on one
request; other-target REJECT versus pending approval; same UUID replay; revision
supersession fork; and grant use versus blocker/revocation when consumption exists.
If concern commits first the later command rereads and denies/includes it; if
governance commits first the concern remains appendable and prevents future use
without rewriting historical decisions. No favorable-subset or cached-list gate.

Use barriers and separate backend PIDs, observe pg_stat_activity,
pg_blocking_pids()/pg_locks, record actual wait/commit order and verify committed
rows afterward. Sleeps alone are not race proof. Bound waits, clean sessions in
finally blocks and fail explicitly on missing synchronization. Retry tests inject
deadlock/serialization and prove at most three whole attempts where contracted,
new transaction/fresh reads each time; permanent errors are not retried.

Cross-expiry evidence follows Addendum A22: record database-derived
tx_started_at, expiry_at, lock_wait_started_at, lock_acquired_at and
authorization_checked_at. Prove transaction/wait start < expiry,
lock_acquired_at >= expiry, authorization_checked_at > expiry and
authorization_checked_at >= lock_acquired_at, with zero protected effects.
Repeat fresh post-wait clock_timestamp() checks after any second required wait;
now(), caller time and cached authority are not final authorization clocks.

## 10. Architecture tests and proposed test layout

Propose dedicated `tests/integration/phase2/test_pr2_19_*.py` modules for golden,
failure, replay/atomicity and races; pure candidate/DTO unit tests under existing
Phase 2 unit paths; architecture tests under `tests/architecture/`. Exact files
are future execution-pack choices, not files created by this draft.

All thirteen 05 §49 obligations require executable evidence:

| Required architecture test | Evidence oracle |
| --- | --- |
| test_literature_source_not_evidence | Source creation/freeze alone leaves evidence/support empty. |
| test_search_result_not_evidence | Retrieval completion alone creates no verified evidence. |
| test_citation_not_claim_support | F3 trace and unchanged support relation/hash sets. |
| test_strategy_does_not_import_persistence | Import graph plus candidate execution with zero DB writes. |
| test_adapter_does_not_write_db | Adapter dependency/capability boundary plus zero canonical delta. |
| test_no_storm_specific_core_schema | Catalog/source inventory: no vendor-owned canonical tables/fields. |
| test_no_paperqa_specific_core_schema | Same inventory; corpus/index stays replaceable operational state. |
| test_discussion_not_canonical_science | F4 durable zero-promotion assertions. |
| test_manuscript_not_scientific_source_of_truth | Wording/placement cannot change Claim/conclusion material or canonical numeric facts. |
| test_review_does_not_mutate_target | Review/Issue creation preserves exact target hash/material. |
| test_decision_does_not_mutate_history | PROCEED/replay preserves target/review/history; no implicit Issue resolution. |
| test_approval_does_not_override_invalid_fact | F5 invalidity denial and zero scientific/effect mutation. |
| test_external_call_not_inside_long_db_transaction | Instrument provider boundary and active transaction observations under search's accepted transaction pattern. |

Static naming/import checks alone do not prove behavioral boundaries. Add existing
08 §40 strong-FK, immutable-history, no-scientific-cascade and common-boundary
regressions, and use PostgreSQL catalog/normal-role probes for persistence facts.
CI required cases fail or report BLOCKED on missing prerequisites; they cannot
silently skip to a green PR2-19 gate. Optional live-provider jobs may be separately
reported without weakening deterministic required coverage.

## 11. Dependencies, acceptance and evidence gate

| Dependency | Admission condition |
| --- | --- |
| Phase 1, PR2-00–05 | Accepted identity/access/source/search/evidence contracts and real DB fixtures; unchanged Phase 1 golden/hash vectors. |
| PR2-06–08, optional 09 | Provider-neutral deterministic fixtures, pinned enabled adapters, native strategy/candidate boundaries. Live access is not required for mandatory offline oracle. |
| PR2-10–13 | Discussion and conclusion/placement/trace coverage; separately accepted successful promotion and manuscript freeze needed for full G4/G5. |
| PR2-14/15 and owner-approved RevisionAction base | Exact target review, complete minimal Decision basis, completed-action implementation; Issue disposition/revision-purpose/re-review gaps explicitly tracked. |
| Owner-approved PR2-16 base | Accepted request/decision/grant/lifecycle and writer-coordination implementation; grant consumption and manuscript purposes need separate contracts. |
| PR2-17/18 | Accepted prepared-package/authorship/consent and prior-art/coverage/novelty contracts for G7; never implement them here. |
| PR2-20 | Receives PR2-19 evidence/gaps for hardening/exit reporting. This plan declares no M4, Human Gate or Phase exit success. |

Draft acceptance: exact status, resolved local links, only this proposal changed,
all requested topics covered, base approval provenance explicit and actual
verification results reported. Before freeze: owner resolves §12, independent
spec/diff/evidence review has no open P0 BLOCKER/P1 MAJOR, and every mandatory
row has an approved prerequisite, exact command/error oracle and executable
node-ID mapping. No actor/test runner may self-authorize missing contracts.

Future implementation acceptance: G0–G7 required scope, F1–F9 and all thirteen
architecture obligations pass on real PostgreSQL 18.x where applicable; lint,
format, types, unit/architecture and affected integration/migration regressions
pass; restart/replay, normal-role SQL, commit fault and observed races pass.
Record pass/fail/error/skip/blocked counts separately, server version/identity,
revision, lock/hash/row-count evidence and cleanup proof. An implemented prefix
may be reviewed as a bounded slice only by explicit owner decision; it cannot
claim full PR2-19 or Phase 2 acceptance.

## 12. Open questions for the owner — recommended conservative answers

| Question | Recommended answer and consequence |
| --- | --- |
| Full PR2-19 now or a bounded baseline slice while PR2-15/16 implement? | Freeze the full matrix with dependency blockers; authorize only available tests separately. No full gate until required suffixes exist and pass. |
| How is the supplied 2026-10-14 base approval recorded given current DRAFT banners? | Treat task-supplied approval as base authority; record its exact approved revision in the later execution pack. Do not alter the two base files here or infer implementation acceptance. |
| Who contracts successful discussion/strategy promotion? | Owning promotion PR defines exact candidate-to-DRAFT provenance, authority, validation and replay before G2/G4 positive suffix. Keep current FORBIDDEN as required negative evidence. |
| What completes the blocking-Issue review/revision cycle? | Separate Issue-disposition, revision-purpose Decision and concern carry-forward contracts. RevisionAction alone leaves OPEN; minimal PROCEED is neither dismissal nor reconsideration. |
| Must F1 prove automatic AuditFinding/ImpactAssessment creation? | Require preserved lineage and invalid downstream admission; test automatic creation only when owning approved contract specifies it. Otherwise create assessments through authorized commands and record missing automation separately. |
| Is citation-only presentation illegal or merely unsupported as scientific evidence? | Permit explicit CITATION_ONLY presentation; require the audit/support gate to report unsupported claims. Do not ban all citations lacking Claim-support edges. |
| Which approval tuples and effects are required for full acceptance? | All accepted finite R2 tuples eventually; bounded conclusion request/decision/grant gets its own coverage. Manuscript/consumption suffixes remain blocked until separately contracted. |
| Are live LLM/provider calls required for the deterministic gate? | No. Fixed licensed corpus and doubles gate scientific semantics; enabled pinned adapters retain separate compatibility checks and opt-in live evidence. |
| May failure hooks or corruption setup ship in production? | No caller-accessible hooks/routes. Test-only wrappers on isolated fixtures; privileged corruption clearly separated from normal-role constraint probes. |
| Can missing DB/prerequisites count as expected failure or SKIP success? | No. Record BLOCKED/setup ERROR and prohibit full gate success; optional live-adapter skips are separately scoped and counted. |
| Are new schema/dependencies or deferred-path fixes allowed in PR2-19? | No by default. Return defects to the owning authorized PR; any material architecture deviation needs ADR/review before implementation. |

## 13. Documentation-task verification

Executed 2026-10-13 against HEAD
`4d19c36b851af824c4dea5c5cd18b270e603e0b4`. These are documentation/baseline
checks, not execution of the proposed future matrix. Only this draft is added to
the tracked-file change set. Scratch/cache/logs remain in ignored
`tmp/pr2-19-verification/`; no commit, push or branch was created.

The local `.venv` initially lacked pytest. The first two invocations of
`uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync pytest
-o addopts='' -ra --tb=short tests/unit tests/architecture` exited 2 before
collection: **0 tests executed**, `Failed to spawn: pytest`. The first
`uv --cache-dir tmp/pr2-19-verification/uv-cache sync --offline --locked`
exited 1 because the empty scratch cache lacked the locked Ruff wheel. Recovery
used the existing local uv cache without network or dependency-file changes:

```bash
mkdir -p tmp/pr2-19-verification
cp -R /Users/fengwang/.cache/uv/. tmp/pr2-19-verification/uv-cache/
uv --cache-dir tmp/pr2-19-verification/uv-cache sync --offline --locked
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short tests/unit tests/architecture
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync ruff check .
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync ruff format --check .
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync pyright
```

Locked sync exited 0 and installed 34 packages. Pytest exited 1: **1820 passed,
5 failed, 0 skipped, 2 warnings** in 33.10s. Four failures in
`tests/unit/test_hg1_runner.py` occur at Unix socket bind with
`PermissionError: [Errno 1] Operation not permitted`. The fifth,
`test_candidate_static_gates_and_inherited_formatter_delta`, fails the pinned
baseline diff check because existing `docs/verification/task9/pyright.txt:4`
has a new blank line at EOF relative to baseline
`b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff`. Neither failure source was changed
or suppressed. Ruff lint exited 0, **All checks passed**; format exited 0,
**456 files already formatted**; Pyright exited 0, **0 errors, 0 warnings,
0 informations**. These tools do not verify Markdown semantics.

PostgreSQL checks and initialization attempt:

```bash
pg_isready -h 127.0.0.1 -p 5432
pg_isready -h 127.0.0.1 -p 55440
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/pr2-19-verification/pgdata -U pr219_admin -A trust --no-locale
```

Both readiness commands exited 2, **no response**. initdb exited 1 at `shmget`:
**could not create shared memory segment: Operation not permitted**, then removed
its incomplete cluster. No test server could start. The following exact suite
selection was executed first with only RB_TEST_ADMIN_URL; it exited 1 with
**111 setup errors**, including missing DATABASE_URL in the older shared fixture.
It was rerun with both selectors to remove that configuration error:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://pr219_admin@127.0.0.1:55479/postgres \
DATABASE_URL=postgresql+psycopg://pr219_admin@127.0.0.1:55479/postgres \
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short \
  tests/integration/phase2/test_pr2_02_source_version_migration.py \
  tests/integration/phase2/test_pr2_10_discussion_persistence.py \
  tests/integration/phase2/test_pr2_11_r2_persistence.py \
  tests/integration/phase2/test_pr2_13_scientific_trace.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_14_conclusion_review.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py
```

Rerun exited 1: **0 passed, 0 failed assertions, 111 setup errors, 0 skipped**
in 9.90s. PostgreSQL connection attempts failed with **Operation not permitted**.
**BLOCKED, not PASS:** no integration or migration assertion completed. The
first integration run took 9.47s. Approval escalation is unavailable here;
rerun this selection on a permitted disposable PostgreSQL 18.x host for actual
baseline integration evidence. Other scientific integration suites were not run:
this non-authoritative document changes no executable/schema/frozen contract.
The future full acceptance matrix remains NOT RUN and requires broader real-DB
coverage under separate implementation authorization.

Documentation verification uses this exact command, rerun after final edits:

```bash
uv --cache-dir tmp/pr2-19-verification/uv-cache run --offline --no-sync python - <<'PY'
from pathlib import Path
import re
import subprocess
p = Path('docs/proposals/PR2-19_E2E_Failure_Injection_Plan_DRAFT.md')
s = p.read_text()
links = re.findall(r'\]\(([^)]+)\)', s)
assert all((p.parent / target).is_file() for target in links)
assert '**Status: DRAFT — awaiting owner approval; not authorized for implementation**' in s
assert subprocess.check_output(['git', 'status', '--short'], text=True).splitlines() == [f'?? {p.as_posix()}']
assert all(line == line.rstrip() for line in s.splitlines())
assert len(re.findall(r'^```', s, re.M)) % 2 == 0
required = ['Purpose', 'Scope', 'Invariants', 'Commands, DTOs', 'Schema proposal', 'Error expectations', 'Concurrency', 'Architecture tests', 'Dependencies, acceptance', 'Open questions']
assert all(term in s for term in required)
architecture = Path('docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md').read_text().split('# 49. Architecture Tests')[1].split('# 50.')[0]
names = re.findall(r'^test_\w+', architecture, re.M)
assert len(names) == 13 and all(name in s for name in names)
assert all(token in s for token in ['G1 /', 'G2 /', 'G3 /', 'G4 /', 'G5 /', 'G6 /', 'F1 /', 'F2 /', 'F3 /', 'F4 /', 'F5 /'])
print(f'8 checks passed: {len(links)} local links; exact status; sole draft change; whitespace; fences; topic coverage; 13 architecture obligations; six golden/five failure families')
PY
git diff --check
```

Result: **8 checks passed, 22 local links resolve**; git diff whitespace check
exited 0. Explicit content checks cover this untracked draft, which ordinary
git diff does not include. Manual review checked authority/dependency separation,
schema restraint and expected durable outcomes; it is not independent review,
owner approval or a future PR2-19 gate PASS.
