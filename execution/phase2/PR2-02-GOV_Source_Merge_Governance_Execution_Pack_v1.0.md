# PR2-02-GOV — Source Merge Governance Bridge: design / execution pack v1.0

**Status:** Design subject. Implementation starts only after committed independent design review returns P0=0, P1=0, readiness YES. **Role:** Required prerequisite to PR2-02; no permanent PR number is consumed. **Migration:** 0021_source_merge_governance_bridge, parent 0020_literature_source_identity.

## Authority and purpose

Precedence: System Architecture/frozen Phase 1 → Addendum A18-A22 → Phase 2 R2 contracts 14-17 and R3/R4 corrections 18-19 in their subjects → ADR-0010 → accepted PR2-00/PR2-01 → this pack. Repository numbering reserves PR2-02 for source lineage, so this is prerequisite subject PR2-02-GOV.

Persist a directed global source-merge proposal and require approval from an effective HUMAN OWNER in every project linked to either source. The bridge never merges sources. PR2-02 depends on the accepted bridge. PR2-00 and PR2-01, including 0019 and 0020, are accepted prerequisites.

## Scope

IN_SCOPE: typed proposal identity; frozen affected-project set; identifier and source-version basis; per-project Human Owner approval/rejection/revocation; lifecycle, supersession, staleness and idempotency; Application/UoW, PostgreSQL persistence/migration, minimal HTTP/CLI, tests/evidence.

OUT_OF_SCOPE: source merge effects; identifier mutation/resolution; SourceVersion creation; providers, search, evidence, claims, manuscripts; generic approval/workflow changes; Agent Runtime; PR2-03+.

## Schema and migration 0021

Add only bridge tables, constraints, indexes and local triggers. Application UUIDs, TIMESTAMPTZ, RESTRICT canonical FKs, persisted UPPER_SNAKE_CASE enums. Do not alter Phase 1, migrations 0019/0020, their hashes or lifecycle.

1. source_merge_proposals: id UUID PK; deployment_id TEXT; source_a_id/source_b_id/canonical_survivor_id UUID FKs to literature_sources; proposed_by_actor_id UUID FK actors; proposed_in_project_id UUID FK projects; rationale TEXT; basis_contract_version VARCHAR(40); identifier_basis_hash/source_version_basis_hash/proposal_basis_hash CHAR(64); hash_scheme VARCHAR(32); request_id UUID; request_hash CHAR(64); result_dto_version SMALLINT; result_dto JSONB; created_at TIMESTAMPTZ; supersedes_proposal_id UUID NULL self-FK. CHECK A≠B, survivor∈{A,B}, source IDs stored in canonical UUID order, nonblank rationale, contract/hash scheme literals, lowercase 64-hex digests and positive result version. UNIQUE(deployment_id,proposed_in_project_id,proposed_by_actor_id,request_id). Material columns cannot update/delete. result_dto is a versioned replay projection only, not canonical truth.
2. source_merge_proposal_projects: proposal_id/project_id FKs, nullable source_a_link_id/source_b_link_id FKs to literature_source_project_links, captured_at and link_basis_hash. PK(proposal_id,project_id); at least one link FK nonnull; deferred trigger verifies each link names the proposal's corresponding source and this project. The set is nonempty and sealed on SUBMITTED; no later insert/update/delete.
3. source_merge_proposal_identifier_basis: proposal/source/identifier IDs (concrete FKs), identifier_type, normalized_value, normalization_version, verification_status, is_primary, binding_basis_artifact_version_id, supersedes_rejected_identifier_id, verification_basis_artifact_version_id, verified_by, verified_at, captured row_version. One immutable row for every identifier row on A/B including REJECTED history; UNIQUE(proposal_id,identifier_id); capture values equal locked durable rows.
4. source_merge_proposal_source_basis: exactly two rows per proposal, one per source, with source_id FK, nullable current_version_id/hash, version_state_hash and captured_at. At 0021 SourceVersion does not exist, so current ID/hash are NULL and a CHECK enforces that. 0022 replaces this check with an ID/hash pair check and adds the concrete same-parent FK to source_versions. It marks nonterminal 0021 proposals stale where empty basis no longer matches before enabling new proposal submission. No polymorphic reference.
5. source_merge_proposal_evidence: proposal_id and artifact_version_id FKs, captured content_hash, UNIQUE(proposal_id,artifact_version_id); each referenced artifact is FROZEN at proposal submission. Rows are immutable and included in proposal basis.
6. source_merge_approvals: id UUID PK; proposal/project FKs; decision APPROVE/REJECT; approver_actor_id FK actors; membership_id FK project_memberships; owner_role_assignment_id FK project_role_assignments; deployment_id, credential_id, trusted subject kind/value and principal_verified_at; decision_basis_hash CHAR(64); request_id/request_hash; result_dto_version SMALLINT; result_dto JSONB; decided_at TIMESTAMPTZ. UNIQUE(proposal_id,project_id), UNIQUE(deployment_id,project_id,approver_actor_id,request_id); positive result version. Deferred guard requires project in frozen set, exact proposal basis hash, matching actor/project membership and role, and HUMAN actor. Decision is immutable. result_dto is a replay projection only.
7. source_merge_governance_events: append-only id/proposal/optional approval/project/actor FKs, kind, occurred_at, reason, deployment_id, request_id, request_hash and basis_hash. Kinds are SUBMITTED, APPROVAL_REVOKED, PROPOSAL_SUPERSEDED, PROPOSAL_STALE, PROPOSAL_CONSUMED. UNIQUE(deployment_id,actor_id,event_kind,request_id). CHECKs/deferred guards enforce required fields, matching basis and allowed transitions. Approval rows are the immutable APPROVE/REJECT decision facts.

