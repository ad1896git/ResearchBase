# PR2-13 remaining placement contract matrix

Base `7b3eb92111ead77849b1e2c80b7b93f18eda82e8`. This matrix freezes two
conditional development slices; formal M3 and PR2-13 admission remain blocked.
Authority: Phase 2 spec §17/§33/PR2-13; Global Registry §publication;
Phase 2 correction §5/§7; field contract §Shared physical rules and
§Publication; R2 hash contract §common encoding/ManuscriptVersion placement set.

| Placement | Exact target and lifecycle | Project/fields | Database invariant | Positive and negative test | Scientific meaning |
| --- | --- | --- | --- | --- | --- |
| Claim | `claim_versions.id`, frozen material: status FROZEN or SUPERSEDED, `frozen_at` and 64-hex `content_hash` | `claims.project_id = publications.project_id`; `manuscript_version_id`, XOR `claim_version_id`/`scientific_conclusion_version_id`, `section_id`, closed `locator={kind,value}`, `rhetorical_strength`, `ordinal`, shared ID/actor/time | Concrete FK RESTRICT, XOR CHECK, typed uppercase strength, unique manuscript+section+ordinal, actor/target indexes, DRAFT parent and frozen same-project target trigger | Valid exact claim readback; reject missing, DRAFT, cross-project, both/null targets, duplicate ordinal, malformed locator, unauthorized principal, conflicting/concurrent replay; empty/nonempty downgrade | Presentation of an existing ClaimVersion; never creates SUPPORTS, evidence review, VERIFIED, or approval. |
| Conclusion | `scientific_conclusion_versions.id`, frozen material: status FROZEN or SUPERSEDED, `frozen_at`, support-set/content hashes | `scientific_conclusions.project_id = publications.project_id`; same table and fields as Claim, opposite XOR arm | Same FK, XOR and trigger; no Claim alias or current-pointer substitution | Valid exact conclusion readback; reject DRAFT, missing hash, cross-project and wrong arm | Presentation of an existing synthesis; no new conclusion, support or promotion. |
| Artifact | `artifact_versions.id`, frozen material: status FROZEN or SUPERSEDED, `frozen_at`, 64-hex content hash | `artifacts.project_id = publications.project_id`; `manuscript_version_id`, `artifact_version_id`, `section_id`, closed locator, role FIGURE/TABLE/OTHER, ordinal, shared ID/actor/time | Concrete FK RESTRICT, role CHECK, unique manuscript+section+ordinal, actor/target indexes, DRAFT parent/frozen same-project target trigger | Valid exact readback; reject invalid role, DRAFT, cross-project, missing, duplicate ordinal, malformed locator; rollback and downgrade | Inclusion of an ArtifactVersion, without scientific support, approval, or manuscript freeze. |

R2 defines the placement locator as exactly `{kind,value}`, with kind
PARAGRAPH/SPAN/CAPTION/ANCHOR and nonblank NFC value. Sections and locator
values use the accepted citation command's 2000-character bound. Rhetorical
strength is DESCRIPTIVE/SUGGESTIVE/SUPPORTED/STRONG. `SUPPORTED` is a
presentation strength label, not a new support relation. Frozen status of the
referenced version is necessary but does not itself prove current scientific
validity; the later manuscript freeze must recompute closure and hashes. Draft
readback here is explicitly nonformal. No placement-set hash, manuscript
content hash, freeze, review, approval, or submission transition is added.

The frozen contract enumerates FIGURE/TABLE/OTHER presentation roles but does
not define a canonical mapping from those roles to the free-form
`artifacts.artifact_type` values. That mapping is UNSPECIFIED here; the slice
checks the exact frozen ArtifactVersion and allowed role, without inventing an
artifact-kind vocabulary. No generic target JSON or alternative semantic
schema is introduced.
