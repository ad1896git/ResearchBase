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

Use the pinned mappings and command oracles in §13 and §14.
PR2-19 adds no product error enum or transport mapping. Authenticate and establish
entitlement before protected existence/hash/conflict diagnostics; compare
sanitized bounded public diagnostics, not driver exceptions or SQL strings.

| Codes / standing | Scenario expectation |
| --- | --- |
| Existing AUTHENTICATION_REQUIRED, FORBIDDEN, CONFLICT_OF_INTEREST | Missing principal, project/read/write/temporal authority and actor independence; current discussion promotion uses FORBIDDEN. |
| Existing VALIDATION_ERROR, NOT_FOUND, SOURCE_VERSION_NOT_FOUND | Closed DTO errors and authorized absence at the actual owning boundary; do not homogenize source-specific absence codes. |
| Existing FROZEN_REFERENCE_REQUIRED, VERSION_NOT_FROZEN, REVIEW_TARGET_NOT_FROZEN, SOURCE_VERSION_NOT_FREEZABLE, INVALID_SOURCE_VERSION_LINEAGE | Owning frozen-state/lineage checks; expected code depends on tested command. |
| Existing PROVENANCE_CLOSURE_VIOLATION, REFERENTIAL_INTEGRITY_ERROR, IMMUTABLE_RECORD, SOURCE_VERSION_IMMUTABLE | Corrupt or unresolved closure, strong-reference or immutable-write attempts. HASH_MISMATCH in design text is not an implemented ErrorCode member here. |
| Existing IDEMPOTENCY_CONFLICT, CONCURRENT_MODIFICATION, INVALID_STATE_TRANSITION | Changed replay, bounded concurrency exhaustion and unavailable lifecycle transition. No automatic retry of permanent denial. |
| Design/base APPROVAL_GATE_FAILED, DECISION_BASIS_INVALID, APPROVAL_TARGET_STALE, APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, REJECTION_RECONSIDERATION_REQUIRED, GRANT_INVALID, GRANT_STALE | Use the proposed mappings in §13; activation belongs to PR2-16/effect contracts. These are not implemented ErrorCode members in this baseline. |

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

Use the exact baseline lock orders in §14. They describe existing commands,
not new locks added by tests. Future approval, revision and consuming commands
are outside this slice. Their own contracts must supply compatible writer and
lock inventories before their blocked cases can be activated. A missing
participant is a P1 finding in its owning PR.

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
Phase 2 unit paths; architecture tests under `tests/architecture/`. Exact files and cases are pinned in §14; this documentation change creates none.

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
verification results reported. Before implementation: owner approves or overrules the §13 decisions, independent
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

## 12. Glossary

Definitions apply from the first occurrence above. Document numbers refer to
§1's authority table unless a path is supplied here.

