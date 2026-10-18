# Finding / Impact Propagation (B26) — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B26 separates current-validity propagation from recording Findings and Impact
Assessments. The proposed first slice explains how one existing Finding and its
recorded assessment targets reach one exact frozen manuscript. It returns B25's
current validity and exact occurrence paths from the same PostgreSQL snapshot.
Reachability is not a new assessment or proof that this Finding caused every
invalidity in the manuscript. Nothing is written or automatically invalidated.

After owner approval **and separate implementation authorization**, build in order:

1. Confirm the accepted Finding/Impact base and B25 against §1. Keep their target
   vocabulary, hashes and validity rules (§3).
2. Add the closed query/readbacks in §11.3. This slice has one query, no commands,
   migration or adapters (§12.5).
3. Extract a same-UoW B25 validity builder and compose it with nonlocking Finding
   and complete assessment reads (§12.3). Do not call a public reader that opens
   another transaction.
4. Verify retained bindings and hashes before matching exact target identities to
   B25 witnesses. Return every occurrence or a named completeness error (§3).
5. Run §12.4's focused tests, record exact evidence, and stop. This draft and its
   documentation checks do not establish implementation or Phase 2 acceptance.

Five review rules:

1. Deterministic facts outrank review, Decision and Approval.
2. A Finding alone does not invalidate its target; an impact path is not support.
3. Keep old scientific bytes, hashes, exact references and current pointers intact.
4. Reads use one REPEATABLE READ snapshot with no explicit table, advisory or row locks.
5. No automatic Finding, assessment, Issue, grant transition or novelty propagation
   is implied. Add automation only through the owning approved contract.

Read §§1–4 first; use the glossary (§10), pinned decisions (§11) and construction
guide (§12) as lookup material. All new behavior below is proposed, not shipped.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried into B26 |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§19–21, 69–74 | Findings do not mutate canonical facts; current validity is derived; governance locators cannot replace concrete scientific provenance. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A3–A4, A10, A18–A21; [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), reference and schema rules | Reuse existing Assessment/Relation patterns and exact frozen references; no new canonical schema or authority from historical attribution. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), frozen provenance, compatibility and G3 | Preserve retained history and common Application boundaries; manuscript text is not scientific truth. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§36–38, F1, P2-INV-016 | Corrected/retracted literature must affect downstream current validity without rewriting old evidence. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7; [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md); [R2 Gap Closure 14](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md), §§2–3; [Hash Contract 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md) | Exact support snapshots and Conclusion inputs own propagation; historical material integrity and derived current validity are separate. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 19 | No direct Harness persistence, inferred scientific truth or acceptance without executed evidence. |

Inspected code, rather than inferred acceptance:

- [Governance domain](../../src/researchbase/domain/governance.py),
  [commands](../../src/researchbase/application/governance.py) and
  [repository](../../src/researchbase/persistence/governance_repository.py) already
  own Finding lifecycle, immutable ImpactAssessments/targets, CorrectionRecords,
  literal assessment hashes and target binding verification.
- [Governance queries](../../src/researchbase/application/governance_queries.py)
  provide Phase 1 downstream paths and `validity_projection_in_uow`. The legacy
  public query methods open their own UoWs; they are not B26 composition hooks.
  `validity_rows` selects assessments by their explicit `impact_targets`, not by
  transitively copying a Finding's conclusion onto every reachable node.
- [B25 Application](../../src/researchbase/application/manuscript_validity.py)
  and [accepted contract](B25_Manuscript_Validity_Contract_DRAFT.md) provide
  exact-manuscript witnesses across experimental and literature dependencies.
  B25's public methods also open a UoW; its collector and owner verification hooks
  are the basis for the proposed same-UoW extraction, not a second validity engine.