This narrow schema is the explicit architecture admission in ADR-0010 and the V5 decision. No JSON field is semantic truth. No other canonical table or generic target is in scope. Downgrade drops only these tables when all are empty; otherwise it raises an explicit data-preservation error before DDL.

## Effective links and visibility

Migration 0020 links are immutable and have no inactive/deleted status. Effective link means every extant literature_source_project_links row for A or B at locked capture. Do not filter by membership, project archive, ACTIVE/RETIRED or merge state; these do not erase durable association. A project without valid approval blocks merge. Deduplicate and sort canonical lowercase UUIDs; persist the set.

Proposal reads and decisions require current membership and a source link in the supplied project context. Do not disclose peer project IDs or peer approvers. Return only caller-project approval and aggregate counts. Source public identity metadata remains public.

## Basis and hash

Hash source-merge-basis-v1 using SHA-256(canonical-json-v1(payload).UTF8), scheme sha256-cjson-v1. All keys are required, nullable values explicit null, UUIDs lowercase canonical, enums uppercase, authored strings NFC; no ORM serialization. Exact payload:

~~~json
{"type":"SourceMergeProposalBasis","material_version":1,"source_a":{"type":"LiteratureSource","id":"<uuid>"},"source_b":{"type":"LiteratureSource","id":"<uuid>"},"canonical_survivor":{"type":"LiteratureSource","id":"<uuid>"},"affected_project_ids":["<uuid>"],"effective_project_links":[{"source_id":"<uuid>","project_id":"<uuid>","link_id":"<uuid>"}],"identifier_state":[{"identifier_id":"<uuid>","source_id":"<uuid>","identifier_type":"<enum>","normalized_value":"<string>","normalization_version":"<string>","verification_status":"<enum>","is_primary":false,"binding_basis_artifact_version_id":"<uuid|null>","supersedes_rejected_identifier_id":"<uuid|null>","verification_basis_artifact_version_id":"<uuid|null>","verified_by":"<uuid|null>","verified_at":"<instant|null>","row_version":1}],"source_version_state":[{"source_id":"<uuid>","current_version":{"type":"SourceVersion","id":"<uuid>","content_hash":"<digest>","version_kind":"<enum>","lifecycle_status":"<enum|null>"}}],"rationale":"<NFC string>","evidence_artifacts":[{"type":"ArtifactVersion","id":"<uuid>","content_hash":"<digest>"}]}
~~~

