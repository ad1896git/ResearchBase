# PR2-15-S1 Minimal DecisionRecord Command Contract v1.0

**Status: FROZEN; owner-approved A–E; independent contract consistency review PASS.** See the [scoped freeze declaration](../phase2/PR2-15-S1-contract-freeze-declaration.md).
**Authority:** Addendum A23 and ADR-0014, limited to the owner's approved A–E in “ResearchBase — PR2-15 V2 FINAL CONTRACT FREEZE”. This is a design contract, not implementation, migration, deployment, scientific decision or formal milestone authorization.

## 1. Scope and hierarchy

Only `record_decision(INTERNAL_SCIENTIFIC_RELEASE, PROCEED)` is specified here. System scientific invariants, frozen Phase 1 semantics, Addendum A18/R2 hash and governance companions, and A20/R4 temporal authorization remain authoritative. This companion refines only command-specific gaps under Phase 2 specification §PR2-15 and Correction §6. It does not widen the finite approval policy or change R2 hash material. Prior V2 DRAFT documents are historical proposals, not competing authority.

`PROCEED` records one immutable, attributable internal scientific decision. It may supply one piece of evidence for a later Application request; every later workflow independently verifies its own authorization, evidence, current state and admission gates. It creates no Approval, grant, release authorization, publication, manuscript freeze/submission, Issue disposition, VERIFIED status, human verification or formal milestone acceptance. Review, Decision, Approval and effect remain distinct.

## 2. Exact command and actor

The command uses existing canonical identities and field representations:

| Input | Representation and meaning |
| --- | --- |
| `id` | UUID; the request UUID is also canonical `DecisionRecord.id`. No new persisted request-ID field or receipt table. |
| `project_id` | Exact Project UUID. |
| `scientific_conclusion_version_id` | Exact target UUID, represented by the existing typed `decision_basis_conclusions` relation, not a new DecisionRecord column. |
| `decision_type` | Fixed persisted literal `INTERNAL_SCIENTIFIC_RELEASE`; any other value fails this command. |
| `decision` | Fixed persisted literal `PROCEED`; any other value fails this command. |
| `question`, `rationale` | Nonblank text required by the existing DecisionRecord field/hash contract; canonical Unicode handling follows Hash R2. Neither text executes policy or substitutes for evidence. |

The verified trusted context supplies `decided_by`; fresh trusted DB time supplies `decided_at`. There are no caller-supplied actor/role/credential/hash/time, review-ID selection, supersession, disposition, or effect inputs. Unknown command fields are rejected. `supersedes_decision_id` is NULL for this command.

First-time creation requires the existing ACTIVE same-project membership, effective OWNER or APPROVER authority, live verified credential and canonical actor identity. The decider must be independent of affected target material authors/contributors under Governance R2 §1 and Correction §6. This command adds no HUMAN-only decider requirement or decider-versus-reviewer exclusion. The later HUMAN approver must still be distinct from the decider, requester, authors and required reviewers as frozen in Governance R2 §1. An AI cannot invent the actual actor's intentional submission or claim HUMAN attribution.

## 3. Target and complete review-evidence snapshot

First creation requires the exact same-project ScientificConclusionVersion to be FROZEN and currently valid, with verified R2 content hash and complete input closure. No latest-version substitution is permitted.

The service, not the caller, selects **all contract-eligible committed InternalReviewRecords** for this exact project, conclusion version and target content hash at the protected transaction snapshot. A qualifying record is immutable/completed, has a valid own hash and concrete exact-target binding, and satisfies the applicable PR2-14 reviewer identity, author independence and review-creation authorization requirements. In the initial PR2-14 schema the committed immutable record itself denotes completion; no completion flag is added. Include every review type/recommendation permitted by PR2-14, including REJECT and UNCERTAIN. At least one qualifying record is required. Presentation filtering, favorable-only selection and a mutable latest-review pointer cannot define the basis. A matching record with corrupt hash, broken provenance or invalid binding causes fail-closed rejection; corruption must not be silently omitted to obtain a favorable set.

The immutable basis is exactly one conclusion reference and that complete review set, with exact historical IDs/content hashes, using the existing typed basis tables. Sort `(target.type,target.id,target.content_hash)` and assign deterministic contiguous ordinals, applying the literal R2 basis payload and own-content payload without alteration. The existing `basis_set_hash` seals the historical evidence snapshot; no additional persisted digest, snapshot entity or field is admitted. The server-derived basis is output, not a caller command argument. A later review does not change an already committed decision's basis. Historical reviewer role expiry by itself does not rewrite a valid review-creation fact; current decider/read authority is still checked. Any existing frozen rule that makes review evidence currently ineligible must be applied and its changing state coordinated as §5 requires.

## 4. Blocking Issues and no replacement

