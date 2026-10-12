# PR2-13 conditional placement scope

Base: `29b50efd9f23159d5b9537091ff196dfbb24ae4f`.
Roadmap: Phase 2 specification §PR2-13, Manuscript Scientific Placement.
This is development only; M3 Human Gate and formal Phase 2 admission remain blocked.
PR2-09 official STORM adapter is a SHOULD and may be deferred when native strategy suffices.

| Frozen source | This slice | Verification |
| --- | --- | --- |
| Field contract §Publication, R2 hash contract §placement-locator | Typed citation placement on an existing DRAFT ManuscriptVersion, exact frozen SourceVersion FK, closed `{kind,value}` locator with kind PARAGRAPH/SPAN/CAPTION/ANCHOR, uppercase citation purpose, section and zero-based ordinal | Valid add/read; malformed locator, enum, non-DRAFT parent and missing target rejected. |
| Registry and Phase 2 spec §17, §33 | Citation is a presentation location, never scientific support. Trace query returns exact manuscript/source version IDs and labels this path citation-only. | No Claim/EvidenceRelation rows or support claim created; restart readback. |
| Field contract shared physical and correction §7 | One linear migration adds only `manuscript_citation_placements`, its exact FKs, uniqueness, indexes and frozen-target/parent guards. | Disposable PostgreSQL catalog and direct-SQL rejection; empty downgrade restores 0035 catalog; nonempty downgrade refuses. |
| Existing PR2-12 Application/UoW | Owner/Researcher write, project-scoped authorized read, one transaction, request replay serialized and payload checked. | Unauthorized, cross-project, duplicate and concurrent replay tests. |

The citation command bounds both `section_id` and locator `value` to 2000
Unicode code points after NFC normalization. The database repeats these limits
for direct SQL writes.

Exclusions: Claim/Conclusion and Artifact placements, placement-set or manuscript
content hashes, manuscript freeze, formal promotion, review, approval, retained
M2/M3 writes, live provider contact. This slice cannot claim full PR2-13 or
PR2-12 formal acceptance. It is a complete citation-only vertical capability
within the PR2-13 contract; the remaining placement kinds require later
separate authorization and review.