| Shorthand | Meaning and governing document |
| --- | --- |
| R2 | Second Phase 2 remediation package: gap, hash, identity and governance contracts 14–17; Addendum 02 A18. |
| R3 | Targeted remediation refining R2; Architecture 18 and Addendum 02 A19. |
| R4 | Temporal authorization remediation refining R3; Architecture 19 and Addendum 02 A20. |
| A-numbers | Sections of Correction Addendum 02, not test identifiers. |
| A2 | Execution naming: LiteratureSearchExecution differs from AgentExecution; Addendum 02. |
| A3 | Formal targets require concrete references; Addendum 02. |
| A4 | Strong canonical reference versus operational locator; Addendum 02. |
| A5 | Minimal Phase 2 identity and authorization; Addendum 02. |
| A10 | Canonical ID collections use relation tables; Addendum 02. |
| A17 | Initial Phase 2 gap closure; Addendum 02. |
| A18 | Normative R2 package precedence; Addendum 02. |
| A19 | Normative R3 package precedence; Addendum 02. |
| A20 | R4 expiry and receipt replay precedence; Addendum 02. |
| A21 | Completed receipt replay requires current read entitlement; Addendum 02. |
| A22 | Legacy preflight and observable cross-expiry proof; Addendum 02. |
| A23 | Bounded minimal DecisionRecord command; Addendum 02 and Architecture 20. |
| TEMP-AUTH-01 | Lock, reread, then fresh trusted time and authorization before effect; Architecture 19 §1. |
| TEMP-AUTH-EVIDENCE-01 | Five database timestamps prove actual wait across expiry; Addendum 02 A22. |
| R-ref | Typed exact hash reference `{type,id,content_hash}`; Hash R2 15 common rules. |
| I-ref | Typed identity reference `{type,id}` without hash (including Run in revision payloads); Hash R2 15 common rules. |
| sealed set | Complete immutable relation set fixed at seal/freeze, not a mutable list; System 01 §§8, 12 and Hash R2 15. |
| frozen closure | Every material dependency resolves to an exact immutable version/record; System 01 §12. |
| basis | Complete saved typed review/target references underlying a Decision; Architecture 20 §§3–6. |
| exact replay | Same scoped UUID and normalized caller material returns saved result under current read entitlement; Architecture 20 §6 and Addendum 02 A21. |
| UUID | Universally unique identifier; canonical identity representation, System 01 foundation/serialization rules. |
| ID | Canonical identifier of an entity/version/record; Registry 03. |
| SHA-256 | Content digest algorithm; Hash R2 15. |
| CAS | Content-addressed artifact storage; Addendum 02 A6. |
| FK / XOR | Foreign key / exactly one allowed concrete target; Registry 03 and Correction 12. |
| DB / SQL / DDL | Database / Structured Query Language / Data Definition Language; System 01 persistence rules. |
| ORM | Object-relational mapper, confined to persistence adapters; System 01 layering rules. |
| UoW | Unit of Work: transaction boundary behind Application ports; System 01 transaction rules. |
| API / HTTP / DTO | Application programming interface / HTTP transport / typed data transfer object; Cross-Phase 08 API contracts. |
| CLI | Command-line interface sharing the Application boundary; Cross-Phase 08. |
| E2E | End-to-end scenario across owning services and durable readback; Phase 2 Specification 05 §42. |
| G0–G7 | This draft's golden rows; G1–G6 correspond to Specification 05 §42; G0 to Cross-Phase 08 §41. |
| F1–F9, b/c suffixes | This draft's failure rows/subcases; F1–F5 derive from Specification 05 §43. |
| RAG | Retrieval-augmented generation; candidate output only, Specification 05 PR2-07. |
| LLM | Large language model; output is candidate state, System 01/Harness 09. |
| DOI | Digital object identifier, external source identity rather than evidence; Registry 03 literature rules. |
| STORM / Co-STORM | Research-method references for replaceable native strategies; Harness 09 §10. |
| PaperQA / PaperQA2 | Optional replaceable scientific-RAG adapter; Specification 05 PR2-07/09. |
| HUMAN / Agent / OWNER | Canonical actor class / caller class / project role; Identity R2 16. OWNER is not independent approval. |
| PROCEED / INTERNAL_SCIENTIFIC_RELEASE | Only shipped Decision value/purpose in the minimal command; Architecture 20 §2. |
| OPEN / BLOCKING | Initial Issue state / severity defining a blocker; Architecture 20 §4. |
| DRAFT / FROZEN / SUPERSEDED | Version lifecycle states; System 01 and each owning contract. SUPERSEDED does not erase history. |
| STALE / INVALID / VALID | Derived current validity, separate from immutable content; System 01 §19 and Correction 12. |
| VERIFIED | Evidence-review status reached only through authorized independent verification; Specification 05 literature rules. |
| CITATION_ONLY / PLACEMENT_ONLY | Presentation trace semantics, not scientific support; Correction 12 and PR2-13 placement services. |
| READY | Manuscript lifecycle state requiring its own transition contract; Governance R2 17. |
| NO_CHANGE | Deferred revision result with no scientific replacement; PR2-15 base. |
| APPROVE / REJECT | Approval decision values; Governance R2 17, distinct from review recommendations. |
| RESTRICT / SHARE / FOR UPDATE | PostgreSQL delete restriction / table lock / row lock modes; System 01 DB rules and Architecture 20 §5. |
| UTC / NFC / UTF-8 | Coordinated Universal Time / Unicode canonical composition / UTF-8 text encoding; Hash R2 15 and temporal R4 19. |
| Path | Python pathlib filesystem path, test report DTO only; this draft §13 under Harness 09 evidence rules. |
| PID / SSI | PostgreSQL backend process ID / Serializable Snapshot Isolation; transaction evidence under Architecture 20 §5. |
| CI | Continuous integration; engineering verification, Harness 09 §§18–19. |
| ADR | Architecture Decision Record; deviations require review under AGENTS.md §11. |
| PR / PR2-nn | Pull request / Phase 2 work package; Specification 05 implementation sequence. |
| TDG2 / M4 / Human Gate | Phase 2 technology decision / final milestone / owner acceptance gates; Specification 05 and Technology Gate 11. |
| P0/P1/P2/P3 | BLOCKER/MAJOR/MINOR/SUGGESTION review severity; AGENTS.md §10. |
| PASS / BLOCKED / ERROR / SKIP | Passed assertions / absent prerequisite / setup or execution error / explicit optional omission; Harness 09 §19. None are interchangeable. |
| node-ID | Pytest module plus test name (and parameter ID); this draft §14 evidence convention under Harness 09 §19. |

## 13. Decisions taken in this draft

Every recommended answer from the former open-question table is adopted below.
The owner may overrule a draft decision. Until then these are the build defaults,
not choices delegated to the implementing engineer.

| Decision topic | Adopted decision and consequence |
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

### Error and replay decisions

The table below is the single transport mapping inventory for this plan. Existing
values are copied from [HTTP errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py). Review mappings remain
provisional in their source; this draft preserves them. Proposed values do not
add ErrorCode members and cannot be used as an implemented oracle.