Sort A/B by UUID and keep both; survivor is separate, so opposite directions hash differently. affected_project_ids is unique and UUID-sorted. effective_project_links sorts by (source_id,project_id,link_id), capturing both link rows where both sources are linked. Identifier rows sort by (type, normalized value, ID), including rejected history. Exactly two source-version rows sort by source UUID. current_version is null when no frozen current version exists; otherwise it contains the exact ID/hash plus kind/status. Evidence refs sort by (ID, hash), duplicates rejected. Rationale is nonblank NFC with meaningful whitespace preserved. Times and actor IDs are excluded; authority provenance is separate. Provide golden and negative vectors for ordering, nulls, direction, duplicate refs, and identifier/version changes.

At 0021 both source-version sets are empty. After 0022, include each source's current SourceVersion ID/hash and kind/status; a corrected or retracted version changes the current ref. Any source, link set, identifier, or current-version state change invalidates approvals. Material change creates a new proposal. Golden vectors include representative references and expected SHA-256 digests.

## Lifecycle, authority and concurrency

Lifecycle derives from immutable material, approval rows and append-only events:
- creation → PENDING_APPROVAL
- PENDING_APPROVAL → APPROVED only with effective APPROVE from every project
- PENDING_APPROVAL → REJECTED on any project REJECT
- PENDING_APPROVAL/APPROVED → SUPERSEDED by explicit successor
- PENDING_APPROVAL/APPROVED → STALE on basis mismatch, approval revocation, or lost approving authority
- APPROVED → CONSUMED only in later PR2-02 merge transaction

REJECTED, SUPERSEDED, STALE, CONSUMED are terminal. APPROVED is historical completeness; merge revalidates. Rejection requires a new proposal. Approval may be revoked before consumption only by an effective HUMAN OWNER of that project; append event, preserve decision, transition proposal to STALE, and require a new proposal. A stale outcome commits its event/lifecycle result before returning the conflict response; it is not raised inside a transaction that would roll the event back.

Authenticated OWNER/RESEARCHER in a project linked to at least one source may propose; proposer may be human or agent. Every affected project decides once. Only authenticated HUMAN OWNER of that exact project may approve, reject or revoke. Proposal submission locks source rows A/B in sorted UUID order (the PR2-01 link writer takes the same source lock), reads the link set and identifiers, locks version rows if present, then rereads and freezes the full basis in SERIALIZABLE isolation. Approval/rejection locks proposal then that project's authority/decision rows, rereads and recomputes the complete basis; stale basis is denied and cannot receive a new approval. Obtain fresh PostgreSQL clock_timestamp() after locks, then validate active membership, effective OWNER interval, actor not retired/type HUMAN, verified principal and current credential with existing verifier. Persist actor, membership, role assignment, credential ID/trusted subject, principal_verified_at and decision time. Recheck authority/credentials at merge; a lost/expired/revoked credential or Owner role makes approval ineffective.

PR2-02 merge lock order: source rows by UUID; project-link set/rows by project UUID; proposal; approvals by project UUID; identifier rows by UUID; version rows by UUID. After locks reread state, recompute affected project IDs and exact link IDs/full basis, get fresh time and validate approvals. Repeat authorization after any later blocking wait. Any new link row, even if the project was already affected through the other source, wrong direction, changed basis, missing/rejected/revoked approval, or lost Human Owner authority denies without merge writes. Bridge does no merge.

## Application, replay and errors

