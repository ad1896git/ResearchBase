# Phase 2 Design R3 — targeted remediation v1.0

**Status:** proposed normative design contract for independent review; design only. **Authority:** Addendum A19. This document changes only the named R2 clauses. No Phase 2 implementation, migration, PR2-00 or PR2-01 is authorized. Phase 1 scientific semantics and `phase1-final-v4` are unchanged.

## 1. DecisionRecord basis canonicalization (P1-03)

`DecisionRecord.basis` is a finite, nonempty **set of typed exact frozen references**, not an ordered list. Its members are the six concrete types in R2 hash contract §Review, decision, approval, and revision. The same concrete target `(type,id)` may occur only once; a repeated target with the same or different claimed content hash is `DECISION_BASIS_DUPLICATE`, before hashing. Each referenced digest must equal the target's independently verified frozen content hash. Null target, null id, null digest, null array member, and any unlisted target type are invalid. The complete basis must also satisfy its decision-type-specific membership rules; a hash never substitutes for those checks.

For `material_version=1`, sort the set by `(target.type,target.id,target.content_hash)`, comparing NFC type text by Unicode code point and canonical lowercase hyphenated UUID/digest text lexically. The type names are the exact case-sensitive R2 literals; IDs are UUID canonical text and hashes are lowercase 64-hex text. The Application derives zero-based contiguous canonical array position from this sorted set. The binding payload is exactly `{"type":"DecisionRecordBasisSet","material_version":1,"basis":[{"target":R(T),"ordinal":0},...]}` where `ordinal` is this **derived position**. Persisted `decision_basis_* .ordinal` values are storage coordinates only and MUST NOT enter the hash or decide the array order. A read reconstructs the set from all typed basis tables, checks uniqueness and frozen refs, derives positions again, and recomputes the hash. Callers cannot supply canonical order. This targeted rule supersedes the R2 basis paragraph and the common R2 ordinal rule for this basis only; the existing one-member R2 golden vector remains valid.

Storage keeps concrete basis FK tables and their `(decision_id,target_id)` uniqueness. Existing `(decision_id,ordinal)` uniqueness may remain as a storage-integrity check, but contiguity and order of those persisted ordinals have no hash meaning. No material version bump is needed because R2 was design only and no Phase 2 DecisionRecord was persisted. A future change to this algorithm requires a new material version.

## 2. Single-use legacy enrollment challenge (P1-05)

PR2-00's legacy actor enrollment has a durable `actor_enrollment_challenges` record. It is a bounded eighth PR2-00 table, in the separately authorized `0019` design scope: `id UUID PK` (challenge identifier), `deployment_id TEXT`, `actor_id UUID NOT NULL FK actors`, `subject_kind`, `subject_value`, `subject_credential_id`, `operator_credential_id`, `nonce_digest CHAR(64)`, `proof_method`, `issued_at TIMESTAMPTZ`, `expires_at TIMESTAMPTZ`, `status ISSUED|CONSUMED|EXPIRED`, `consumed_at TIMESTAMPTZ NULL`, `result_binding_id UUID NULL FK actor_subject_bindings`, `request_id UUID`, and `row_version INT`. Every required text is nonblank; `expires_at>issued_at`; digest is lowercase 64-hex; status CONSUMED iff both consumption fields exist, and the result binding points to the same actor/deployment/subject. `(deployment_id,nonce_digest)` and `(deployment_id,request_id)` are unique permanently. No DELETE, no reset to ISSUED, and no UPDATE of identity, challenge, or issuance fields. A challenge is bound at issuance to the exact actor, deployment, subject, credential and operator; the signed immutable audit attestation cites challenge ID and nonce digest. The nonce secret is never persisted.