| Error code | HTTP status | CLI exit | Standing |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Existing |
| NOT_FOUND | 404 | 3 | Existing |
| AUTHENTICATION_REQUIRED | 401 | 3 | Existing |
| FORBIDDEN | 403 | 3 | Existing |
| REVIEW_TARGET_NOT_FROZEN | 409 | 4 | Existing |
| CONFLICT_OF_INTEREST | 403 | 3 | Existing |
| SUBJECT_BINDING_UNPROVEN | 403 | 3 | Existing |
| INVALID_STATE_TRANSITION | 409 | 4 | Existing |
| VERSION_NOT_FROZEN | 409 | 4 | Existing |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Existing |
| IMMUTABLE_RECORD | 409 | 4 | Existing |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing |
| DUPLICATE_CONTENT | 409 | 4 | Existing |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Existing |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Existing |
| SUBJECT_ALREADY_BOUND | 409 | 4 | Existing |
| OWNER_COVERAGE_GAP | 409 | 4 | Existing |
| OWNER_CREDENTIAL_UNAVAILABLE | 409 | 4 | Existing |
| ENROLLMENT_CHALLENGE_EXPIRED | 409 | 4 | Existing |
| BOOTSTRAP_CLOSED | 409 | 4 | Existing |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Existing |
| LEGACY_STATE_INVALID | 409 | 4 | Existing |
| IDENTIFIER_INVALID | 422 | 2 | Existing |
| SOURCE_IDENTITY_CONFLICT | 409 | 4 | Existing |
| IDENTIFIER_ALREADY_BOUND | 409 | 4 | Existing |
| IDENTIFIER_BASIS_NOT_FROZEN | 409 | 4 | Existing |
| SOURCE_NOT_FOUND | 404 | 3 | Existing |
| SHARED_SOURCE_REJECTION_REQUIRES_REVIEW | 409 | 4 | Existing |
| SOURCE_MERGE_PROPOSAL_NOT_FOUND | 404 | 3 | Existing |
| SOURCE_MERGE_PROPOSAL_STALE | 409 | 4 | Existing |
| SOURCE_MERGE_APPROVAL_MISSING | 409 | 4 | Existing |
| SOURCE_MERGE_APPROVAL_FORBIDDEN | 403 | 3 | Existing |
| SOURCE_MERGE_REJECTED | 409 | 4 | Existing |
| SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED | 409 | 4 | Existing |
| SOURCE_MERGE_BASIS_CONFLICT | 409 | 4 | Existing |
| SOURCE_NOT_MERGEABLE | 409 | 4 | Existing |
| SOURCE_MERGE_IDENTIFIER_CONFLICT | 409 | 4 | Existing |
| SOURCE_VERSION_NOT_FOUND | 404 | 3 | Existing |
| SOURCE_VERSION_NOT_FREEZABLE | 409 | 4 | Existing |
| SOURCE_VERSION_ALREADY_FROZEN | 409 | 4 | Existing |
| SOURCE_VERSION_IMMUTABLE | 409 | 4 | Existing |
| INVALID_SOURCE_VERSION_LINEAGE | 409 | 4 | Existing |
| SEARCH_PLAN_QUESTION_REQUIRED | 422 | 2 | Existing |
| SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED | 422 | 2 | Existing |
| SEARCH_PLAN_QUESTION_INVALID | 422 | 2 | Existing |
| SEARCH_PLAN_QUESTION_SCOPE_MISMATCH | 403 | 3 | Existing |
| SEARCH_PLAN_VERSION_IMMUTABLE | 409 | 4 | Existing |
| SEARCH_PLAN_NOT_FROZEN | 409 | 4 | Existing |
| ADAPTER_UNAVAILABLE | 503 | 5 | Existing |
| ADAPTER_VERSION_MISMATCH | 409 | 4 | Existing |
| HASH_MISMATCH | 409 | 5 | Proposed; owning contract must adopt |
| APPROVAL_GATE_FAILED | 409 | 4 | Proposed; owning contract must adopt |
| DECISION_BASIS_INVALID | 409 | 5 | Proposed; owning contract must adopt |
| APPROVAL_TARGET_STALE | 409 | 4 | Proposed; owning contract must adopt |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 422 | 2 | Proposed; owning contract must adopt |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Proposed; owning contract must adopt |
| GRANT_INVALID | 409 | 4 | Proposed; owning contract must adopt |
| GRANT_STALE | 409 | 4 | Proposed; owning contract must adopt |

For runnable cases: discussion promotion → FORBIDDEN; changed Decision material
or second initial Decision scope → IDEMPOTENCY_CONFLICT; current invalid
Decision closure or OPEN/BLOCKING Issue → PROVENANCE_CLOSURE_VIOLATION;
non-frozen conclusion review → REVIEW_TARGET_NOT_FROZEN; reviewer/decider author
equality → CONFLICT_OF_INTEREST. Missing principal → AUTHENTICATION_REQUIRED;
current authority loss → FORBIDDEN. Source lineage and artifact-binding faults
use INVALID_SOURCE_VERSION_LINEAGE and FROZEN_REFERENCE_REQUIRED respectively.
Evidence quotation/locator rejection and evidence changed-receipt input use
VALIDATION_ERROR in the current service; do not substitute IDEMPOTENCY_CONFLICT.
Candidate validation raises ValueError, not a product ErrorCode. Raw PostgreSQL
constraint probes assert SQLSTATE and rollback, not an invented HTTP response.

Same UUID replay keeps the saved basis and result. New UUID is never a recovery
policy. Decision retries at most three whole transactions on normalized
CONCURRENT_MODIFICATION; permanent denials are not retried. Discussion and
source commands retain their existing three-attempt serializable retry. Tests
must distinguish an aborted transaction from a committed-but-lost response.
PR2-14 review replay remains its existing current-target-validity behavior;
this draft does not grant it the Decision's stale-target historical replay rule.