One synchronous command equals one UoW transaction:
- propose_source_merge(principal, project_id, source_a_id, source_b_id, survivor_id, rationale, evidence_artifact_ids, request_id)
- approve_source_merge(principal, project_id, proposal_id, request_id)
- reject_source_merge(principal, project_id, proposal_id, reason, request_id)
- revoke_source_merge_approval(principal, project_id, proposal_id, reason, request_id)
- supersede_source_merge_proposal(principal, project_id, proposal_id, replacement_inputs, request_id)
- project-scoped get_source_merge_proposal and get_source_merge_approval_status.

Replay scope is deployment/project/actor/command/request UUID; exact hash returns saved IDs/DTO after authentication and current project read entitlement, without repeating mutation. Changed hash is IDEMPOTENCY_CONFLICT 409. Advisory lock plus uniqueness serializes duplicates. Approval/rejection races on proposal+project allow one result. Revoke/consume race on proposal: consumption first forbids revoke; revoke first forbids consume.

Each request hash is SHA-256(canonical-json-v1(payload).UTF8), scheme sha256-cjson-v1, omitting request ID and transport fields. Payloads are closed typed objects:
~~~json
{"type":"PROPOSE_SOURCE_MERGE","material_version":1,"project_id":"<uuid>","source_a_id":"<uuid>","source_b_id":"<uuid>","canonical_survivor_id":"<uuid>","rationale":"<NFC string>","evidence_artifact_refs":[{"type":"ArtifactVersion","id":"<uuid>","content_hash":"<digest>"}]}
{"type":"APPROVE_SOURCE_MERGE","material_version":1,"project_id":"<uuid>","proposal_id":"<uuid>","proposal_basis_hash":"<digest>","decision":"APPROVE"}
{"type":"REJECT_SOURCE_MERGE","material_version":1,"project_id":"<uuid>","proposal_id":"<uuid>","proposal_basis_hash":"<digest>","decision":"REJECT","reason":"<NFC string>"}
{"type":"REVOKE_SOURCE_MERGE_APPROVAL","material_version":1,"project_id":"<uuid>","proposal_id":"<uuid>","approval_id":"<uuid>","proposal_basis_hash":"<digest>","reason":"<NFC string>"}
{"type":"SUPERSEDE_SOURCE_MERGE_PROPOSAL","material_version":1,"project_id":"<uuid>","prior_proposal_id":"<uuid>","replacement_proposal_request_hash":"<digest>"}
~~~
For proposal payload, source IDs are stored sorted and direction is bound by the separate survivor ID. Evidence refs sort by ID/hash and duplicates fail. Same request key/hash returns the original record; same key/different hash conflicts. No command replays by re-running proposal calculation or an effect.

| Condition | Error | Transaction |
|---|---|---|
| Missing principal/live credential | AUTHENTICATION_REQUIRED 401 | rollback |
| Hidden proposal/no project read link | SOURCE_NOT_FOUND 404 | no disclosure |
| Agent/non-Owner/inactive Owner | SOURCE_MERGE_APPROVAL_FORBIDDEN 403 | rollback |
| Missing approval | SOURCE_MERGE_APPROVAL_MISSING 409 | no merge |
| Any explicit rejection | SOURCE_MERGE_REJECTED 409 | rejection event commits atomically |
| Changed link/source/identifier/version basis or authority | SOURCE_MERGE_PROPOSAL_STALE 409 | stale event only; no merge |
| Changed hash under replay key | IDEMPOTENCY_CONFLICT 409 | rollback |
| Consumed/terminal proposal | SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED or terminal conflict 409 | no writes |
| Invalid/already merged pair | SOURCE_NOT_MERGEABLE, or existing SOURCE_IDENTITY_CONFLICT only if identical | rollback |
| Retry exhaustion | CONCURRENT_MODIFICATION 409 | rollback |

No path partially writes approval or merge state.

## Architecture and adapters