An applicable blocker is exactly `ReviewIssue.status=OPEN AND severity=BLOCKING`, through a valid authoritative ReviewRecord relationship to the same Project and **exact** ScientificConclusionVersion. Inspect the complete applicable Issue set independently of displayed reviews. Another version, merely shared project, Claim, source or similar content cannot create a blocking relationship. An applicable blocker denies PROCEED without committing a DecisionRecord, basis rows or decision audit event.

This first command must not supersede, replace, update, delete or silently invalidate any earlier DecisionRecord for the same `(project_id, exact scientific_conclusion_version_id, decision_type=INTERNAL_SCIENTIFIC_RELEASE)` scope. A new UUID does not bypass this prohibition, including when a different actor submits it. Exact replay uses §6. First creation requires no existing decision in that scope. The target UUID plus existing project/type and typed basis relations represent this scope; no new normative identity is needed. Future persistence must enforce this under the shared target lock and database-level scope guard, including direct SQL under the normal application role. A unique decision/target pair inside one basis set alone does not enforce uniqueness across decisions.

## 5. Shared transaction coordination: Issues AND reviews

One Application command is one PostgreSQL transaction. The coordination identity is the existing exact ScientificConclusionVersion row. Every participating writer must use compatible exclusion on that row before evaluating or changing protected state. The required participants include:

1. First-time Decision creation: complete review-set selection, blocker check, no-earlier-decision check and atomic insert.
2. ScientificConclusionVersion ReviewRecord creation, including a review with **zero Issues**. Immutable review UPDATE/DELETE remain forbidden. Any later authorized operation affecting review eligibility must coordinate too.
3. Every relevant Issue INSERT and any later authorized UPDATE, DELETE or lifecycle change that can alter the blocking predicate. Existing forbidden mutations remain forbidden; coordination grants no disposition authority.
4. Other mutable eligibility facts relied on for the protected snapshot: implementations must use the existing authority/provenance locking rules and a compatible locking/isolation protocol for their writers. Target-row locking alone does not prove consistency of unrelated upstream or authorization state. Missing participation is an implementation blocker, not permission to weaken the predicate.

The bounded database realization uses the target row `FOR UPDATE` on both sides, held through commit/rollback. New conclusion ReviewRecord INSERT must take that mode from the start; retaining initial `FOR SHARE` and later upgrading during Issue INSERT can deadlock between two initial-review transactions. Issue INSERT obtains the immutable review's target identity, locks the target, then locks/rereads the ReviewRecord and checks exact binding. The existing 0040 triggers do not yet implement these requirements. Normal-role direct SQL must participate through forward database guards rather than depending solely on voluntary Application behavior.

Required relative order is command/request coordination (if needed) → exact target row → parent/other closure and authority locks in a documented compatible order → review rows in stable UUID order → Issue/basis writes. No participating path may invert the target/review order. For an already existing target, missing/invalid references deny; no lock key may be caller-defined authority. Any later wait requires reread of affected durable state and renewed fresh `clock_timestamp()` authorization under TEMP-AUTH-01 before the effect. The implementation must document all required locks, order and retry boundary; it must not claim complete coordination based only on a Decision-side lock.

After target coordination and all required waits, use fresh transactionally consistent reads to select the complete eligible review set, all applicable blockers and earlier scoped decisions, verify hashes/closure, then revalidate current credential, membership, role and independence with fresh trusted DB time immediately before writing. A cached pre-lock list or a transaction-start snapshot at READ COMMITTED cannot substitute for fresh post-wait statements. An equivalent isolation protocol must prove the same insertion/eligibility guarantees; it cannot omit writer participation.

**Issue/review first:** if that writer commits first, Decision waits and then includes the new eligible review or observes the blocker and denies. **Decision first:** later writers wait until the Decision completes, then may create otherwise-authorized review/Issue history; the old Decision and its basis remain immutable. Later approval/release gates recheck new blockers and current evidence; old PROCEED does not authorize them. This prevents insertion phantoms at the protected snapshot without preventing legitimate later concerns.

Deadlock/serialization failure rolls back the entire attempt. Any bounded retry starts a new transaction, repeats coordination, reads and authorization, and compares request identity; never reuse a pre-wait authorization or partially selected basis. Commit uncertainty is recovered by exact UUID replay, not a new UUID or replacement decision. Rejection leaves no partial decision, basis or successful audit event. PostgreSQL enforcement and end-to-end race safety are **NOT VERIFIED** until separately implemented and tested.

## 6. UUID replay, disclosure and immutable history

The canonical caller command is a closed normalized tuple of `id`, `project_id`, exact target UUID, fixed `decision_type`, fixed `decision`, `question`, `rationale`, plus the trusted resolved actor and command identity. UUID and text normalization follow R2. The server-selected review snapshot is not caller material to rescan during replay; retain and verify the saved typed basis. Compare existing canonical material directly; do not add a request hash field or change scientific hash payloads.