The trusted enrollment adapter issues a fresh unpredictable nonce and the Application inserts the challenge in one SERIALIZABLE transaction before delivering it. It checks operator authority and target actor eligibility at issuance. `bind_legacy_actor_subject` receives `challenge_id`, a verified live challenge response and the signed attestation. Under the same deployment lock and a row lock on the challenge it verifies the exact challenge/attestation/principal tuple, trusted proof, `status=ISSUED`, `DB transaction time < expires_at`, actor eligibility and subject uniqueness. One SERIALIZABLE transaction inserts the binding and binding event, sets challenge CONSUMED with `consumed_at` and `result_binding_id`, and commits them together. A deferred trigger verifies the challenge's result binding/event and prohibits a committed enrollment binding without its consumed challenge; the binding has a nonnull unique `enrollment_challenge_id` FK for LEGACY_ATTESTATION proof. The challenge is unique per resulting binding and each binding cites at most one challenge. Concurrent attempts serialize on the challenge row and unique keys; only one can commit. A failed or rolled-back enrollment creates no binding or consumption. At or after expiry, even if an expiry sweeper has not changed status, consumption fails `ENROLLMENT_CHALLENGE_EXPIRED`; a sweeper may monotonically mark ISSUED→EXPIRED for audit. All mismatches, missing challenge/audit proof, unverifiable live proof or replay of CONSUMED/EXPIRED fail closed without a new binding. Revoking the resulting binding leaves challenge CONSUMED forever. A new ceremony requires a new challenge. Bootstrap and post-bootstrap provisioning remain separate ceremonies.

## 3. Effective OWNER across credential expiry (P1-06)

At trusted DB time `t`, `role_owner(actor,project,t)` means a non-retired actor, an ACTIVE membership interval at `t`, and an OWNER role interval `[effective_from,effective_until)` covering `t`. `credential_valid(actor,t)` means at least one ACTIVE subject binding for that actor whose **actual trusted authentication credential** is valid at `t`: its issuer/adapter-valid `not_before <= t < not_after`, and it is not revoked, disabled or otherwise rejected by the trusted verifier at `t`. The binding row alone is insufficient. An OS principal has a deployment-defined current validity/revocation check; mTLS uses checked certificate validity and revocation. If validity cannot be established, it is false. Define `effective_owner(actor,project,t) = role_owner(actor,project,t) AND credential_valid(actor,t)`. A request additionally requires a live verified principal for that actor at command time. No cached successful authentication crosses a credential expiry boundary.

Before the credential's expiry instant an open OWNER role can satisfy `effective_owner` if all other predicates hold. At `t = not_after` and later it cannot, even when membership, role and binding rows remain open. Authorization and the operational OWNER availability query evaluate the trusted credential state and DB time on **every** command/read; they deny OWNER authority and return `OWNER_CREDENTIAL_UNAVAILABLE` when no effective OWNER exists. An expiry requires no DB write, event or role-interval rewrite to take effect. Credential rotation may append a new authenticated binding and revoke an old one without falsifying the role history. The role's interval records governance assignment, never credential validity.

The **structural invariant** enforced by the existing project lock/deferred guard is contiguous role/membership OWNER coverage through the present and an unbounded role path, considering retirement and binding revocation known to the database. The **operational invariant** is that at least one `effective_owner` is currently available; this cannot be guaranteed forever by a database trigger because credentials can expire externally without a write. Every command requiring OWNER rechecks it at DB time; a role/binding/retirement write that would remove the last effective OWNER is rejected under the project lock, including already expired credentials. For scheduled credential expiry the administrative process MUST rotate or enroll a replacement before expiry; the system must report impending expiry and loss of effective coverage, but a missed rotation cannot grant authority after expiry. No past role interval or event is backdated to hide the gap.

If the last effective OWNER is lost, ordinary OWNER commands fail closed. Recovery is an explicit audited deployment-operator ceremony, outside ordinary OWNER authority: an allowlisted operator proves current host/credential authority and independently verifies the new or recredentialed HUMAN subject, signs an immutable recovery attestation naming project, actor, challenge and evidence, and uses a dedicated `recover_project_owner` Application command. Its separately authorized implementation must use a fresh single-use challenge, same-project lock, SERIALIZABLE transaction, existing actor/binding/membership/role/event model, and independent operator/subject principals. It may add a new binding and, if needed, a new membership/role effective **from recovery DB time**. It never reopens a retired interval, rewrites earlier owner/credential history, grants scientific approval, or uses the first-bootstrap secret. A project remains operationally unavailable until the recovery transaction commits and a live credential verifies. Any previously elapsed operational gap remains visible in audit/availability history; structural role continuity is not redefined as proof of uninterrupted authenticated availability.

## 4. Corrected identifier binding basis (P1-12)

For PR2-01 add `source_identifiers.binding_basis_artifact_version_id UUID NULL FK artifact_versions(id) ON DELETE RESTRICT` and `source_identifiers.supersedes_rejected_identifier_id UUID NULL FK source_identifiers(id) ON DELETE RESTRICT`. Both are immutable identity/provenance fields. A corrected binding has **both nonnull**. The predecessor must be REJECTED, have the exact same `(identifier_type,normalized_value)`, and be a different row; the new source is explicit and may differ only under the separately authorized cross-project correction policy. One rejected binding may have at most one direct corrected successor (`UNIQUE supersedes_rejected_identifier_id WHERE NOT NULL`), while a later rejection can be succeeded again. The pair forms an acyclic chronological chain. No rejected row is changed or deleted. These two concrete typed FKs are the durable basis relationship; no new canonical source schema is needed.