- [B04 repository](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  supplies `prepare_read(bounded=True)`: first SQL is REPEATABLE READ, READ ONLY;
  bounded SELECTs fail before materializing more than 10,000 rows.
- [Decision repository](../../src/researchbase/persistence/decision_repository.py)
  and [novelty repository](../../src/researchbase/persistence/novelty_repository.py)
  show the existing first-SHARE write protocol. [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
  shows deferred completeness triggers. Neither pattern authorizes new B26 writes.

[PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md) and
[PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) supply this draft's structure.
There is no B26 execution pack in this checkout. B18's parallel novelty contract
is outside this slice; existing novelty code is only a transaction-pattern reference.

## 2. Scope, dependency boundaries and non-goals

Propose `get_finding_manuscript_impact`: one Project, one existing Finding, one
Publication and one exact FROZEN ManuscriptVersion. The result covers only this
manuscript's verified closure and all assessments explicitly linked to this Finding.
It is not project-wide downstream discovery or a declaration that every affected
publication has been found. A caller can inspect another exact manuscript with a
fresh query; separate calls do not share a snapshot.

B25 and accepted Finding/Impact persistence are prerequisites. Reuse B04,
literature/support and Conclusion verification through B25. Do not implement a
missing prerequisite, new governance target type, source-to-Finding write bridge,
novelty propagation, scientific repair or workflow transition here.

## 3. Invariants and conservative judgments

### 3.1 Current validity stays with its existing owner

Run B25's whole exact closure verification with `admission=False`. Preserve its
order-independent aggregate: INVALID/RETRACTED → INVALID; otherwise any non-VALID
dependency → STALE; otherwise VALID. Its governance translation remains:
`invalid` → INVALID; `not_assessed`/`unaffected` without corrections → VALID;
all other states or correction IDs → STALE. NOT_ASSESSED is no positive audit
assurance. A corrected predecessor is retained history, not automatically the
current source's validity owner. Neither supersession alone nor current-pointer
navigation replaces an exact dependency.

The accepted governance projection excludes assessments whose linked Finding is
`dismissed`. It includes `open`, `confirmed` and `resolved` Findings, and unlinked
assessments. Among active assessments precedence is `invalid > stale >
requires_review > unknown > unaffected`; no active assessment yields
`not_assessed`. Corrections are returned independently. A new `no_impact`
assessment, resolving a Finding, or recording a Correction does not erase an
older active invalid assessment. Preserve these semantics, not latest-wins repair.

All of this is derived data. Finding presence/severity, an Issue, a review,
Decision or Approval supplies no additional invalidity or validity override.
Current manuscript validity includes other Findings and source/evidence states;
it must not be relabeled as the selected Finding's causal contribution.

### 3.2 Finding/assessment matches are exact reachability witnesses

After authorization and scoped lookups, load the Finding and **all** assessments
whose `audit_finding_id` equals its ID. Verify the complete target sets and literal
assessment hashes with the accepted governance repository/domain, including
targets not reachable from this manuscript. Require every record and target to
belong to the requested Project. Verify the Finding's saved target hash binding
too; nullable hashes retain their accepted meaning (not an invented Run hash).

Map the eight governance kinds in §11.3 to B25's typed node kinds. Match exact
kind and UUID against verified B25 witnesses. Emit one FINDING_TARGET match for
the Finding's target when present, and one ASSESSMENT_TARGET match per linked
assessment target when present. Retain all B25 occurrences, including repeated
placements, retained predecessor paths, and citation/artifact paths. Matching
retained history or a citation is navigation, not positive scientific support or
proof of a current active dependency. Do not infer path activity from node names;
B25's aggregate already owns that distinction.

Keep dismissed and no-impact assessments in historical readback and matches.
Only the existing validity reader decides whether they contribute to state.
Do not match by parent ID, shared source, title, text, timestamp or current pointer.
An unassessed Finding may have a target match and an empty assessment set; it
does not acquire an implicit assessment. Zero matches is a complete successful
answer for this exact closure, not evidence of no impact elsewhere.

Integrity failure is an error, not an INVALID result. Normalize malformed saved
governance bindings/hashes and nested missing provenance to
PROVENANCE_CLOSURE_VIOLATION. Never drop a broken assessment or truncate paths.

## 4. Proposed commands, DTOs and historical readback

No commands. One closed query (§11.3), with an out-of-band `VerifiedPrincipal`,
returns typed immutable data, never ORM models. The embedded B25 validity result
and selected Finding/assessments are evaluated within the same UoW.

Use B25/B04's nonlocking authorization and publication reader policy: active
HUMAN with effective OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER role, live membership,
subject binding and credential. Human and Agent callers enter the same boundary;
an Agent principal receives the existing policy denial, not an alternate route.
Authenticate and authorize Project read access before target lookup. Match the
Finding's Project before hydrating its target/payload; a foreign or absent root,
Publication or manuscript returns NOT_FOUND without disclosure. Archived-project
reads follow the existing B04 reader policy. Fresh DB time and credential checks
are required again immediately before return.

DRAFT manuscript → VERSION_NOT_FROZEN; unsupported persisted manuscript lifecycle
→ PROVENANCE_CLOSURE_VIOLATION. Existing owner verifiers retain their frozen
reference rules. `evaluated_at` is the final UTC database authorization time,
not a durable snapshot ID. No replay receipt, saved projection or cached answer.

## 5. Schema and literal hash proposal — no migration

No tables, columns, indexes, triggers, events, cache or new hash payload. Reuse the
existing governance records and concrete scientific edges. The closed typed
references in query DTOs are transient, not a new persisted polymorphic chain.
Existing governance soft locators remain confined to their accepted cross-cutting
role and undergo reference validation. Do not use assessment JSON as a graph.

Assessment hashes still come from `calculate_impact_assessment_hash`; B25 hashes
come from their owning verifiers. No hash is added to this transient readback.
§12.1 inventories existing types/constraints, not migration authorization.

## 6. Error contract — proposed use of existing categories

Use §11.2 only. STALE, INVALID, dismissed Findings, empty assessments and zero
matches are successful data. A missing user-selected root is distinct from a
missing saved edge. Return no partial result on integrity or completeness failure.

## 7. Transactions, concurrency and failure recovery

One fresh REPEATABLE READ, READ ONLY UoW per query, configured before authorization
or any data SELECT (§12.2). No explicit table, advisory or row locks. PostgreSQL's
ordinary SELECT ACCESS SHARE locks are not explicit lock commands. No writes,
flushes, receipts, temporary tables or hidden propagation events.

Concurrent Finding status changes, assessment/correction INSERTs, source lineage
changes and evidence verification changes may commit during a read. Return a
complete snapshot-visible result; the next query may differ. Fresh time can expire
credentials while membership/binding rows remain snapshot-visible. Do not promise
linearizable revocation visibility. ArtifactStore bytes are verified by existing
owners; PostgreSQL cannot snapshot external files.

Retain UoW error sanitation; connection loss or an aborted branch returns no DTO.
No automatic retry protocol is added. A caller may issue a fresh query. Existing
write commands retain their own transactions and lock order; B26 does not wrap
them or create a second transaction inside them.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins new test files and regression selections. Use separate PostgreSQL 18.x
connections and observed barriers for concurrency; timing-only sleeps do not
prove snapshot consistency or nonblocking reads. This documentation task adds no
executable tests or behavior.

## 9. Acceptance criteria and evidence boundary

Future acceptance requires one complete bounded query, exact matching, unchanged
owner validity/hash semantics, no write effects, and observed nonlocking snapshot
evidence. Run all §12.4 checks; report counts/skips, with no open P0/P1. B26 first
slice acceptance would not accept global discovery, automated Finding creation,
novelty propagation, submission workflow or the Phase 2 exit gate. The broader
F1/P2-INV-016 obligation still needs its owning end-to-end evidence/dispositions.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Finding | Existing attributed governance concern with a validated target and lifecycle. |
| ImpactAssessment | Immutable recorded conclusion and explicit target set; not a scientific fact mutation. |
| Propagation | Re-evaluating downstream current validity along retained exact dependencies. |
| Match | Exact target reachability within the selected manuscript's B25 witnesses. |
| Current validity | Owner-derived state, independent of retained hash integrity and authority. |
| Retained history | Verified earlier material that may be navigable without owning current validity. |
| Complete | Every scoped row and occurrence in one snapshot, or a named error. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Pin one Application-only Finding→exact-manuscript explanation query. No automatic
recording is required by this proposed slice. Reuse B25 propagation rather than
copying assessment targets into downstream tables. Preserve existing governance
enum spellings, target kinds, precedence and correction semantics. No new
persistence, runtime dependency, schema admission or change to public B25 DTOs.
Source retraction/dispute still affects B25 validity even without a Finding;
B26 does not fabricate a source-target Finding that the accepted registry cannot
represent. B18 novelty propagation is deferred independently.

### 11.2 Pinned error mappings

These match [HTTP errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py); no adapters are added here.

| Code | HTTP | CLI exit | Trigger |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong query type, extra fields or non-UUID input. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing valid verified principal. |
| FORBIDDEN | 403 | 3 | Reader entitlement or live credential check fails. |
| NOT_FOUND | 404 | 3 | Authorized exact root or manuscript scope absent/foreign. |
| VERSION_NOT_FROZEN | 409 | 4 | Selected manuscript is DRAFT. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Owning verifier requires frozen referenced material. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Broken saved binding/hash/shape/project, unsupported persisted enum, missing saved edge, or fixed completeness ceiling exceeded. |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing UoW-normalized concurrency/timeout failure. |

Within verified saved closure normalize nested NOT_FOUND, VALIDATION_ERROR,
REFERENTIAL_INTEGRITY_ERROR, REVIEW_TARGET_NOT_FROZEN and
INVALID_SOURCE_VERSION_LINEAGE to PROVENANCE_CLOSURE_VIOLATION; do not mask root
lookup or caller validation errors. Unexpected failures retain sanitized
INTERNAL_ERROR, HTTP 500 / CLI fallback 1; INTERNAL_ERROR is not a new ErrorCode.
No HASH_MISMATCH, FINDING_PROPAGATION_FAILED or MANUSCRIPT_INVALID code.

### 11.3 DTO fields, Python types and limits

New DTOs are frozen, slotted and closed using the existing Application decorator.
Require exact `uuid.UUID` instances, not strings. No caller-selected bounds,
actors, hashes, statuses or timestamps. Tuples contain the declared types only.

| DTO | Exhaustive fields |
| --- | --- |
| `GetFindingManuscriptImpactQuery` | `project_id: UUID`, `finding_id: UUID`, `publication_id: UUID`, `manuscript_version_id: UUID`. |
| `FindingImpactMatch` | `basis: Literal['FINDING_TARGET','ASSESSMENT_TARGET']`, `assessment_id: UUID \| None`, `target: AuditNodeRef`, `occurrences: tuple[AuditOccurrence, ...]`. |
| `FindingManuscriptImpactReadback` | `finding: AuditFinding`, `assessments: tuple[ImpactAssessment, ...]`, `validity: ManuscriptValidityReadback`, `matches: tuple[FindingImpactMatch, ...]`. |

Reuse existing domain `AuditFinding`/`ImpactAssessment` and B25 DTOs without new
fields or changed payload encoding. Their complete definitions are in the linked
domain/Application files in §1. Domain records are allowed; ORM instances are not.
`assessment_id` is null iff FINDING_TARGET; otherwise it names a returned
assessment whose exact target matches. Every match has at least one occurrence.
No match emits a state inferred from `impact_kind`.

Closed target mapping (left side is existing `GovernanceTargetType.value`):

| Existing kind | B25 `AuditNodeRef.kind` |
| --- | --- |
| experiment_spec_version | ExperimentSpecVersion |
| dataset_snapshot | DatasetSnapshot |
| artifact_version | ArtifactVersion |
| run | Run |
| metric_definition_version | MetricDefinitionVersion |
| measurement | Measurement |
| statistical_result | StatisticalResult |
| claim_version | ClaimVersion |

Keep existing lowercase domain/readback enums: Finding status `open/confirmed/dismissed/resolved`,
severity `info/minor/major/critical`; assessment conclusion
`no_impact/stale/invalid/requires_review/unknown`; impact kind
`direct/downstream/stale/invalid/requires_review`; governance state
`not_assessed/unaffected/stale/invalid/requires_review/unknown`. Storage is already
UPPER_SNAKE_CASE after [0017](../../migrations/versions/0017_persisted_canonical_enum_normalization.py);
the existing `PersistedCanonicalEnum` adapter in
[models.py](../../src/researchbase/persistence/models.py) converts between these
representations. Use it for typed predicates/results; raw SQL must use stored
uppercase values. No enum migration or hash-payload case change. B25 aggregate
remains `VALID/STALE/INVALID`; new match-basis literals are uppercase and transient.

Fixed bounds: 10,000 per SELECT, distinct graph nodes, returned assessments, total
assessment targets, matches, and total returned occurrence paths; path depth 256
nodes, inclusive of manuscript. Count paths in embedded validity and matches
together, even if duplicated in the response. Reuse B25's retained-predecessor
depth guards. Apply row ceiling+1 before hydration; enforce aggregate ceilings
while collecting, not after unbounded allocation. Overflow is closure failure,
never truncation, pagination or a caller-tunable limit.

Sort assessments by `(created_at, str(id))`, targets by `(target_type.value,
str(target_id))`, matches by `(basis, str(assessment_id) or '', target.kind,
str(target.id))`. Preserve B25's occurrence ordering by placement kind/UUID and
ordered node kind/UUID pairs. Deduplicate only identical occurrences within one
match; retain different placements and different assessment IDs. Repeated reads
of unchanged snapshot-visible facts differ only in evaluation time. Hashes retain
lowercase 64-hex format (nullable where already allowed); times are aware UTC.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

**Zero B26 DDL.** This abbreviated inventory describes existing
[0015](../../migrations/versions/0015_governance_audit.py), with enum checks
normalized/extended by 0017 and reflected in current models, not new SQL to apply:

```sql
-- audit_findings: id UUID PK; project_id UUID FK projects(id) RESTRICT;
-- target_type VARCHAR(64), target_id UUID NOT NULL; target_content_hash CHAR(64) NULL;
-- severity VARCHAR(16), status VARCHAR(20), row_version INTEGER NOT NULL;
-- ck_audit_findings_severity; ck_audit_findings_status;
-- ck_audit_findings_target_type (eight stored uppercase kinds in §11.3);
-- ix_audit_findings_project; ix_audit_findings_target.
-- impact_assessments: id UUID PK; project_id UUID FK projects(id) RESTRICT;
-- audit_finding_id UUID NULL FK audit_findings(id) RESTRICT;
-- assessment_payload JSONB, conclusion VARCHAR(32), content_hash CHAR(64) NOT NULL;
-- ck_impact_assessments_conclusion; ix_impact_assessments_finding.
-- impact_targets: impact_assessment_id UUID FK impact_assessments(id) RESTRICT;
-- target_type VARCHAR(64), target_id UUID NOT NULL; target_content_hash CHAR(64) NULL;
-- impact_kind VARCHAR(32) NOT NULL;
-- impact_targets_pkey (impact_assessment_id,target_type,target_id);
-- ck_impact_targets_kind; ix_impact_targets_target.
-- ck_impact_targets_target_type (same eight kinds).
-- correction_records: id UUID PK; project_id UUID FK projects(id) RESTRICT;
-- target_type VARCHAR(64), target_id UUID NOT NULL; target_content_hash CHAR(64) NULL;
-- correction_type VARCHAR(32), corrected_assertion JSONB, reason TEXT,
-- content_hash CHAR(64) NOT NULL; ck_correction_records_type;
-- ix_correction_records_target.
-- ck_correction_records_target_type (same eight kinds).
-- Governance attribution: created_by UUID FK actors(id) RESTRICT,
-- created_at TIMESTAMPTZ NOT NULL. No ON DELETE CASCADE.
```

Existing immutability/history guards stay installed. No propagation table,
materialized view, outbox, queue, generic reference registry, schema trigger or
stored result is admitted. In particular do not add an immediate trigger that
requires an assessment parent/target set to be complete before child insertion.
If a later owning contract authorizes new multirow writes, completeness follows
0042's `DEFERRABLE INITIALLY DEFERRED` constraint-trigger pattern (e.g.
`pr215_complete_decision`, `pr215_complete_conclusion`, `pr215_complete_review`),
with its own named guards and authorization. None is needed for this read slice.

### 12.2 Exact lock order and transactions

| Entry point | Required sequence |
| --- | --- |
| `get_finding_manuscript_impact` | Validate closed input/principal without DB I/O → fresh UoW and existing manuscript error normalization → first SQL `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY` using `prepare_read(bounded=True)` → enable existing snapshot-safe revision reads → nonlocking Project authorization → plain scoped Finding header and Publication/manuscript lookup → verified Finding/full linked assessments → same-UoW B25 validity build → exact matching and bounds → fresh DB-time/credential authorization → return. |
| B26 commands | None; no table inventory, advisory key, row-lock order, receipt, commit effect or retry loop exists to implement. |

The query must never call `lock_snapshot`, `prepare_write`, `FOR SHARE`,
`FOR UPDATE`, `pg_advisory_*` or another public Application reader. Prepare the
snapshot once, not inside the extracted builder. Every repository SELECT uses
the same Session; all DTO assembly completes before leaving the UoW.

For comparison, existing snapshot-consistent writers in decision/novelty
repositories establish READ COMMITTED on connection checkout, execute their
literal `LOCK TABLE ... IN SHARE MODE` as the **FIRST statement**, then timeout
settings, command-specific advisory/row locks, durable rereads and fresh
authorization before effects. A preliminary SELECT or `SET LOCAL` before SHARE
would break that write protocol. Do not transfer it to this read path or alter
those commands in B26. Any later automation needs its owning contract to pin its
complete table inventory and exact per-command order before implementation.

### 12.3 Ordered build steps and module paths

1. Add proposed `src/researchbase/application/finding_impact.py` with §11.3 DTOs
   and the query service. Keep domain independent of adapters, ORM and SQL.
2. In existing `src/researchbase/application/manuscript_validity.py`, extract a
   same-UoW validity builder from `_query`/`_Collector`. Preserve public signatures,
   DTOs, error behavior and B25 bounds. The outer service owns transaction setup
   and final authorization; the builder neither opens a UoW nor prepares one.
3. Extend `src/researchbase/application/ports.py` and
   `src/researchbase/persistence/governance_repository.py` only as needed for a
   plain `(project_id,finding_id)` header lookup before full hydration. Return
   NOT_FOUND for foreign roots. Reuse existing verified Finding/assessment
   loaders, bounded on the B26 Session; check the full linked set, project and
   stored bindings before exposing it. Do not reuse a loader that silently drops
   a missing selected row or permits a malformed persisted enum to escape raw.
4. Compose B25 and governance in one UoW in the new service, using the existing
   factory/credentials/ArtifactStore injection pattern. Normalize nested saved
   corruption at this new boundary. Match typed identities, preserve historical
   paths and apply aggregate bounds. Existing
   `src/researchbase/persistence/uow.py` and manuscript `prepare_read` remain the
   transaction owners; add no new persistence mechanism or global listener.
5. Add §12.4 tests and run focused checks. No API/CLI route, migration, domain
   schema, dependency, architecture rewrite or unrelated refactor is part of
   this build. Record exact evidence and stop after the authorized slice.

### 12.4 Test artifacts and required cases

New filenames below are planned; existing filenames are regression targets.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b26_finding_impact_contract.py` (new) | Closed/frozen DTOs; reject string UUIDs/extra fields; all eight target mappings; assessment-ID XOR; stable sorting; no latest-wins or impact-kind state inference; 10,000 and ceiling+1, combined path budget and depth 256/257. Pin §11.2 mappings against both adapter maps. |
| `tests/architecture/test_b26_boundaries.py` (new) | Application→ports, no ORM leakage or nested public UoWs; no migrations/DDL/runtime dependencies/new target enums; no write or locking helper on the query path. |
| `tests/integration/phase2/test_b26_finding_impact.py` (new) | Exact Finding target and linked assessment matches through experimental and literature-bound Claim→Conclusion→manuscript paths; repeated placements; artifact/citation and retained predecessor reachability without support inference; all Finding statuses and assessment conclusions; multiple conflicting assessments; unlinked/other Findings affect overall validity without entering selected assessment set; corrections cannot clear invalidity; no-assessment/zero-match success. Source retraction/dispute changes B25 validity without creating Finding/assessment rows. |
| Same integration file | Missing/foreign roots, DRAFT, denied/expired credentials; missing saved targets, foreign child project, target hash and assessment hash corruption, invalid enums, incomplete target sets; CAS/closure failures; fail closed at every bound. Snapshot-visible output hashes/bytes/pointers and row/event counts unchanged after success and failure. |
| `tests/integration/phase2/test_b26_finding_impact_races.py` (new) | Separate-connection barriers: Finding dismissal, new assessment/correction, source retraction and evidence dispute commit during query; complete old snapshot then complete new snapshot. Observe first SQL and absence of explicit locks/DML; concurrent INSERT/UPDATE can finish while read is open. Pause before final authorization across credential expiry and deny return. |

Required existing regressions after authorization:
`tests/unit`, `tests/architecture`,
`tests/integration/test_pr14_governance_integration.py`,
`tests/integration/test_pr14_schema.py`, and the three
`tests/integration/phase2/test_b25_manuscript_{validity,audit,read_races}.py` files.
Run `uv run --frozen ruff format --check .`, `uv run --frozen ruff check .`,
`uv run --frozen pyright`, `git diff --check`, and focused pytest selections on
real PostgreSQL 18.x. Do not substitute SQLite or claim a skipped test passed.

### 12.5 Not in this slice

Project-wide impact discovery; automatic Findings/ImpactAssessments or copied
downstream target rows; SourceVersion/Conclusion/Manuscript governance target
expansion; novelty/B18 propagation; Issue disposition; Decision/Approval/grant
staleness automation; repair, withdrawal, re-review or readiness transitions;
prepared-package propagation; new submission/external effects; adapters, queues,
workers, caches, event buses and new persistence. Existing owning command guards
still apply independently; a successful read grants no permission to act.

## 13. Open questions for the owner — override register

| Owner decision needed | Draft's pinned recommendation |
| --- | --- |
| What is the first B26 slice? | Approve the one exact Finding/manuscript explanation query, preserving B25's validity rules. Global discovery needs a separate bounded contract. |
| Does Phase 2 require automatic Finding/assessment recording on retraction? | Do not infer automation from the conceptual F1 chain. Existing validity must propagate immediately through owner readers. Obtain an explicit owning-contract disposition for any required durable write bridge before authorizing it; this draft does not claim full F1/exit acceptance. |
| Should novelty be included? | No; B18 owns that parallel slice and its eventual compatibility requirements. |

These recommendations make the proposal concrete for review. They are not owner
approval, an architecture amendment or implementation authorization. Any override
changes the contract before implementation, not silently during coding.

## 14. Documentation verification note

Documentation-only verification on 2026-10-18. All commands below used
`UV_CACHE_DIR=/private/tmp/rb-lane22-uv`. Initial `uv run --frozen` attempts for the
same checks exited 2 before execution because dependency download DNS was denied.
Copying the existing local uv cache into that temporary cache allowed
`uv sync --frozen --offline` to install the locked environment (exit 0).

```text
uv run --frozen --offline ruff format --check .
  639 files already formatted; exit 0.
uv run --frozen --offline ruff check .
  All checks passed; exit 0.
uv run --frozen --offline pyright
  0 errors, 0 warnings, 0 informations; exit 0.

uv run --frozen --offline pytest tests/unit tests/architecture -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  5105 passed, 4 failed, 12 errors, 8 warnings in 73.88s; exit 1.
  Four tests in tests/unit/test_hg1_runner.py fail at Unix socket bind:
  PermissionError: Operation not permitted. Twelve setup errors in
  tests/architecture/test_pr2_19_boundaries.py require RB_TEST_ADMIN_URL.
  This selection did not pass.

uv run --frozen --offline pytest tests/integration/test_pr14_schema.py tests/integration/test_pr14_governance_integration.py tests/integration/phase2/test_b25_manuscript_validity.py tests/integration/phase2/test_b25_manuscript_audit.py tests/integration/phase2/test_b25_manuscript_read_races.py -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
  13 skipped, 92 setup errors in 1.57s; exit 1. Zero passed.
  DATABASE_URL absent: 13 legacy skips. RB_TEST_ADMIN_URL absent: 92 B25 errors.
  Separate psycopg probes to localhost:5432 and /private/tmp/.s.PGSQL.5432
  both failed with Operation not permitted. PostgreSQL execution is blocked;
  no PostgreSQL version, constraint or runtime PASS is claimed.
```

Eight documented error mappings were compared programmatically with current HTTP
and CLI maps; all matched. All 27 local Markdown link references resolved.
`git diff --check` and `git diff --no-index --check /dev/null
docs/proposals/B26_Finding_Impact_Propagation_Contract_DRAFT.md` both exited 0
with no whitespace findings. `git status --short` showed only this added proposal.
No implementation, migration, full-suite result or gate acceptance is claimed.
The outer loop owns the subsequent whole-suite check.
