# M2-AQ-001 — durable metadata observations and result-resolution linkage

Status: OPEN; no contract/schema change implemented. Starting candidate df603fe0fbb8c80758400e7b13cb831b7f730187.

## Required behavior

M2 mission §§4–5 requires durable conflicting bibliographic observations and explicit unresolved/ambiguous outcomes, with exact originating result/plan/execution linkage. These must survive process restart without creating LiteratureEvidence or overwriting frozen history.

## Frozen constraints and gap

- TDG2-02 (`docs/architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md:12`) requires resolver provider/version/retrieval metadata and raw-response ArtifactVersion when retained.
- PR2-04 execution pack §8 (`execution/phase2/PR2-04_Literature_Search_Execution_Execution_Pack_v1.0.md:136`) states: “later retention must use redacted, licensed immutable ArtifactVersion bytes and a separately reviewed concrete linkage, never inline provider JSON.”
- Field contract 13 (`docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md:31`) defines appended resolutions with required result/source FKs, optional same-source version FK, actor/time and text basis. There is no observation-artifact FK or source-less observation outcome. This table is not implemented at the approved M1 checkpoint.
- Correction 12 §6 (`docs/architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md:90`) limits SourceVersion metadata to six curated bibliographic fields and excludes vendor response/adapter material.
- Source identifier verification already has a frozen ArtifactVersion basis FK, but only models UNVERIFIED→VERIFIED/REJECTED transitions. It cannot own a source-less, conflicting/unavailable provider observation, nor repeated conflict observations after verification without changing the identifier's status.
- Field contract 13 migration rules require ADR and revised contract before semantic changes. AGENTS §§4,11 prohibits silently extending canonical schemas and primary-chain soft references.

A transient Crossref response or CLI JSON output is insufficient to meet durable conflict preservation. A standalone CAS file would not establish the required concrete database provenance linkage. Encoding artifact/result UUIDs in `basis TEXT` or generic Artifact metadata would leave soft references instead of a reviewed concrete owning relation. Reusing SourceVersion fulltext/correction basis would misstate bibliographic observations as fulltext or a scientific correction.

## Proposed narrow amendment for architecture-owner review

Keep existing SearchResultResolution as the successful result→source/version relation. Specify a dependent append-only metadata-observation relation (or explicitly approved extension of the existing resolution pattern), rather than a new top-level aggregate. It needs concrete result FK, exact frozen ArtifactVersion basis FK, provider/mapping version, retrieval time, typed MATCH/CONFLICT/AMBIGUOUS/UNAVAILABLE outcome, actor and replay semantics. Specify source-null outcomes and authorization/project closure. Retain only redacted permitted provider bytes in CAS; no secrets or vendor JSON in SourceVersion. Clarify whether UNAVAILABLE without a response has no artifact and how that is represented.

An ADR and revised field contract must settle exact storage, linkage, hash/idempotency, constraints and transaction rules before implementing that amendment. This question does not authorize M3 evidence/support/review, generic orchestration, a new literature database, or source merging.

## Work preserved

One requested M2 worktree exists at the reviewed M1 commit. Offline OpenAlex adapter code/tests are preserved but not activated in production composition. A single real keyless OpenAlex network connectivity probe returned HTTP 200; it is not the required authenticated end-to-end demonstration. No canonical DB writes, migrations, credentials or user installation changes were made.