The basis is the exact FROZEN `ArtifactVersion` identity, its verified content hash and `frozen_at`. Its content is independently inspectable evidence of the corrected source-identifier association; a mere free-text reason, provider assertion or later verification event is insufficient. The add command takes `binding_basis_artifact_version_id` and `supersedes_rejected_identifier_id` as nullable typed inputs; if the normalized value has rejected history and is being rebound, it MUST select the explicit rejected predecessor and frozen basis. It cannot infer a predecessor from lookup order. An ordinary first add has both null; a caller may supply a frozen basis for an ordinary add only when the predecessor is null, but that does not turn it into a correction. `register_literature_source` with an initial identifier is an ordinary first add; a corrected binding must use explicit `add_source_identifier`. The basis and predecessor rejection event MUST already be committed before the add transaction starts. In the add transaction, lock the normalized identity and predecessor, and verify `basis.frozen_at <= add decision DB time` and `predecessor.rejection_event.occurred_at <= add decision DB time`. The predecessor must already be REJECTED at add time; a later verification can never supply the binding basis. The binding row persists its basis FK even while UNVERIFIED or after REJECTED. Formal reads verify the frozen basis/hash and the timestamp ordering. The later separate verification command retains its own event basis; it cannot replace the binding basis.

`ADD_SOURCE_IDENTIFIER` receipt input material v1 is amended before implementation to include exactly `"binding_basis_artifact_version_id": UUID|null` and `"supersedes_rejected_identifier_id": UUID|null`, both always present, in addition to the R2 fields. The receipt's same-key comparison therefore distinguishes corrected binding choices. HTTP and CLI add inputs expose both typed IDs, with both optional only for an ordinary first add. The PR2-01 pack's five-table scope remains: these are two columns, FKs and guards on the existing identifier table, not a new canonical object. No migration is run by this design.

## 5. Governance grant replay identity

The three consumption commands in R2 governance §1 require `command_key UUID`. It is globally unique across `approval_grant_consumptions`, so a key cannot be reused under another grant, project, caller or command. The authenticated actor ID and project ID are included in the request material; no caller-supplied identity is trusted. The **entire normalized request** is a closed object with keys `type` (literal `ApprovalGrantConsumptionRequest`), `material_version` (JSON integer 1), `command` (one of `RECORD_INTERNAL_SCIENTIFIC_RELEASE`, `TRANSITION_PUBLICATION_READY`, `FREEZE_PREPARED_SUBMISSION`), `project_id`, `actor_id`, `grant_id`, `target` (exact `{type,id,content_hash}` frozen conclusion or manuscript ref from the request), `result_id` (exact conclusion version, Publication or PREPARED package UUID, respectively), `expected_package_manifest_hash` (lowercase SHA-256 digest only for freeze, otherwise JSON null), and `checked_review_ids` (array of distinct InternalReviewRecord UUIDs). There are no extra or omitted keys. `checked_review_ids` is the exact finite review set bound to the ApprovalRequest, sorted by canonical lowercase UUID text after duplicate rejection; it is a set, and input order is irrelevant. A missing array is invalid; empty is invalid under the R2 approval gate. `target.type` is `ScientificConclusionVersion` only for release and `ManuscriptVersion` for the other two. `result_id` equals the target ID for release, the target's Publication ID for ready, or the exact precreated same-publication PREPARED package ID for freeze. For freeze, `expected_package_manifest_hash` is computed from the package's currently validated exact manifest before consumption and must match the committed package hash; for other commands it is null. Any semantically meaningful command argument is represented by one of these typed fields or by the grant's immutable request/decision and exact package manifest; the commands accept no other mutable free-form effect argument.

Normalize UUIDs to lowercase hyphenated canonical text; enums are persisted uppercase literals; digests are lowercase 64-hex; the nullable field is always present as JSON null when absent. Use unchanged `canonical-json-v1`: recursively sort object keys by Unicode code point, compact separators, UTF-8, no BOM/newline, and the Phase 1 serializer's escaping/number rules. This payload contains strings, integer 1, null, objects and one sorted UUID array; no float or implicit default. `request_hash = SHA-256(canonical-json-v1(payload).UTF8)` as lowercase hex; scheme `sha256-cjson-v1`. Exclude `command_key`, transport headers, request arrival time, persisted result DTO, generated event/consumption IDs, and unlisted server audit metadata. The key selects the receipt; it does not contribute to the semantic request hash.