### Closed test DTOs, limits and enums

Create frozen, slotted dataclasses in the test helper named in §14. These are
report DTOs only. Do not create product DTOs or a generic command interpreter.
Each scenario is a named Python test calling typed owning commands directly.

| DTO | Exact fields and Python types |
| --- | --- |
| ScenarioSpec | `scenario_id: str`, `authority_clause: str`, `prerequisite_contracts: tuple[str, ...]`, `actor_ids: tuple[UUID, ...]`, `fixture_case: str`, `command_steps: tuple[str, ...]`, `fault_point: str`, `expected_outcome: str`, `expected_error_code: str \| None` |
| ScenarioObservation | `scenario_id: str`, `step_index: int`, `command_identity: str`, `result_ids: tuple[UUID, ...]`, `error_code: str \| None`, `state_deltas: tuple[StateDelta, ...]`, `verified_hashes: tuple[VerifiedHash, ...]`, `backend_pids: tuple[int, ...]`, `lock_events: tuple[LockEvent, ...]`, `evidence_paths: tuple[Path, ...]` |
| StateDelta | `table_name: str`, `before_count: int`, `after_count: int` |
| VerifiedHash | `record_id: UUID`, `hash_field: str`, `expected: str`, `actual: str` |
| LockEvent | `backend_pid: int`, `event: str`, `at: datetime`, `blocker_pids: tuple[int, ...]` |
| RecordDecisionCommand (existing) | `id: UUID`, `project_id: UUID`, `scientific_conclusion_version_id: UUID`, `question: str`, `rationale: str`, `decision_type: str = "INTERNAL_SCIENTIFIC_RELEASE"`, `decision: str = "PROCEED"` |
| ClaimInputRequest (existing) | `claim_version_id: UUID`, `relation_type: str`, `literature_support_snapshot_id: UUID \| None = None` |
| LiteratureInputRequest (existing) | `literature_evidence_id: UUID`, `relation_type: str` |
| ReviewIssueRequest (existing) | `severity: str`, `issue_type: str`, `description: str` |

Test DTO string limits: IDs and command labels 128 characters; authority clauses
and prerequisite names 512; diagnostic text 1000. Collections: 32 command steps,
16 actors, 32 prerequisites, 128 result IDs/deltas/hashes/lock events/paths.
Counts and step indices are nonnegative integers; backend PIDs are positive.
Hashes are 64 lowercase hexadecimal characters. All timestamps are timezone-aware
UTC database observations. Evidence paths must remain under the test report
root. Reject unknown fields and invalid values when constructing test DTOs.
These report limits do not truncate or limit canonical review/basis sets.

Pinned test enums: `fault_point` = NONE, AFTER_PARENT_INSERT,
AFTER_RELATION_INSERT, AFTER_EVENT_INSERT, BEFORE_COMMIT, AFTER_COMMIT_RESPONSE,
SERIALIZATION, DEADLOCK. `expected_outcome` = PASS, DENIED, BLOCKED, ERROR.
`event` = TX_STARTED, WAIT_OBSERVED, LOCK_ACQUIRED, AUTH_CHECKED, COMMITTED,
ROLLED_BACK. Scenario IDs are exactly the rows in §14; finite command labels
come from that row's named owning methods. No eval, arbitrary SQL hook or dynamic
import is allowed. Pure candidate DTO failures use a named ValueError assertion;
`expected_error_code` is then None.

Existing Decision text is NFC-normalized nonblank UTF-8, with no current maximum
in its owning `_text`; do not add a product limit here. Review summary and Issue
description are NFC-normalized nonblank UTF-8, at most 16000 characters; initial
Issues are a tuple with at most 100 entries. Review types: SCIENTIFIC, STATISTICAL,
LITERATURE, REPRODUCIBILITY, EDITORIAL, COMPREHENSIVE. Recommendations: ACCEPT,
MINOR_REVISION, MAJOR_REVISION, REJECT, UNCERTAIN. Severities: INFO, MINOR, MAJOR,
BLOCKING. Issue types: UNSUPPORTED_CLAIM, CITATION, STATISTICAL, METHODOLOGICAL,
REPRODUCIBILITY, OVERCLAIM, CONTRADICTION, NOVELTY, WRITING, OTHER. Initial status
is OPEN. Targets shipped by InternalReviewService are CLAIM_VERSION and
SCIENTIFIC_CONCLUSION_VERSION; manuscript/artifact review is outside this slice.

Conclusion claim/literature input collections are tuples, at most 100 each;
relation_type is SUPPORTS, CONTRADICTS or QUALIFIES. Exact hashes and current
validity are resolved by the owning service, never supplied by report DTOs.

Use ScientificRAGRequest and EvidenceCandidate from
[scientific_rag_provider.py](../../src/researchbase/application/scientific_rag_provider.py).
Question is at most 16000 characters; source IDs are a nonempty unique UUID tuple;
max_evidence_candidates is an integer 1–100, default 20; excerpt is nonblank and
at most 4000 characters. Locator page is positive; paragraph is a positive decimal
string; section/figure/table are bounded to 128 characters; quote_span has the
`char:start:end` format and requires a paragraph. Provider/adapter IDs and version
are bounded to 128, model ID to 256, notes to 1000, answer to 16000. There is no
existing source-set maximum; use two sources and at most two candidates in the
deterministic fixture. ResearchStrategyRequest topic is at most 255 characters.
No contribution_role enum is introduced: authorship is blocked under PR2-17.

