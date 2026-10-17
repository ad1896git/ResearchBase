# PR2-15 RevisionAction Command Contract — APPROVED

**Status: APPROVED by owner 2026-10-14 — authorized for implementation**

**Scope:** Owner-authorized Task 13 implementation of the conservative first slice below.
Existing approved architecture retains precedence; this authorization does not
advance a phase or acceptance gate. Historical proposal wording below is retained
for traceability; the decisions in §10 supersede its draft-only restrictions.

## 1. Purpose, authority and current baseline

RevisionAction records an attributable **completed** response to an exact review
issue and/or revision decision, with exact resulting scientific history. It
answers “what change actually resulted, based on which concern or choice?” It
does not answer “is the concern resolved?” or “may this result be released?”

Read this proposal under the following authorities, in their established order:

| Source | Constraint carried into this proposal |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–9, 23, 37 | Deterministic fact precedence, immutable history, frozen provenance, distinct governance semantics and review/revision trace. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A20 and A23 | R2 precedence and bounded schema admission; fresh temporal authorization; minimal Decision scope remains bounded. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 registry | RevisionAction is a governance-owned immutable record, not a Version or workflow entity. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9, 12–18, 24, 38, 41 | Stable command/error semantics, additive migration, concrete exact references, immutable historical reads, common Application boundary and golden regression. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19–22, 41.9, 42.6, PR2-14/15 | Review → Issue → Decision → revision → targeted re-review; old versions are preserved. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§2, 4, 6–7 | Completed-action meaning, typed basis/result, independent Issue disposition and governance separation. |
| [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), shared physical rules; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), RevisionAction payload; [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §4 | Seven concrete result FKs and finite action shapes supersede the older single-result union and older action names. |
| [Minimal Decision Contract 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§1, 4–7 | INTERNAL_SCIENTIFIC_RELEASE/PROCEED supplies no RevisionAction or Issue disposition authority. The blocking-Issue cycle remains open. |

The inspected implementation is narrower than the broad Phase 2 design:

- [InternalReviewService](../../src/researchbase/application/internal_review.py)
  creates immutable reviews and initial OPEN issues for exact frozen ClaimVersion
  and ScientificConclusionVersion targets. It provides no disposition command.
- [0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py) permits
  only initial OPEN Issue/Event history and forbids ordinary Issue mutation.
  [0041](../../migrations/versions/0041_pr2_15_review_coordination.py) coordinates
  conclusion reviews/issues on the exact conclusion row.
- [DecisionService](../../src/researchbase/application/decision.py),
  [decision material](../../src/researchbase/domain/decision.py),
  [repository](../../src/researchbase/persistence/decision_repository.py) and
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) implement only
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED, complete conclusion/review basis, replay
  and no replacement. The repository uses request coordination, target locks
  and a sorted SHARE-table snapshot inventory. There is no revision-purpose
  Decision command or RevisionAction persistence in this baseline.

Older `manuscript_edit`, `claim_revision`, `citation_change` and
`resulting_version_ref` examples in 05/12/13 are not additional action shapes.
The seven R2 shapes and literal R2 payload govern. This proposal does not change
them or reinterpret the existing Decision command.

## 2. Proposed scope and non-goals

Propose one write command, `record_revision_action`, and one authorized exact-ID
query, `read_revision_action`. They record/read completed history only. Initial
issue-driven scope is the existing PR2-14 ClaimVersion and conclusion reviews;
record all seven R2 result shapes only when the required basis, result commands
and relevance checks are available. Unavailable paths fail closed.

Decision-only recording and NO_CHANGE depend on a **separately approved
revision-purpose Decision contract**. They must remain unavailable until that
contract defines its finite purpose/value, exact target/review basis, authority,
independence and rationale rules. This draft does not invent those values or
enable them through PROCEED. Issue-only completed changes need not first obtain
a PROCEED decision; that would reproduce the open blocking-Issue dependency cycle.
The owner must approve this proposed issue-only path explicitly.

Excluded: edit planning/scheduling, performing experiments or edits, creating or
freezing results, automatic re-review, Issue ADDRESSED/DISMISSED/VERIFIED,
Approval/grant/consumption, publication transitions, prepared submission, venue
sending, ExternalEffect, Agent Runtime and new generic governance infrastructure.
Task 13 authorizes the implementation slice selected in §10, including its
forward migration and verification. No broader phase or architecture gate is advanced.

## 3. Domain invariants and revision trace

1. **Completed action only.** Each result must already be durable and frozen or
   terminal before first recording. A proposed edit, queued run, DRAFT version,
   suggestion or model answer is not completed history. Each owning Application
   command retains its own transaction; recording does not retroactively make
   result creation and action recording one distributed transaction.
2. **Immutable record.** No update, delete, unfreeze or version chain. A mistaken
   action is corrected by a new action referencing the predecessor; both remain
   readable. Supersession corrects attribution/trace, not scientific result bytes.
3. **Review != Decision != Approval != Command != ExternalEffect.** An action
   documents completion. It does not evaluate adequacy, authorize another command,
   or claim external delivery. Review recommendations and authoritative choices
   cannot make deterministic scientific errors valid.
4. **Concrete basis.** At least one exact Issue or Decision FK is present. An
   Issue resolves through its immutable ReviewRecord to exact old target ID/hash;
   a Decision resolves through its saved typed basis. If both exist, project and
   exact affected target must agree. Common project, similar text, shared Claim
   or a latest pointer alone cannot establish relevance.
5. **Trace is old-to-new.** The old target comes from the basis; the new result
   comes from concrete result FKs. No extra generic `target_ref`, JSON provenance
   object or duplicate canonical edge. A trace query can reconstruct
   `ReviewRecord → ReviewIssue → RevisionAction → exact result`, optional exact
   Decision basis, and any superseding action. Later re-review is a new review
   of the exact new target, never an edit of the old review.
6. **Completion != resolution.** Recording leaves the Issue OPEN and its events
   unchanged. A future independently contracted transition must validate action,
   result and independent reviewer and append its own IssueEvent. NO_CHANGE may
   support a separately contracted dismissal; it cannot pretend a blocking Issue
   was materially ADDRESSED. No old PROCEED or action clears later blockers.
7. **Attribution and access.** Human and Agent use the same authenticated
   Application boundary. Proposed first-write roles are active same-project OWNER
   or RESEARCHER, with live verified subject/credential and fresh effective role.
   The recorder may be a material author; independent evaluation belongs to
   re-review/disposition, not to an invented HUMAN-only recording requirement.
   `created_by` means the authenticated recorder, not an assertion that this actor
   exclusively authored every result. Role selection is an owner question (§10).
8. **Current validity vs history.** First recording verifies current deterministic
   validity and full exact closure, except a terminal FAILED/CANCELLED Run is valid
   completion history without being positive evidence. An obsolete old target
   does not by itself prohibit documenting its correction. Later invalidity does
   not rewrite the action or permit historical references to move to latest.

### 3.1 Finite result and relevance rules — proposed command refinement

All unlisted result columns must be NULL. Every hashed result's own content hash
and closure are recomputed; Run has exact identity/closure, not an invented hash.

| Persisted `action_type` | Required result columns | Completion and relevance |
| --- | --- | --- |
| `NEW_EXPERIMENT` | `result_experiment_spec_version_id`, `result_run_id` | Exact FROZEN Spec; Run uses that exact Spec, sealed inputs and SUCCEEDED/FAILED/CANCELLED terminal state. Require an existing typed scientific path from the affected target's support/hypothesis/spec to the new experiment; narrative alone is insufficient. |
| `ANALYSIS_CHANGE` | `result_statistical_result_id` | Immutable StatisticalResult with exact Measurement/Run closure; a typed input path connects it to the affected target's scientific support. |
| `CLAIM_CHANGE` | `result_claim_version_id` | FROZEN ClaimVersion with sealed evidence; for a Claim-targeted issue, a distinct successor under the same Claim; for a conclusion target, successor of an exact Claim input in its saved support graph. |
| `CONCLUSION_CHANGE` | `result_scientific_conclusion_version_id` | FROZEN conclusion with R2 closure; distinct successor under the affected conclusion, or exact new conclusion input closure linking the affected Claim/successor. |
| `MANUSCRIPT_CHANGE` | `result_manuscript_version_id` | FROZEN manuscript with placement closure; for current Claim/conclusion issue scope its exact placements bind the affected target or a demonstrable successor. If manuscript review scope is later admitted, require distinct successor under the same Publication. Citation-only edits use this shape, not a new CITATION_CHANGE value. |
| `SOURCE_CHANGE` | `result_source_version_id` | FROZEN SourceVersion, required correction/retraction lineage and basis; same-source successor of an exact SourceVersion in the affected target's literature closure, with project access link. Global source identity alone does not establish relevance. |
| `NO_CHANGE` | none | Exact revision-purpose Decision explicitly accepts this concern without material change and has nonblank rationale. Issue-only NO_CHANGE and existing PROCEED deny. No Issue transition. |

“Successor” means provable ordering under the owning identity's accepted version
contract, with both IDs retained; it does not require a new predecessor column
where none exists. A material change cannot reuse the affected version as its
result. Do not force different domains to share a parent identity. The owner must
approve the finite relevance matrix before implementation; a combination without
an existing deterministic typed path stays unavailable, rather than adding a soft
reference or claiming free text proves causality. Mere relevance does not prove
the result adequately addresses the issue.

## 4. Commands, DTOs and readback

### 4.1 `RecordRevisionActionCommand` — closed immutable input DTO

| Field | Representation and meaning |
| --- | --- |
| `id` | Required UUID; request identity is canonical RevisionAction ID. |
| `project_id` | Required exact Project UUID for admission/access; derived scope must agree with basis and results. Not an additional proposed persisted semantic column. |
| `review_issue_id` | UUID or NULL; exact immutable concern, not all issues for a target. |
| `decision_record_id` | UUID or NULL; only an eligible separately contracted revision-purpose Decision. |
| `action_type` | One of the seven uppercase R2 literals in §3.1. |
| Seven `result_*_id` fields | UUID or NULL, exactly the column names in §3.1 and §5; all present in canonical comparison, null when unused. |
| `supersedes_revision_action_id` | UUID or NULL; completed correction predecessor (§4.3). |

Unknown fields deny. No actor, role, credential, hash, caller time, free-form
results JSON, status, Issue transition, evidence-selection filter, approval or
effect input. There is no new rationale field: NO_CHANGE rationale belongs to its
DecisionRecord. Trusted context supplies `created_by`; fresh trusted DB UTC time
supplies `created_at`, interpreted as the time completion was **recorded**, not
an invented execution time. Actual completion times remain with owning results.

### 4.2 `RevisionActionReadback` and exact-ID query

Return canonical ID, derived project, basis IDs, action type, all seven exact
result IDs, actor/time, predecessor ID, own `content_hash` and `hash_scheme`.
Include verified exact hashes for Decision, ReviewRecord/old target, hashed
results and predecessor in a typed provenance projection. Issue and Run are
identity refs and receive no fabricated own hash. Current result/target validity
and “has superseding action” are explicitly derived read fields, not material
action status. `read_revision_action(project_id, id)` requires current authorized
read entitlement; it does not require original actor impersonation.

### 4.3 UUID replay and corrections

Authenticate and authorize disclosure first. Proposed read roles mirror existing
Decision readers: OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER with active membership,
live verified credential and fresh temporal entitlement. This does not widen
InternalReviewService's existing read policy; expanded nested review disclosure
requires that review's own authorization, otherwise return permitted references.

For command replay, canonical UUID, project, command identity, trusted original
actor, basis IDs, action type, seven result IDs and predecessor must match.
Verify saved literal hash and historical closure without substituting current
refs or rescanning for a new basis. A currently entitled same actor receives the
saved result once, even after write-role loss or later result invalidity.
Different material conflicts; another actor or inaccessible project receives
nondisclosing FORBIDDEN. An unknown/incomplete record requires first-write gates.
No receipt table, persisted request digest or extra scientific hash is proposed.

Propose one nonforking correction chain per action: predecessor must exist, be
same project, retain identical Issue/Decision basis IDs, have no successor, and
have a valid own hash. New record ID differs. The new completed result/action
shape may correct the old one; changing the concern is a separate root action,
not a reparented correction. Unique nonnull predecessor plus predecessor locking
prevents forks; self-reference and cycles deny. Root actions are not globally
unique by Issue: one concern can cause multiple completed changes. There is no
automatic semantic deduplication or mutation of an existing root. The correction
policy requires owner approval and must not enable Decision supersession.

## 5. Persistence and hash contract

Use the already design-admitted `revision_actions` record, not a new top-level
schema. Proposed physical columns are exhaustive:

```text
id UUID PK; created_at TIMESTAMPTZ NOT NULL; created_by UUID NOT NULL
review_issue_id UUID NULL; decision_record_id UUID NULL; action_type VARCHAR(32) NOT NULL
result_experiment_spec_version_id UUID NULL; result_run_id UUID NULL
result_statistical_result_id UUID NULL; result_claim_version_id UUID NULL
result_scientific_conclusion_version_id UUID NULL; result_manuscript_version_id UUID NULL
result_source_version_id UUID NULL; supersedes_revision_action_id UUID NULL
content_hash CHAR(64) NOT NULL; hash_scheme VARCHAR(32) NOT NULL
```

Concrete FKs point to actors, review_issues, decision_records,
experiment_spec_versions, runs, statistical_results, claim_versions,
scientific_conclusion_versions, manuscript_versions, source_versions and the
same revision_actions table. All use RESTRICT; each FK has a B-tree index unless
covered by the proposed partial UNIQUE predecessor index. CHECKs enforce at
least one basis, finite action/pair/all-other-null shapes, no self-supersession,
lowercase 64-hex hash and fixed scheme. Normal-role DB guards enforce immutable
UPDATE/DELETE, same project/accessible source, frozen/terminal exact results,
Spec/Run pairing, valid correction chain and supported basis purpose. Authorization
and full deterministic closure verification remain Application obligations;
structural DB guards alone are not proof of a trustworthy scientific hash.

Project scope derives through the Issue's ReviewRecord and/or Decision project,
then is checked against result ownership (or explicit LiteratureSourceProjectLink).
Do not add a duplicate project owner, mutable action status, generic target
pair, result JSON, RevisionActionVersion, new audit schema or request receipt.

Use **exactly** Hash R2 15's `RevisionAction.content_hash` payload: `type`,
`material_version=1`, `review_issue` I-ref/null, `decision` R-ref/null,
`action_type`, `results` with all seven literal keys, predecessor R-ref/null and
`created_by` I-ref. Its seven result keys are
`result_experiment_spec_version`, `result_run`, `result_statistical_result`,
`result_claim_version`, `result_scientific_conclusion_version`,
`result_manuscript_version`, `result_source_version` (no `_id` suffix in payload).
Only Run uses I-ref; other results use their existing content hashes. Preserve
canonical-json-v1, sha256-cjson-v1, canonical UUIDs and explicit nulls. Do not hash
DTO project scope, time, row ID, derived status or operational data into a new
payload. Issue details remain independently immutable and verified through review
binding; this proposal does not give ReviewIssue a new hash.

Any future realization is an additive forward migration with one Alembic head;
accepted 0040–0042 remain unchanged. A downgrade must refuse deletion of committed
RevisionAction history or removal of required guarantees. Revision-purpose
Decision support is a separate dependency: 0042's fixed purpose/value and complete
conclusion-review checks must not be relaxed generically to accommodate it.

## 6. Errors — proposed mapping to existing stable categories

No new error enum or HTTP route is proposed. Detailed messages must be bounded,
sanitized and nondisclosing until access is established. Existing categories keep
their meaning; HASH_MISMATCH in design prose is not currently an ErrorCode member.

| Existing code | Proposed condition | Retry behavior |
| --- | --- | --- |
| `VALIDATION_ERROR` | Unknown field/type, absent basis, unsupported action or invalid result shape. | Correct input. |
| `AUTHENTICATION_REQUIRED` | No verified principal. | Authenticate. |
| `FORBIDDEN` | Missing current entitlement/credential/role, foreign scope or another actor's command replay. | Obtain valid entitlement; no blind retry. |
| `NOT_FOUND` | Missing exact resource after permitted scope disclosure. | Correct reference. |
| `FROZEN_REFERENCE_REQUIRED` | Required result is DRAFT/unsealed/unfrozen. | Complete the owning command first. |
| `INVALID_STATE_TRANSITION` | Run not terminal, unavailable Decision purpose/NO_CHANGE path or predecessor already superseded. | Resolve state/contract; no blind retry. |
| `PROVENANCE_CLOSURE_VIOLATION` | Hash mismatch, invalid exact binding, irrelevant result, corrupt basis, current-invalid first-write result, wrong Spec/Run pair or cycle. | Investigate/correct provenance; never omit offending refs. |
| `IDEMPOTENCY_CONFLICT` | Entitled same actor reuses UUID with different canonical command. | Recover original request; new ID only for a genuinely distinct authorized action. |
| `IMMUTABLE_RECORD` | Attempted material UPDATE/DELETE. | Append a correction. |
| `REFERENTIAL_INTEGRITY_ERROR` | Sanitized FK/constraint failure without a more specific mapping. | Correct input/state. |
| `CONCURRENT_MODIFICATION` | Deadlock/serialization or conflicting correction detected during coordination. | Only deadlock/serialization permits bounded full-transaction retry. |

Timeout/connection/commit-uncertainty handling must follow the existing sanitized
UoW contract; do not relabel uncertainty as successful completion or retry a new
UUID. Recover durable completion by exact UUID replay.

## 7. Transactions, concurrency and failure recovery

One synchronous Application command → Repository Port/UoW → persistence adapter
→ one PostgreSQL 18.x transaction. No Domain dependency on Session, API, CLI or
external harness. Adapters call the same Application command; results are DTOs,
not ORM entities. No external side effect occurs inside recording.

Proposed lock order: request coordination → affected exact old target row(s) in
stable table/UUID order → compatible closure/authority snapshot locks → review
and Issue rows in stable UUID order → correction predecessor → result checks →
insert/readback → commit. This is an ordering proposal, not a claim that today's
locks cover new paths. Inventory all participating writers before implementation.
Align with the existing Decision target-before-parent/review protocol and sorted
SHARE-table snapshot inventory; do not invert it or acquire a shared target lock
and later upgrade. Multiple-target/result paths require an approved compatible
ordering and demonstrated deadlock recovery, not arbitrary dynamic locking.

Issue/result validity, role/credential revocation, source access, correction
append and any future disposition writer must coordinate with the protected
facts they can change. Normal-role direct SQL must participate in structural
guards. Target locking alone cannot protect unrelated mutable eligibility.
After every wait, reread durable state with fresh statements and revalidate
credential, membership and effective role at fresh `clock_timestamp()` immediately
before insert/commit. Do not reuse transaction-start time or pre-lock eligibility.

Concurrent identical UUID requests commit at most one action and one existing
creation audit event, if applicable. Concurrent corrections of one predecessor
yield one successor; loser rolls back and reports conflict. Two distinct root
actions for one Issue may coexist (§4.3). Issue insertion/recording must not imply
a favorable-only snapshot or suppress legitimate later concerns. A newly committed
blocker remains visible to subsequent PROCEED/approval gates; action recording
cannot change the exact-target blocker predicate.

Bounded deadlock/serialization retry starts a new transaction and repeats all
reads/authorization/hash checks. Mid-write error leaves no partial action or
successful audit event. Failure to record does not erase the previously completed
result; retry the same action UUID. Unknown commit outcome is recovered by replay,
not by replacing history. Persisted hash verification after restart is mandatory.

## 8. Architecture test obligations

| Proposed test obligation | Required evidence |
| --- | --- |
| Application boundary/layering | Domain imports exclude ORM/FastAPI/Typer/harness; Human/Agent call the same policy; no adapter direct repository/DB path or ORM DTO leakage. |
| Finite schema/provenance | Seven concrete result FKs and pair/XOR shapes; no type/id soft edge, generic results JSON, cascade, parallel target owner or new receipt/digest. |
| Governance separation | Recording creates no IssueEvent/transition, Review/Decision/Approval/grant, VERIFIED, release, manuscript transition or external effect; PROCEED remains narrowly fixed. |
| Frozen closure/hash compatibility | Independent literal R2 hash oracle for all seven shapes, null keys, Run I-ref, StatisticalResult R-ref and predecessor; no Phase 1 hash/material changes. |
| Immutable history/correction | Normal-role SQL UPDATE/DELETE denies; correction preserves predecessor and old target/result, no fork/cycle/reparent; separate root actions remain allowed. |
| Authority/disclosure/replay | Human/Agent attribution, role expiry/revocation after waits, inaccessible refs nondisclosing, same-actor exact replay after stale/write-role loss only with current read right; no nested-review policy bypass. |
| Coordination | Shared writer inventory/order, actual PostgreSQL blocking witness, both commit orders for role/validity change and correction race; no sleep-only concurrency proof. |

These are implementation obligations for the admitted slice; unavailable shapes
are tested for closed admission. Task 13 evidence is recorded separately.

## 9. Acceptance criteria and evidence boundary

**Draft acceptance:** owner can review all proposed policies, dependencies and
questions; relative source links resolve; only this proposal changes; it remains
explicitly non-authorizing. Existing checks validate the unchanged baseline,
not a RevisionAction implementation or a Phase 2 gate.

**Later implementation acceptance, conditional on separate authorization:**

| Requirement | Required acceptance evidence |
| --- | --- |
| Basis and relevance | Disposable fixtures for issue-only, eligible decision-only and both; no basis, foreign project, wrong exact target, unrelated same-project result, malformed/corrupt basis deny atomically. Uncontracted Decision/NO_CHANGE paths deny. |
| All seven shapes | Each valid shape; every missing/extra result combination; DRAFT, unsealed/nonterminal Run, wrong Spec/Run, corrupt/STALE first-write result deny. FAILED/CANCELLED history never presented as positive evidence. |
| Exact revision trace | Read old review/issue/target hashes, result identities/hashes and correction chain after restart; new results preserve old versions; targeted re-review is a separate exact-target review. |
| No resolution/effect | Before/after row counts prove Issue remains OPEN and IssueEvent/review/decision/approval/publication/VERIFIED/effect state unchanged. Blocking PROCEED still denies. |
| Idempotency and correction | Exact replay, changed payload/actor/project, same-ID concurrency, one successor under concurrent correction, two independent legitimate root changes; no duplicate audit on replay. |
| PostgreSQL constraints/migrations | Real PostgreSQL 18.x catalog/FK/CHECK/trigger and normal-role direct-SQL evidence; every result shape, scope, immutability and correction guard; additive upgrade with one head and data-preserving/refused downgrade. No SQLite. |
| Failure/temporal safety | Actual lock witnesses (`pg_stat_activity`, `pg_blocking_pids`, backend/lock identity), both race orders; renewed DB-time authorization after wait; mid-write rollback, deadlock/serialization retry and uncertain-commit replay. |
| Regression | Existing PR2-14/15 unit and PostgreSQL suites, relevant Phase 1 result/closure tests, PR2-11/12/13 closure suites, architecture checks and applicable cross-phase golden workflows. Exact commands, server version, pass/fail/skip counts and P0/P1 findings recorded. |

Acceptance cannot claim the full Review → Issue → Decision → Revision → disposition
flow until the separate Decision-purpose and Issue-lifecycle contracts are frozen,
implemented and verified. Contract review or existing baseline tests do not close
that cycle. No formal PR2-14/15, M4, approval, deployment or phase gate is advanced
by this draft.

## 10. Owner questions resolved — conservative choices, 2026-10-14

| Question | Chosen option |
| --- | --- |
| Initial breadth | Smaller first slice: issue-only CLAIM_CHANGE for Claim reviews and CONCLUSION_CHANGE for conclusion reviews, each a later frozen version of the same owning identity. All seven R2 shapes remain represented in the closed DTO and literal hash; other command paths fail closed. |
| Revision-purpose Decision | Deferred pending its separate approved contract. Any Decision basis and NO_CHANGE deny; never reinterpret PROCEED. |
| Open-Issue correction path | Completed issue-only recording is admitted without PROCEED; Issue stays OPEN. |
| Writer/read authority | Active OWNER/RESEARCHER recorder through the same Human/Agent boundary; existing Decision read roles. Existing canonical subject binding currently admits HUMAN only, so unbound Agents fail closed; no identity guard is weakened or new Agent authentication invented. Return verified typed review references only, with no nested review text or Issue descriptions, so no expansion of review disclosure. |
| Deterministic relevance | Admit only same-identity, strictly increasing accepted version_number for the matching target type. All cross-domain paths and other shapes deferred; no soft references or narrative causality. |
| Historical admission | Current-valid first-write results; stale old target allowed; authorized exact historical replay allowed after result invalidity/write-role loss. No stale-result first admission. |
| Correction semantics | One nonforking same-basis predecessor chain; multiple independent roots per Issue. Different basis requires a separate root. |
| Issue lifecycle dependency | ADDRESSED/DISMISSED/VERIFIED and all Issue transitions deferred to a separate contract. |
| Transaction realization | Existing Decision request → exact old target FOR UPDATE → sorted SHARE snapshot → review/Issue → predecessor order; selected results are read under the protected table snapshot. Reuse the existing Decision inventory of mutable closure/authority facts, excluding immutable frozen ClaimVersion material (FROZEN/SUPERSEDED both admissible). Closure adapters use protected reads only in this UoW, without late parent/result row locks; authority also reads under the snapshot rather than taking the project lock after it. Owning command defaults are unchanged. Immutable review/Issue basis uses row locks; frozen conclusion versions/inputs rely on their existing immutable SQL guards, without extra SHARE table locks that invert trigger coordination. Existing 10s lock/30s statement limits and maximum three deadlock/serialization transaction attempts; uncertainty recovered by exact UUID. |

No Decision-purpose, Issue-lifecycle, approval or phase gate is authorized here.

## 11. Documentation-task verification — 2026-10-13

Only this proposal is added. The following checks ran on the existing checkout;
they are baseline/documentation evidence, not RevisionAction acceptance. Logs and
temporary tooling data are under ignored `tmp/task10-verification/` inside the
repository. No branch, commit or push was created.

The initial `uv run --offline` attempts exited 2 before running tests because the
default cache path was sandbox-inaccessible. Successful tool execution below uses
an in-repository cache and the existing locked environment (`--no-sync`).

```bash
uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra tests/architecture tests/unit/architecture tests/unit/phase2/test_pr2_15_decision.py
uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync ruff check .
uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync ruff format --check .
uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync pyright
git diff --check
git diff --exit-code -- docs/architecture src migrations tests
```

| Check | Exact result |
| --- | --- |
| Architecture and Decision unit selection | **130 passed**, 0 failed, 0 skipped, in 2.07s. |
| Ruff lint | **PASS**, “All checks passed!” |
| Ruff format | **PASS**, 456 files already formatted. |
| Pyright | **PASS**, 0 errors, 0 warnings, 0 informations. |
| Diff whitespace and protected-path diff | **PASS**, both exit 0; protected paths unchanged. |

Exact local-link/status check (also rerun after this evidence section was added):

```bash
uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync python -c 'from pathlib import Path; import re; p=Path("docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md"); s=p.read_text(); links=re.findall(r"\]\(([^)]+)\)", s); assert all((p.parent/t).exists() for t in links); assert "DRAFT — awaiting owner approval; not authorized for implementation" in s; print(f"2 checks passed: {len(links)} local links resolve; exact DRAFT status present")'
```

Result: **2 checks passed**, all **17** relative source links resolve and exact
required status is present. The check counts source links outside its own code
example; the regex contains no additional Markdown link.

PostgreSQL 18 initialization was attempted only in repository scratch space:

```bash
mkdir -p tmp/task10-verification/pgsocket
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/task10-verification/pgdata -U task10_admin -A trust --no-locale
/opt/homebrew/opt/postgresql@18/bin/pg_ctl -D tmp/task10-verification/pgdata -l tmp/task10-verification/postgres.log -o '-k /Users/fengwang/Documents/ResearchBaseProject/tmp/task10-verification/pgsocket -p 55479 -h 127.0.0.1' start
RB_TEST_ADMIN_URL=postgresql+psycopg://task10_admin@127.0.0.1:55479/postgres uv --cache-dir tmp/task10-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py
```

**BLOCKED, not PASS:** initdb exited 1 with `could not create shared memory
segment: Operation not permitted` (`shmget`); it removed the incomplete cluster.
pg_ctl exited 1 because that data directory did not exist. Both conventional
local ports 5432 and 55440 had no responding server in `pg_isready` checks.
The selected integration run exited 1: **0 passed, 0 failed assertions, 56 setup
errors, 0 skipped**, in 5.05s. Connection attempts to port 55479 were also denied
with `Operation not permitted`. No integration assertion or PostgreSQL acceptance
ran successfully. Approval escalation is unavailable in this environment.

No production/retained database was modified. A PostgreSQL-enabled environment
must rerun the four selected suites to obtain baseline integration evidence.
Other scientific integration suites were not run: this proposal changes no
executable, schema or frozen contract behavior. Broader suites in §9 remain
obligations of a later authorized implementation, not claims about this draft.

## 12. Task 13 implementation and verification — 2026-10-14

Implemented the §10 first slice: issue-only, same-identity successor CLAIM_CHANGE
and CONCLUSION_CHANGE; immutable command/readback, literal R2 material, existing
UoW/ports, protected closure reads, fresh authority, UUID replay and nonforking
correction. Other shapes, Decision bases, NO_CHANGE, Issue disposition, approval,
release and API/CLI routes remain unavailable. All seven physical result FKs and
literal hash shapes are represented. Migration 0044 follows 0043; all 45 previous
migration files are byte-identical to HEAD.

Final evidence: [check results](../verification/task13/checks.json),
[complete PostgreSQL coverage](../verification/task13/full-verified-summary.json),
[read-only review](../verification/task13/read-only-review.json), and
[historical migration hashes](../verification/task13/historical-migration-sha256.json).

| Check | Actual final result |
| --- | --- |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Ruff lint/format | PASS; 471 files already formatted |
| Unit | 1,802 passed; 0 failed/errors/skipped |
| Architecture | 117 passed; 0 failed/errors/skipped |
| RevisionAction unit/integration | 84 passed; 0 failed/errors/skipped |
| Task 12 migration compatibility | 9 passed; 0 failed/errors/skipped |
| Complete suite, PostgreSQL 18.6 | 5,058 unique collected tests passed; 0 failed/errors/skipped |

The complete suite ran in five partitions. Initial empty-database bootstrap was
corrected, and the final run migrated a newly created shared database first.
Task 12's no-new-table test was pinned to its own 0043 revision; its entire
562-test partition was rerun and passed. Final coverage verifies the union of
passing partition XML against fresh complete collection, without omissions or
duplicates. Original failed results remain recorded as failures. Every shared
verification database was deleted; Phase 2 fixtures also use disposable databases.

Two inherited Task 12 XML reports required trailing-space entity encoding for
the unchanged whitespace gate. Parsed XML content was verified identical; see
[encoding evidence](../verification/task13/xml-evidence-encoding.json). No governing
Harness rule was modified and no historical result was relabeled.

Commands ran from the repository with `UV_CACHE_DIR=$PWD/.uv-cache`:

```bash
uv run --offline --no-sync pyright
uv run --offline --no-sync ruff check .
uv run --offline --no-sync ruff format --check .
uv run --offline --no-sync pytest -o addopts='' -q -ra tests/unit --junitxml=docs/verification/task13/unit-final.xml
uv run --offline --no-sync pytest -o addopts='' -q -ra tests/architecture tests/unit/architecture --junitxml=docs/verification/task13/architecture-final.xml
uv run --offline --no-sync pytest -o addopts='' -q -ra tests/integration/phase2/test_revision_action.py tests/unit/phase2/test_revision_action.py --junitxml=docs/verification/task13/revision-final.xml
uv run --offline --no-sync pytest -o addopts='' -q -ra tests/integration/phase2/test_task12_schema_migration.py --junitxml=docs/verification/task13/task12-compatibility.xml
RB_TASK13_RUN_DIR=$PWD/docs/verification/task13/final-run RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres HG1_RUN_LOCAL=1 uv run --offline --no-sync python docs/verification/task13/run_full_verification.py
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres HG1_RUN_LOCAL=1 uv run --offline --no-sync python docs/verification/task13/run_single_shard.py 4
uv run --offline --no-sync python docs/verification/task13/verify_complete_suite.py
git diff --check
```

The targeted integration commands used
`DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase`
and the same PostgreSQL admin URL; each test created its own disposable database.
Expanded per-partition Python/pytest argument lists are retained as command JSON
beside their XML. No commit, push, branch creation or formal phase-gate action occurred.