Add to `approval_grant_consumptions`: `request_hash CHAR(64) NOT NULL`, `hash_scheme VARCHAR(32) NOT NULL CHECK = 'sha256-cjson-v1'`, `result_dto_version SMALLINT NOT NULL CHECK >0`, and `result_dto JSONB NOT NULL` as a versioned replay projection. Keep R2's concrete result FK XOR and unique grant FK; make `command_key UUID NOT NULL UNIQUE` globally. The DTO is not a formal provenance source. The consumption row and result transition/package freeze/grant event commit in one SERIALIZABLE Application transaction. The Application normalizes and hashes before effect, checks current authentication/authorization even for replay, then locks or waits on the command-key uniqueness path. If a committed row exists: equal hash and equal normalized command scope returns its saved result IDs/DTO with no new transition; different hash raises `IDEMPOTENCY_CONFLICT` 409 without mutation. A matching hash with a different key is a fresh command and cannot consume the already consumed grant. If no row exists, lock grant/target, recheck R2 policy and closure, perform the effect and insert one complete receipt. Concurrent same-key calls serialize; after a serialization retry they follow the same replay/conflict rule. Rollback leaves neither result nor receipt. A terminal grant with no matching receipt fails `GRANT_INVALID`; it is never reconstructed by caller claims.

## 6. Initial identifier primary rule

`register_literature_source` accepts at most one `initial_identifier` under the existing PR2-01 command shape. If present and registration creates a new identifier row, that row's `is_primary` is **true**; the command does not accept a separate primary flag or use insertion order. If absent, the new source has no primary. On compatible registration of an existing source, registration creates only a project link and leaves its existing identifiers and primary unchanged; any supplied initial identifier must resolve to the already existing compatible identifier and cannot alter its bit. `add_source_identifier` retains its explicit `is_primary` argument, and the database partial unique primary constraint remains. A rejected former primary retains its historical bit but is excluded from the live-primary uniqueness and is not silently replaced.

## 7. Golden vectors and verification

The appendix below is normative. Each `preimage` line is the exact canonical JSON text, without an enclosing code-fence newline. Its UTF-8 bytes are exactly `preimage.encode('utf-8')`, with no BOM and no terminal newline; the listed byte length and digest are independently checkable. Source objects preserve deliberately noncanonical key/insertion order where shown. All other R2 hash vectors remain in force and must also verify. The DecisionRecord adversarial pair demonstrates order and persisted ordinal independence. A changed member demonstrates semantic difference. No caller-selected order is a canonicalization input.

<!-- R3_VECTORS_START -->
### Decision basis A (persisted order 1)

Semantic source object (JSON; object key order is nonsemantic):

```json
{"persisted_rows":[{"target":{"type":"InternalReviewRecord","id":"00000000-0000-0000-0000-000000000022","content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"ordinal":1},{"target":{"type":"ClaimVersion","id":"00000000-0000-0000-0000-000000000021","content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"ordinal":0}]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"basis":[{"ordinal":0,"target":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000021","type":"ClaimVersion"}},{"ordinal":1,"target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000022","type":"InternalReviewRecord"}}],"material_version":1,"type":"DecisionRecordBasisSet"}
```