## 14. Implementation guide

### Exact DDL sketch: empty change set

PR2-19 is test orchestration. Adding tables would violate §5 and AGENTS.md §4.
The following is the complete DDL specification, not a placeholder:

| Table | Column | SQL type | NULL/NOT NULL | Constraint name | Index name |
| --- | --- | --- | --- | --- | --- |
| None added or altered | None | Not applicable | Not applicable | None | None |

```sql
-- PR2-19 migration body: no SQL statements.
-- Do not create an Alembic revision, temporary canonical table or test receipt.
```

Use the existing Alembic head in disposable databases. Catalog probes enumerate
existing FK, RESTRICT, immutable and sealed-set guards; they do not recreate them.
RevisionAction, Approval and package DDL belongs to the contracts listed below.

### Runnable matrix and named fixtures

RUNNABLE NOW means buildable against current code, not already executed or
accepted. A blocked full row cannot be satisfied by its runnable prefix.
Every future module path below starts with `tests/integration/phase2/`, except
G0's explicitly named existing E2E module. Named fixtures are defined below.

| Row | Full-row status | Exact test module and fixture / missing contract |
| --- | --- | --- |
| G0 | RUNNABLE NOW | Existing `tests/e2e/test_phase1_golden_scientific_workflow.py`; `fresh_fixture`, `run_workflow`, `projection` from `tests/e2e/support.py`. |
| G1 | BLOCKED BY search-result-to-SourceVersion resolution admission | `test_pr2_19_search_evidence.py`; `pr219_evidence_env` + PR2-04 execution fixtures. Independent search and source/evidence prefixes are runnable; no persisted resolution bridge is supplied by this draft. |
| G2 | BLOCKED BY successful strategy candidate-to-question/hypothesis DRAFT promotion | `test_pr2_19_candidates.py`; `pr219_candidate_env`. Native candidate prefix runnable. |
| G3 | RUNNABLE NOW | `test_pr2_19_rag_evidence.py`; `pr219_evidence_env`, `pr219_candidate_env`. Offline ScientificRAG double → exact source/quotation checks → evidence create/review. Optional live PaperQA is not a prerequisite. |
| G4 | BLOCKED BY successful discussion-to-HypothesisVersion DRAFT promotion | `test_pr2_19_discussion.py`; `pr219_discussion_env`; negative prefix F4 is runnable. |
| G5 | BLOCKED BY manuscript freeze command | `test_pr2_19_citation_trace.py`; `pr219_trace_env`; draft/placements/trace prefix runnable. |
| G6 | BLOCKED BY completed RevisionAction, Issue disposition, revision-purpose Decision, concern carry-forward, manuscript review and Basic Approval | `test_pr2_19_governance.py`; `pr219_decision_env`; no-blocker review → minimal PROCEED prefix runnable, request/grant suffix blocked. |
| G7 | BLOCKED BY PR2-17 package/authorship/consent and PR2-18 coverage/prior-art/novelty contracts | `test_pr2_19_dependencies.py`; no synthetic READY/package/novelty fixtures. |
| F1 | BLOCKED BY manuscript current-validity/audit projection and Basic Approval | `test_pr2_19_lineage.py`; `pr219_evidence_env`, `pr219_trace_env`; source/direct-literature/snapshot/conclusion prefix runnable; no automatic audit creation claim. |
| F1b | RUNNABLE NOW | `test_pr2_19_lineage.py`; `pr219_evidence_env`; missing/wrong-source/unfrozen predecessor, bad correction basis and concurrent corrections. |
| F2 | RUNNABLE NOW | `test_pr2_19_candidates.py`; `pr219_candidate_env`, `pr219_evidence_env`; invented/out-of-corpus IDs, absent paragraph and substituted quotation, valid control and zero canonical delta. |
| F2b | BLOCKED BY contracted defensive read of unresolved formal FK under privileged corruption | `test_pr2_19_integrity.py`; `pr219_evidence_env`, `pr219_decision_env`; missing/corrupt CAS and saved Decision hash corruption prefixes runnable. Normal-role FK rejection is runnable separately. |
| F3 | RUNNABLE NOW | `test_pr2_19_citation_trace.py`; `pr219_trace_env`; CITATION_ONLY and unchanged support hashes. Automatic unsupported-assertion audit remains outside this row until contracted. |
| F4 | RUNNABLE NOW | `test_pr2_19_discussion.py`; `pr219_discussion_env`; Human/Agent instruction content, close/bind, current FORBIDDEN and zero scientific writes. Future positive promotion excluded. |
| F5 | BLOCKED BY Basic Approval and manuscript READY transition/review | `test_pr2_19_governance.py`; `pr219_decision_env`; minimal Decision blocker/unknown-field prefix runnable. |
| F5b | BLOCKED BY Basic Approval independence, stale-target and purpose tuple gates | `test_pr2_19_governance.py`; `pr219_decision_env`; existing Decision authority/closure prefix runnable. |
| F5c | BLOCKED BY Basic Approval project/purpose rejection fence and reconsideration contract | `test_pr2_19_governance.py`; no fabricated rejection receipt fixture. |
| F6 | BLOCKED BY completed RevisionAction seven-result-shape contract and implementation | `test_pr2_19_revision.py`; no synthetic action/result fixtures; NO_CHANGE also requires revision-purpose Decision. |
| F7 | BLOCKED BY Basic Approval atomic decision/grant/event command | `test_pr2_19_atomicity.py`; `pr219_decision_env`, `pr219_discussion_env`; existing parent/relation/event and Decision basis rollback prefix runnable. |
| F8 | RUNNABLE NOW | `test_pr2_19_replay.py`; `pr219_decision_env`, `pr219_discussion_env`; exact replay, changed material, concurrent UUID, restart, lost response and bounded aborted retry. This row covers existing commands only. |
| F9 | BLOCKED BY grant consumption command, atomic result/receipt and current-read replay contract | `test_pr2_19_grant_consumption.py`; no grant fabrication. |