Authenticate and establish current historical-record read authorization before disclosing protected existence, content or conflict details. Require existing project/actor/command scope to match; another actor cannot turn a reused UUID into replay authority. Current read entitlement requires the applicable existing read policy, ACTIVE project membership/effective read role and live verified credential, evaluated with fresh trusted time where time-sensitive. The old authoring role supplies no perpetual read right. A separately authorized history read is distinct from impersonating the original command actor.

For a durable completed matching record, same UUID and identical canonical command returns its immutable saved result without another DecisionRecord or decision audit event. This remains allowed if target later becomes STALE or original write role expires/revokes, provided current read entitlement survives. Same UUID with different canonical command conflicts for an entitled caller; unauthorized callers receive nondisclosing authentication/authorization failure. New creation always needs current eligibility and write authority. Unknown or incomplete history is not a successful replay and enters current first-time eligibility or fails closed. Concurrent same-UUID commands must produce at most one committed record; new-UUID requests for the same scope fail §4.

Return existing canonical `id`, project/type/value, actor/time, exact target/ref hashes and complete saved typed review basis with `basis_set_hash` and `content_hash`. The immutable DecisionRecord actor/time/request identity and basis provide the auditable fact under the existing contract. If an existing audit mechanism records creation, it must commit atomically once and not duplicate on replay; no new audit schema is admitted here. Errors preserve existing Application categories for invalid input/basis, missing authentication, forbidden access, conflict of interest, idempotency/scope conflict and transaction failure. Never return raw DB/credential diagnostics or disclose other-project identity through an error.

## 7. Deferred lifecycle and implementation boundary

No-change DISMISSED is deferred to a separate future frozen contract. This command creates no RevisionAction, Issue transition, alternate approval or bypass. The broader dependency cycle remains **OPEN**: blocking-Issue dismissal needs its own valid DecisionRecord/disposition basis, while this PROCEED command denies until applicable blockers are absent. Zero-blocker targets have a reachable path; that does not resolve the broader cycle or complete PR2-14.

No PR2-14 STALE replay semantics are changed by §6. Existing PR2-14 behavior and its separate question remain unchanged. Human Gate, TDG2 activation, formal PR2-06/10/11/12/13/14/15 and M4 gates retain their prior status.

Future separate engineering authorization must implement the existing DecisionRecord/typed basis objects, no-replacement database guard, immutable hashes/history and complete-review snapshot, and replace relevant review/Issue guards in a **forward** migration. Do not edit accepted migrations or add unauthorized semantic columns, receipts or digest fields. Preserve one Alembic head; a data-preserving downgrade must refuse loss of committed history or silently removed guarantees. Migration 0040 is unchanged by this contract freeze.

## 8. Required acceptance evidence — planned, NOT RUN

| Requirement | Later authorized verification obligation |
| --- | --- |
| Exact command/actor/target | Valid disposable synthetic fixture; wrong purpose/value/actor, author conflict, role expiry/revocation, draft/STALE/missing/cross-project target deny atomically. No invented HUMAN evidence. |
| Complete review basis | All eligible review types and favorable/unfavorable recommendations included; zero eligible reviews deny; corrupted exact-target record fails closed; exact persisted refs/ordinals/R2 hashes read back after restart. |
| Blocking scope | OPEN/BLOCKING denies; lower severity alone does not; unrelated version/project/common Claim/source does not become a blocker; direct SQL preserves typed bindings. |
| Review and Issue insertion races | Separate backends show actual lock wait using `pg_stat_activity`, `pg_blocking_pids()` and backend/lock IDs; prove both commit orders for zero-Issue review INSERT and blocking Issue INSERT, complete evidence snapshot, no partial writes. Sleep alone is insufficient. |
| Mutable eligibility and temporal auth | Inventory relevant writers; prove shared coordination or equivalent consistency, fresh post-lock DB time, revoked/expired authority denial and rollback. Forbidden Issue/review mutations remain forbidden. |
| Non-replacement | Same scope/new UUID, concurrent different UUIDs and different actors cannot create a second decision; normal-role direct SQL scope substitution fails; original remains unchanged. |
| Replay/disclosure | Identical replay once; different payload conflicts; STALE target/original role loss permits only currently authorized historical replay; unknown ID cannot succeed; unauthorized caller learns no protected existence. |
| Failure safety | Mid-write rollback, deadlock/serialization retry, uncertain commit recovery; no duplicate basis/audit or lost history; catalog/upgrade/data-preserving downgrade checks on disposable PostgreSQL. |
| Prohibited effects | No Approval/grant/release/Issue disposition/RevisionAction/VERIFIED/manuscript transition or retained deployment write; no PR2-14 replay behavior change. |

Contract consistency review is not implementation evidence. No automated test or PostgreSQL write is authorized by this document's freeze.