UTF-8 byte interpretation: `418 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `d7b1ed4e124782f4008f41f91b73f5d88a6004fb90b2eab6940ff95dda897f88`.

### Decision basis A (swapped persisted ordinals)

Semantic source object (JSON; object key order is nonsemantic):

```json
{"persisted_rows":[{"target":{"type":"ClaimVersion","id":"00000000-0000-0000-0000-000000000021","content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"ordinal":77},{"target":{"type":"InternalReviewRecord","id":"00000000-0000-0000-0000-000000000022","content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"ordinal":4}]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"basis":[{"ordinal":0,"target":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000021","type":"ClaimVersion"}},{"ordinal":1,"target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000022","type":"InternalReviewRecord"}}],"material_version":1,"type":"DecisionRecordBasisSet"}
```

UTF-8 byte interpretation: `418 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `d7b1ed4e124782f4008f41f91b73f5d88a6004fb90b2eab6940ff95dda897f88`.

### Decision basis B (different member)

Semantic source object (JSON; object key order is nonsemantic):

```json
{"persisted_rows":[{"target":{"type":"InternalReviewRecord","id":"00000000-0000-0000-0000-000000000023","content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},"ordinal":1},{"target":{"type":"ClaimVersion","id":"00000000-0000-0000-0000-000000000021","content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"ordinal":0}]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"basis":[{"ordinal":0,"target":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000021","type":"ClaimVersion"}},{"ordinal":1,"target":{"content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","id":"00000000-0000-0000-0000-000000000023","type":"InternalReviewRecord"}}],"material_version":1,"type":"DecisionRecordBasisSet"}
```

UTF-8 byte interpretation: `418 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `9f1aa18f19e41e40984f0255936197c37420c6d146d443765f36af747a5b2f13`.

### LiteratureEvidence.content_hash

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"LiteratureEvidence","material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","source_version":{"type":"SourceVersion","id":"00000000-0000-0000-0000-000000000001","content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"},"evidence_type":"QUOTATION","locator":{"page":"12","section":null,"paragraph":null,"figure":null,"table":null,"quote_span":null},"extracted_statement":"Café exposure improved recall.","normalized_assertion":null,"extraction_method":"HUMAN","confidence":"MODERATE"}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"confidence":"MODERATE","evidence_type":"QUOTATION","extracted_statement":"Café exposure improved recall.","extraction_method":"HUMAN","locator":{"figure":null,"page":"12","paragraph":null,"quote_span":null,"section":null,"table":null},"material_version":1,"normalized_assertion":null,"project_id":"00000000-0000-0000-0000-000000000010","source_version":{"content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","id":"00000000-0000-0000-0000-000000000001","type":"SourceVersion"},"type":"LiteratureEvidence"}
```

UTF-8 byte interpretation: `535 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `6afe3b7c2fb8dc7bfc2f0561055ac18ce2cd8d11a64d5c31783233a03ac57453`.

### ManuscriptVersion.placement_set_hash

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"ManuscriptVersionPlacementSet","material_version":1,"claim_placements":[],"citation_placements":[{"source_version":{"type":"SourceVersion","id":"00000000-0000-0000-0000-000000000001","content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"},"section_id":"INTRO","locator":{"kind":"PARAGRAPH","value":"p1"},"citation_purpose":"BACKGROUND","ordinal":0}],"artifact_placements":[]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"artifact_placements":[],"citation_placements":[{"citation_purpose":"BACKGROUND","locator":{"kind":"PARAGRAPH","value":"p1"},"ordinal":0,"section_id":"INTRO","source_version":{"content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","id":"00000000-0000-0000-0000-000000000001","type":"SourceVersion"}}],"claim_placements":[],"material_version":1,"type":"ManuscriptVersionPlacementSet"}
```

UTF-8 byte interpretation: `411 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `4dd9c22356a328ec182d0a4f2330f55ffe5b60b6ca65d48eee63ced773bddf95`.

### ManuscriptVersion.content_hash

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"ManuscriptVersion","material_version":1,"publication_id":"00000000-0000-0000-0000-000000000004","document_artifact":{"type":"ArtifactVersion","id":"00000000-0000-0000-0000-000000000024","content_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"},"title":"Café recall","abstract":null,"semantic_change_class":"INITIAL","placement_set_hash":"4dd9c22356a328ec182d0a4f2330f55ffe5b60b6ca65d48eee63ced773bddf95"}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"abstract":null,"document_artifact":{"content_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","id":"00000000-0000-0000-0000-000000000024","type":"ArtifactVersion"},"material_version":1,"placement_set_hash":"4dd9c22356a328ec182d0a4f2330f55ffe5b60b6ca65d48eee63ced773bddf95","publication_id":"00000000-0000-0000-0000-000000000004","semantic_change_class":"INITIAL","title":"Café recall","type":"ManuscriptVersion"}
```

UTF-8 byte interpretation: `439 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `2e910c3b0c9242184a0d4daf7fda5bd5f17defb41feb7e53fa46be1ff83830dc`.

### Grant K+A input order 1

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"ApprovalGrantConsumptionRequest","material_version":1,"command":"TRANSITION_PUBLICATION_READY","project_id":"00000000-0000-0000-0000-000000000010","actor_id":"00000000-0000-0000-0000-000000000011","grant_id":"00000000-0000-0000-0000-000000000025","target":{"type":"ManuscriptVersion","id":"00000000-0000-0000-0000-000000000007","content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"result_id":"00000000-0000-0000-0000-000000000004","expected_package_manifest_hash":null,"checked_review_ids":["00000000-0000-0000-0000-000000000013","00000000-0000-0000-0000-000000000012"]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"actor_id":"00000000-0000-0000-0000-000000000011","checked_review_ids":["00000000-0000-0000-0000-000000000012","00000000-0000-0000-0000-000000000013"],"command":"TRANSITION_PUBLICATION_READY","expected_package_manifest_hash":null,"grant_id":"00000000-0000-0000-0000-000000000025","material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","result_id":"00000000-0000-0000-0000-000000000004","target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"type":"ApprovalGrantConsumptionRequest"}
```

UTF-8 byte interpretation: `610 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `c08f141629ea381ea71ddc9ad1f44ceb952fa1d6cbcc3e0847263a53cbaddf3b`.

### Grant K+A input order 2

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"ApprovalGrantConsumptionRequest","material_version":1,"command":"TRANSITION_PUBLICATION_READY","project_id":"00000000-0000-0000-0000-000000000010","actor_id":"00000000-0000-0000-0000-000000000011","grant_id":"00000000-0000-0000-0000-000000000025","target":{"type":"ManuscriptVersion","id":"00000000-0000-0000-0000-000000000007","content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"result_id":"00000000-0000-0000-0000-000000000004","expected_package_manifest_hash":null,"checked_review_ids":["00000000-0000-0000-0000-000000000012","00000000-0000-0000-0000-000000000013"]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"actor_id":"00000000-0000-0000-0000-000000000011","checked_review_ids":["00000000-0000-0000-0000-000000000012","00000000-0000-0000-0000-000000000013"],"command":"TRANSITION_PUBLICATION_READY","expected_package_manifest_hash":null,"grant_id":"00000000-0000-0000-0000-000000000025","material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","result_id":"00000000-0000-0000-0000-000000000004","target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"type":"ApprovalGrantConsumptionRequest"}
```

UTF-8 byte interpretation: `610 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `c08f141629ea381ea71ddc9ad1f44ceb952fa1d6cbcc3e0847263a53cbaddf3b`.

### Grant K+B changed grant

Semantic source object (JSON; object key order is nonsemantic):

```json
{"type":"ApprovalGrantConsumptionRequest","material_version":1,"command":"TRANSITION_PUBLICATION_READY","project_id":"00000000-0000-0000-0000-000000000010","actor_id":"00000000-0000-0000-0000-000000000011","grant_id":"00000000-0000-0000-0000-000000000026","target":{"type":"ManuscriptVersion","id":"00000000-0000-0000-0000-000000000007","content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},"result_id":"00000000-0000-0000-0000-000000000004","expected_package_manifest_hash":null,"checked_review_ids":["00000000-0000-0000-0000-000000000013","00000000-0000-0000-0000-000000000012"]}
```

Exact canonical JSON preimage (one line, no trailing newline):

```json
{"actor_id":"00000000-0000-0000-0000-000000000011","checked_review_ids":["00000000-0000-0000-0000-000000000012","00000000-0000-0000-0000-000000000013"],"command":"TRANSITION_PUBLICATION_READY","expected_package_manifest_hash":null,"grant_id":"00000000-0000-0000-0000-000000000026","material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","result_id":"00000000-0000-0000-0000-000000000004","target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"type":"ApprovalGrantConsumptionRequest"}
```

UTF-8 byte interpretation: `610 bytes`, no BOM or terminal newline; `preimage.encode("utf-8")`. Expected SHA-256: `b65aa64fa7ae49e3842d78d78295d445b741f7dde09d2472d0949802983f7b2b`.

<!-- R3_VECTORS_END -->

## 8. Design gate

The later authorized PR2-00 contract/evidence pack must incorporate the eighth challenge table and credential-expiry operational checks. The later authorized PR2-01 pack must incorporate the two binding-basis fields, amended add receipt material and registration primary rule. The later authorized governance PR must incorporate the grant receipt fields/algorithm and corrected DecisionRecord basis hash material. These are design amendments to those packs, not execution of them. Independent review must verify the committed R3 subject against frozen Phase 1 and all R2 closed properties. Until that review, `READY_FOR_PHASE2_REAUTHORIZATION=NO`, `PHASE_2_AUTHORIZED=NO`, `READY_FOR_PHASE2_IMPLEMENTATION=NO`, and `NEXT_PR=NONE`.