Create fixture wrappers in `tests/integration/phase2/pr2_19_support.py`, following
PR2-14/15's helper/fixture reuse layout. Register wrapper fixtures in each new
module by explicit imports; reuse the existing Phase 2 conftest. Paths here name
future files and are deliberately not Markdown links to nonexistent files.

- `pr219_evidence_env`: wrap `m3` from `test_m3_evidence.py`; upgrade its isolated
  DB to head before commands; reuse TechnicalCredentials and tmp_path CAS.
- `pr219_candidate_env`: fixed two-source corpus from pr219_evidence_env, offline
  ScientificRAGCapability double and native strategy; use provider shapes from
  `tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py` and
  `test_pr2_08_native_strategy.py`. No DB-writing provider fake.
- `pr219_decision_env`: reuse `decision_env`, `_command`, `_review` from
  `test_pr2_15_decision.py` and its `normal_sql_role` fixture for adversarial SQL.
- `pr219_trace_env`: reuse `conclusion_env`, `phase2_database_url` and `_draft`
  as imported by `test_pr2_13_scientific_trace.py`; build citations through owning
  services, never synthetic frozen manuscript rows.
- `pr219_discussion_env`: reuse `discussion_env` from
  `test_pr2_10_discussion_persistence.py`; retain its server-identity preflight.

All wrapper DBs are fixture-owned disposable PostgreSQL 18.x databases. Retain
identity checks before CREATE and finally cleanup. Do not mix fixtures backed by
different databases into one scenario. For a shared chain, derive services from
one wrapper's factory/credentials/engine and create additional actors through
that fixture's accepted test setup. Preserve separate author, verifier, reviewer
and independent decider; later HUMAN approver cannot be fabricated by the test.

### Ordered build steps and test cases

1. Build `pr2_19_support.py`: the §13 records, count/hash observations, fixed corpus,
   fresh-connection readback and barrier helpers. Reuse
   `_wait_for_pg_blocker` from `test_pr2_14_internal_review.py`. Helpers may wrap
   UoW/repository calls for finite fault injection; no changes to production.
2. Create `tests/unit/phase2/test_pr2_19_report_contract.py`: every DTO field/type,
   unknown field, limit edge, enum, path confinement and aware timestamp case.
   This is a new report contract, not duplicate tests of existing DTO constructors.
3. Create runnable candidate and RAG modules: G3/F2 cases from the matrix, plus
   independently verified quotation bytes, independent HUMAN review, restart,
   no evidence on source creation/retrieval alone and no provider DB access.
4. Create lineage, integrity and citation modules for the runnable prefixes/F1b/F3:
   both direct-literature and Claim snapshot paths, correction/retraction preserves
   old bytes, invalid new admission, normal-role FK/immutability rejection,
   CAS failures, CITATION_ONLY and separate experiment/literature trace paths.
5. Create discussion module: F4 valid control, Human/Agent malicious turn content,
   transcript binding, restart, zero new canonical scientific rows and FORBIDDEN.
6. Create governance module for the minimal Decision prefix: complete ACCEPT/REJECT/
   UNCERTAIN basis, OPEN/BLOCKING denial, unrelated Issue control, author conflict,
   cross-project/no-principal/expired-role denials, unchanged target/history and
   no approval/effect. Test unknown command fields at the closed boundary.
7. Create atomicity and replay modules: finite mid-write faults, pre-commit abort,
   post-commit lost response, concurrent same UUID, changed material, fresh service,
   three-attempt serialization/deadlock exhaustion and no duplicate history.
8. Create `test_pr2_19_races.py`: Decision versus zero-Issue review INSERT and
   BLOCKING Issue INSERT in both orders, upstream impact and authority writers in
   both orders, actual lock observations, fresh complete basis/blocker checks and
   cross-expiry five-timestamp proof. Reuse PR2-15's coordinated normal-role probes.
9. Create `tests/architecture/test_pr2_19_boundaries.py`: all thirteen §10 names.
   Import/catalog checks are static; behavioral cases call the integration
   helpers. Approval-invalid-fact obligation stays BLOCKED. Create
   `test_pr2_19_dependencies.py` to inventory every blocked row/contract and fail
   the full-gate report if any mandatory blocker remains; do not mark them xfail
   or skip to obtain success. Do not create blocked-only test modules until their
   prerequisite is authorized; reserve their exact names in the report.
