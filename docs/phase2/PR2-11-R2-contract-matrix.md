# PR2-11 R2 contract matrix — frozen before implementation

Base: `0498204bbef4faea390a8724038462ebfff3e901`.
Precedence: Addendum A18 (`02_...Addendum...`, A18) places the R2 gap
closure (`14_...R2`, §3) and literal hash contract (`15_...R2`, common encoding
and lines 81–89) above conflicting R1 fields and older Phase 2 prose.
The Global Registry owns the stable identity/version names. This matrix
does not promote the blocked PR2-11 candidate.

| Requirement and authority | Input / output / persistence | Positive and negative test |
| --- | --- | --- |
| Identity/version, Registry rows 82–83; R2 §3 | Stable `ScientificConclusion` and numbered `ScientificConclusionVersion`; DRAFT→FROZEN→SUPERSEDED, never rewrite frozen material. Same-parent current pointer. | Create/read/revise; reject cross-parent pointer and frozen edit. |
| Typed inputs, R2 §3 | `scientific_conclusion_claim_inputs`: exact ClaimVersion FK, relation, zero-based ordinal, nullable claim-bound LiteratureSupportSnapshot FK. `scientific_conclusion_literature_inputs`: exact LiteratureEvidence FK, relation, zero-based ordinal. No generic reference JSON. | Claim-only, literature-only and combined sets; reject empty, duplicate, gaps, wrong-project/snapshot target. |
| Snapshot match, R2 §3 | Bound snapshot targets the exact same ClaimVersion and Project, is immutable and hash-verified. Composite FK and freeze guard. | Accept matching frozen snapshot; reject cross-claim/project or altered hash. |
| Freeze, R2 §3 | One transaction validates at least one input, exact frozen Claim and Phase 1 closure, bound snapshot closure, direct positive evidence latest independent HUMAN VERIFIED, frozen non-retracted source, then seals input set. | Positive freeze/readback; reject draft/stale/retracted/rejected support; rollback preserves DRAFT. |
| Direct/snapshot duplicate, R2 §3 | Duplicate positive support is invalid. The exception for CONTRADICTS/QUALIFIES requires statement/limitations to acknowledge the difference; no mechanical acknowledgment grammar is specified, so exception handling is **UNSPECIFIED** in this slice and overlaps fail closed. | Reject duplicate positive overlap; do not infer semantic acknowledgment. |
| Binding hash, R2 hash contract lines 81–85 | Exact payload `ScientificConclusionVersionSupportSet`, material_version 1, `claim_inputs` and `literature_inputs`; each row has typed `R(T)` with exact stored `content_hash`, relation and ordinal; claim row includes nullable typed snapshot ref. Sort `(ordinal,target.id)` within each array; reject duplicate target/relation. Persist SHA-256 of canonical-json-v1. | Supplied R2 golden preimage/hash; order, missing key, changed ref hash, ordinal and snapshot sensitivity. |
| Own hash, R2 hash contract lines 87–89 | Exact payload `ScientificConclusionVersion`, material_version 1, parent `scientific_conclusion_id`, statement, exactly four-key scope (`population`, `conditions`, `time_window`, `applicability`), uppercase confidence, nullable limitation, binding hash. Exclude row ID/status/time/actor. | Supplied R2 golden preimage/hash; reject missing/extra scope keys, changed parent or content. |
| Canonical material, R2 common encoding | NFC human text at creation, canonical-json-v1 UTF-8, lowercase UUID/digest, explicit nulls, uppercase enums, zero-based contiguous ordinals. `hash_scheme=sha256-cjson-v1` where persisted. | Unicode equivalence, exact payload bytes, invalid Unicode/enum/order rejection. |
| Reference closure, R2 common encoding and §3 | Frozen read recomputes both hashes and upstream closure; later upstream invalidity is derived STALE/INVALID, never a rewrite of old hashes. SUPERSEDED exact refs remain historical. | Restart/readback; tampered hash fails; dispute/retraction changes validity projection while frozen bytes persist. |
| Authority, System Architecture/Application; R2 §3 | Authenticated principal, current project membership/role/credential, one command per DB transaction; no candidate or Agent output promotes itself. | Unauthorized write/read denied; idempotent replay, concurrent creation, rollback. |
| Test-only participants | Disposable PostgreSQL 55442 only; fixtures never constitute genuine Human B/C evidence. | Assert disposable database identity and cleanup; no retained writes. |

Confirmed blocked-candidate defects: missing snapshot FK and at-least-one
cardinality; incomplete support/own hash payload; incomplete scope and enum
material; initial direct positive SUPPORTS review bypass (subsequently fixed
there, but not accepted lineage). Its nine passing PostgreSQL tests do not
establish R2 compliance. Relevant exact golden vectors are in the R2 hash
contract and will be used verbatim.

Explicitly unspecified by R2: a machine-readable semantic acknowledgment
grammar for direct/snapshot CONTRADICTS/QUALIFIES overlap; any automated
promotion authority for a generated conclusion; a new scientific schema
beyond the typed tables and admitted snapshot relation.