Write path: Caller → Application → Repository/UoW → PostgreSQL. Domain imports no SQLAlchemy/FastAPI/Typer. HTTP/CLI call identical typed Application surfaces with VerifiedPrincipal; actor headers are not authority. Minimal routes support create/get/approve/reject/revoke/status. CLI: researchbase literature merge-proposal create|show|approve|reject|revoke|supersede --project-id; writes require UUID request IDs and existing error mapping.

Acceptance, Independence, Planted-Truth and Reading contracts do not apply to administrative identity merge approval. Human-Authority applies directly. Honest-Failure requires fail-closed denial. Deterministic facts precede authority.

## Required acceptance evidence

PostgreSQL 18.x required for migrations, locks, constraints, concurrency and temporal tests. Each invariant maps to evidence:

| Invariant | Cases |
|---|---|
| Directed proposal/hash | survivor directions differ; golden order/null/set vectors; changed links, identifiers, versions, rationale/evidence changes hash |
| Project set | one project linked to both counted once; multi-project sorted; peer IDs never disclosed |
| Identifier/version state | rejected history captured; status/proof/primary change stales; 0021 empty versions; 0022 typed same-parent refs; pre-0022 proposal stale |
| Approvals | one/multiple projects; missing one deny; reject terminal; duplicate decision deny; Human Owner allowed; Agent/non-Human/non-Owner denied |
| Time/authority | inactive/expired credential denied; lost Owner/credential before merge stales; held lock crossing expiry denies at fresh clock_timestamp() |
| Races | new link after approvals stales; concurrent approve/reject one winner; same-key duplicate one result; revoke/consume one winner |
| History/replay | rejection/revoke/supersession/consumption auditable; exact replay no second effect; changed hash conflict; rollback atomic |
| Migration | fresh 0020→0021 and frozen 0018→0019→0020→0021; unique head; owned table inventory; old catalogs unchanged; empty downgrade succeeds; populated downgrade refuses |
| Architecture/regression | import boundaries; PR2-00/01 regressions; Phase 1 catalog/hash non-drift |
| Tool/evidence | full suite counts, Ruff, Pyright, raw format and baseline delta, changed Python files clean, git diff --check, reproducible PostgreSQL instructions |

Evidence path artifacts/pr_evidence/PR2-02-GOV/. Include starting/implementation/evidence subjects, migration, files, exact commands/results/counts, PostgreSQL version/startup/URL pattern/test DB cleanup, temporal/lock proof, formatter baseline/current/new sets, Phase 1 non-drift, PR2-00/01 regression and reviewer result. Evidence-only child follows implementation and cannot certify itself.

Run focused unit/PostgreSQL, migration and architecture checks; full uv run pytest -o addopts=''; uv run ruff check .; uv run pyright; raw uv run ruff format --check .; changed-file format checks and FORMAT-BASELINE-01 delta; Alembic history/head; git diff --check. Report raw formatter failures honestly; gate passes only with no new failures and all changed Python files clean.

## Review gate and next boundary

Commit only ADR-0010 and this pack, ensure clean tree, then use one fresh review-only context. Reviewer receives exact pack SHA, ADR, authoritative architecture, accepted PR2-00/01, migration history and Phase 1 baseline; inspect committed diff and independently assess scope/schema/hash/authority/races. Return P0/P1/P2 and READY_FOR_GOVERNANCE_BRIDGE_IMPLEMENTATION. Pass requires P0=0, P1=0, readiness YES. One narrow non-policy remediation and a new reviewer are allowed; new policy P2 stops.

On design pass V5 authorizes direct main-context implementation. Commit implementation, complete checks/evidence, commit evidence child, then one fresh implementation reviewer. Bridge acceptance is prerequisite to PR2-02 pack freeze. PR2-02 migration 0022 adds SourceVersion lineage and concrete basis FKs; it consumes this bridge, not redesigns it. Stop for P0, P1 after remediation, new P2 needing judgment, Phase 1 drift, PR2-00 temporal P2 reopen, migration conflict, design contradiction, unavailable verification or corruption.