10. Run unit/architecture and runnable integration modules plus existing Phase 1
    golden, PR2-10–15 regression and affected migration suites. Record exact
    command/node-IDs and counts under `artifacts/pr_evidence/PR2-19/`. Full gate
    fails while any matrix row or architecture obligation remains BLOCKED.

Owning production paths are `src/researchbase/application/internal_review.py`,
`decision.py`, `literature_evidence.py`, `discussion.py`,
`manuscript_placement.py`, `manuscript_scientific_trace.py`;
ports are `src/researchbase/application/ports.py`, persistence is
`src/researchbase/persistence/internal_review_repository.py`,
`decision_repository.py`, `publication_repository.py`, `uow.py`.
Follow this separation in test composition. Do not create a PR2-19 Application
service, persistence adapter, route or CLI command. Return production defects
to the owning authorized PR instead of fixing them in the test slice.

### Exact lock orders for exercised commands

These are baseline observation oracles. All locks last until commit/rollback.
`P` below means `rb_phase2_lock_project(project_id)` then `projects FOR UPDATE`.
`A` means the existing authorization query locks actors, membership, role and
subject binding rows (`FOR UPDATE OF a,m,r,b`, ordered by those IDs in the search
plan repository), followed by fresh `clock_timestamp()` credential/role checks.
The source-version repository retains its own authorization selection order.
P and A are defined here only as abbreviations, not new lock primitives.

| Command | Exact acquisition order |
| --- | --- |
| DecisionService.record_decision, including replay | Set local lock_timeout=10s, statement_timeout=30s → advisory `pr215:decision:{id}` → exact conclusion version FOR UPDATE → the sorted SHARE table list below → P → A → eligible reviews ORDER BY id FOR SHARE → Issue reads/basis writes → fresh A before commit. Replay verifies saved basis instead of selecting a new basis. |
| InternalReviewService.create, conclusion target | Advisory `pr214:review:{derived_id}` → exact conclusion version FOR UPDATE → scientific_conclusions parent FOR UPDATE → P → A → target closure/read → fresh A after possible waits → review INSERT/initial Issue INSERT → commit. Derived id is the existing uuid5 scoped request identity. |
| InternalReviewService.create, Claim target | P → A → advisory `pr214:review:{derived_id}` → P → A → literature_evidence.target Claim lookup/closure → fresh A → review/Issue writes. Do not apply the conclusion order to Claim reviews. |
| Normal-role conclusion Review INSERT | 0041 trigger: exact conclusion version FOR UPDATE before validating/writing review; parent/closure guards follow; never begin with target FOR SHARE and upgrade. |
| Normal-role conclusion Issue INSERT | Resolve immutable review's target → exact conclusion version FOR UPDATE → review row lock/reread → validate binding → Issue write. |
| DiscussionService.create | Begin serializable → P → A → scoped CREATE_SESSION advisory receipt lock → validate exact inputs → session/input writes → fresh A → commit. |
| DiscussionService.append / close / bind_transcript | Begin serializable → P → A → scoped APPEND_TURN / CLOSE_SESSION / BIND_TRANSCRIPT advisory receipt lock → discussion session FOR UPDATE → validate/write turn, close or binding → fresh A → commit. |
| DiscussionService.request_promotion | No locks or writes; unconditional FORBIDDEN in this baseline. |
| SourceVersionService.create | Begin serializable → P → scoped CREATE_SOURCE_VERSION advisory receipt lock → literature_sources FOR UPDATE → source authorization row locks → validate frozen artifact/predecessor → draft/receipt writes. |
| SourceVersionService.freeze | Begin serializable → nonlocking version lookup → P → scoped FREEZE_SOURCE_VERSION advisory receipt lock → literature_sources FOR UPDATE → exact source_versions FOR UPDATE → current source version FOR UPDATE where present → source authorization locks → freeze/current-pointer/receipt writes. |
| LiteratureEvidenceService.import_document / create / review / snapshot | Begin serializable → P → A → scoped source-version receipt advisory lock → operation locks detailed below → fresh A → receipt → commit. These operations rely on SSI; do not add row locks to test doubles. |
| ScientificConclusionService.create / revise | Begin serializable → P → A → scoped CREATE_CONCLUSION / REVISE_CONCLUSION receipt advisory lock → Claim parent/version FOR UPDATE in input order, snapshot evidence FOR UPDATE in saved edge order → direct literature_evidence FOR UPDATE in input order → new parent INSERT for create, existing scientific_conclusions parent FOR UPDATE for revise → version/input writes and readback → fresh A → receipt/commit. |
| ScientificConclusionService.freeze | Begin serializable → P → A → scoped FREEZE_CONCLUSION receipt advisory lock → scientific_conclusions parent FOR UPDATE → exact conclusion version FOR UPDATE → Claim and evidence closure locks in saved input/edge order → seal/current-pointer writes → fresh A → receipt/commit. |
| PublicationService.create_publication | P → A → advisory `pr212:publication:{derived_id}` → parent/initial event insert or replay read → commit. |
| PublicationService.create_draft | P → A → advisory `pr212:draft:{derived_id}` → publications parent FOR UPDATE → document/version validation reads → draft INSERT or replay read → commit. |
| ClaimPlacementService.add / ArtifactPlacementService.add | P → A → publications parent FOR UPDATE → manuscript and exact target reads → advisory `pr213:claim-placement:{derived_id}` / `pr213:artifact-placement:{derived_id}` → placement read/insert → commit. |
| CitationPlacementService.add | P → A → publications parent FOR UPDATE → manuscript/source validation reads → advisory `pr213:citation:{derived_id}` → citation read/insert → commit. |

