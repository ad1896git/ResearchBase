# PR2-13 ManuscriptVersion scientific trace contract matrix

Base: `57b70f38fc0a9317bf537beae19b9af14ca04ee0`.
Authority: system architecture §3.4–3.6; Global Registry §Publication;
Phase 2 specification §§17, 45, PR2-13 and final trace objective; correction
§5/§7; field contract §Publication; accepted PR2-10/11/12/13 schema.

The frozen PR2-13 contract requires a manuscript scientific trace query but
does not specify a wire format, page size, or sort key. The DTO below is a
read-only Application representation, not a new scientific schema or state.

| Requirement | Persisted authority | Query/test rule |
| --- | --- | --- |
| Input and authority | Project, Publication, exact ManuscriptVersion; current verified principal and existing project role/binding | `trace(principal, project_id, publication_id, manuscript_version_id)`; authorize before result disclosure; foreign/missing target returns NOT_FOUND; no caller supplied actor/role authority. |
| Lifecycle | `manuscript_versions.status`, hashes and `frozen_at` | Return actual persisted status and hashes; current schema only admits DRAFT, so never label a DRAFT trace formal/frozen. Do not implement freeze or promotion. |
| Placements | Three exact placement tables; source, Claim/Conclusion and ArtifactVersion FKs | Return all categories with original placement/target IDs, section, locator, ordinal, typed role/purpose/strength and target hash; citation remains `CITATION_ONLY`, other placements `PLACEMENT_ONLY`; deterministic kind/section/ordinal/ID order. |
| Claim experiment provenance | `evidence_relations` concrete ClaimVersion FK, Measurement or StatisticalResult FK; result-input and Measurement→Run FKs | Return only persisted relation ID/type and exact source/result/measurement/run IDs, including every result input; no inferred support edge. Empty tuple means no explicit relation. |
| Conclusion inputs | `scientific_conclusion_claim_inputs` and `_literature_inputs` exact frozen target FKs | Return persisted relation type/ordinal and exact ClaimVersion or LiteratureEvidence ID; never substitute current pointers. Claim inputs then expose their own persisted experiment/literature paths. |
| Literature evidence and review | Exact `scientific_conclusion_claim_inputs.literature_support_snapshot_id` → `literature_support_snapshots` + relations; direct Conclusion literature inputs; Evidence plus review-event history | Return only snapshots pinned by a placed ConclusionVersion, preserving that ConclusionVersion ID on every literature path. Never substitute a later Claim snapshot. Return exact snapshot/relation/input, Evidence and SourceVersion IDs, hashes and current review status. `SUPPORTS` is reported only when a persisted edge says so; current review state is separate. Unreviewed remains UNREVIEWED. Citation alone never creates an evidence edge. |
| Missing/stale data | Exact FKs and accepted frozen-target guards | Preserve empty edge sets as absence; fail closed on unresolved or cross-project targets and inconsistent required hashes, without inventing a new scientific validity state. |
| Consistency, ordering, size | One manuscript's finite placement and one-hop explicit evidence relations; no normative pagination/limit | Fixed batch SQL queries in one repeatable-read UoW transaction, no recursive traversal or per-placement query. Sort each returned relation by persisted ordinal and ID. No arbitrary record cap or ranking. |
| No mutation | Existing read path and PostgreSQL transaction | No INSERT/UPDATE/DELETE, no hash rewrite, no review or support creation; compare table inventories before/after; reopen connection for durable readback. |

Test fixtures use only disposable PostgreSQL 55442 databases. They may contain
synthetic Claim/Conclusion and unreviewed LiteratureEvidence but no fabricated
human VERIFIED event, Operator C or retained scientific record. The endpoint
spelling in Phase 2 prose is adapter guidance; this slice implements the
Application query only and does not add an HTTP route.