Decision SHARE table list in exact lexicographic order:
`actor_subject_bindings`, `actors`, `artifact_versions`, `artifacts`,
`audit_findings`, `claim_versions`, `claims`, `correction_records`, `datasets`,
`experiment_spec_versions`, `experiment_specs`, `impact_assessments`,
`impact_targets`, `literature_evidence`, `literature_evidence_review_events`,
`literature_source_project_links`, `literature_sources`, `metric_definition_versions`,
`metric_definitions`, `project_membership_events`, `project_memberships`,
`project_role_assignments`, `projects`, `runs`, `scientific_conclusions`,
`source_versions`. See
[Decision repository](../../src/researchbase/persistence/decision_repository.py)
and [review repository](../../src/researchbase/persistence/internal_review_repository.py).
Literature operation locks after the receipt lock: import_document writes new
artifact/version rows; create reads source/artifact then locks its newly inserted
literature_evidence row FOR UPDATE during readback; review locks the existing
evidence row FOR UPDATE before events; snapshot locks target parent and version
`FOR UPDATE OF p,v`, then each evidence row FOR UPDATE in caller input order.
Conclusion/Decision closure validation can also lock literature_evidence rows
FOR UPDATE while checking saved snapshots, in persisted input/edge order. Include
these actual waits in race observations and repeat fresh authorization afterward.
Claim review target lookup likewise takes parent/version FOR UPDATE before
checking evidence closure. No test wrapper may reorder these owning operations.
Readback commands take their owning P → A authorization locks where used;
conclusion and trace readback can then acquire Claim/evidence closure locks in
saved input order. Source read uses its source authorization locks. No replay or
readback may add a mutating step. Phase 1 setup is the unchanged `run_workflow`
sequence; its command-local locking remains governed by Cross-Phase 08 and the
existing Phase 1 tests, not by a new cross-command lock plan. PR2-19 does not
compose commands into one transaction or hold cross-command locks. If a future
contract changes an order, update its race oracle before activating that row.

### Not in this slice

| Missing contract | Blocked artifact/behavior |
| --- | --- |
| Search-result resolution admission | Exact persisted search result → frozen SourceVersion bridge for complete G1; no fabricated resolution relation. |
| Strategy candidate promotion | Explicit question/hypothesis DRAFT admission with validation, authority, provenance and replay; G2 suffix. |
| Discussion candidate promotion | Same owning boundary for discussion-derived HypothesisVersion DRAFT; G4 positive suffix. |
| Manuscript freeze | Frozen material/placements/hash seal and admission command; G5 and package prerequisites. |
| Manuscript READY transition | Readiness predicate, authorization and lifecycle command; F5/G7. |
| Manuscript review | Exact frozen target, current validity and complete review basis; G6/F5. |
| Completed RevisionAction | Seven finite completed-result fields, relevance, predecessor/supersession, replay and shared lock order; G6/F6. |
| Issue disposition | Authority/basis for transition out of OPEN, immutable disposition history; G6. |
| Revision-purpose Decision | Eligible revision and NO_CHANGE decisions; minimal PROCEED is insufficient; G6/F6. |
| Concern carry-forward | Mapping old concerns to exact new result/re-review targets; G6. |
| Basic Approval | Request/decision/grant commands, tuples, independence, rejection fence, replay, full lock/writer inventory; G6/F5–F7. |
| Reconsideration | Explicit evidence permitting request after project/purpose rejection; F5c. |
| READY_FOR_SUBMISSION Decision purpose | Readiness choice cannot be inferred from internal PROCEED; G7. |
| PREPARE_SUBMISSION Decision purpose | Separate preparation choice/basis; G7. |
| Grant consumption | Atomic consuming command/result/receipt with entitlement replay and blocker/expiry races; F9 and package freeze suffix. |
| Manuscript validity/audit projection | Contracted downstream stale/invalid and unsupported-assertion readback; F1 and optional F3 audit. |
| Automatic finding/impact propagation | Only if an owning contract requires automation; no automatic rows inferred from retraction. |
| Defensive unresolved-FK read | Contract for fail-closed read of privileged corrupt closure; F2b suffix. Normal SQL FK denial remains runnable. |
| PR2-17 preparation | Package, contribution/authorship/consent fields/limits/resolver; G7. No consent-to-grant resolver is invented here. |
| PR2-18 novelty | Serializable coverage capture, prior-art relations, INCONCLUSIVE-only first slice and DB guard; G7. |

## 15. Open questions for the owner — override only

There are no unresolved engineering choices in the runnable slice. The owner may
overrule any §13 decision or authorize a narrower test slice. Record an override
and its governing contract before changing the affected oracle. Approval of this
draft alone does not authorize implementation or activate blocked contracts.

## 16. Documentation verification note

This documentation change is verified by local-link and format checks only.
No executable, schema or frozen contract changed; integration suites are not affected or claimed PASS.
