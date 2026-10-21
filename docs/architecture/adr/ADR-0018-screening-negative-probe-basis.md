# ADR-0018 — Screening and negative-probe basis

Status: ACCEPTED — APPROVED by owner 2026-10-19; first slice authorized for implementation.

## Context

[B20](../../proposals/B20_Screening_Negative_Probe_Contract_DRAFT.md) needs exact retained probes,
per-result dispositions/criteria and the basis for
NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE. Accepted
[ADR-0017](ADR-0017-novelty-material-v2.md) admits positive
assessment basis, coverage resolution membership and comparison corrections;
it deliberately leaves negative admission disabled. Architecture
[03](../03_Global_Schema_and_Contract_Registry_v1.0.md),
[12](../12_Phase2_Architecture_and_Contract_Correction_v1.0.md),
[13](../13_Phase2_Schema_Field_Contract_v1.0.md) and
[15](../15_Phase2_Hash_Payload_Contract_R2_v1.0.md) do not yet register
B20 children or its hash shape. This is a requested additive amendment, not an
assertion that frozen architecture already authorizes them.

## Decision — proposed; each admission requires owner approval

### Architecture Question B20-AQ-01 — can existing records express the basis?

Reuse existing facts first: immutable execution_context stores ordered intended
queries/provider/budgets; terminal execution seals retain attempts/query/results,
including zero results and interruptions. B21 coverage retains exact executions
and visible resolution membership. PriorArtRelation/evidence and B22 chains
retain exact comparisons and corrections. NoveltyAssessment already owns the
attributed outcome, scope, narrative criteria and predecessor.

These records do not say which disposition/criterion a particular assessment
assigned to every result, or retain its explanation for a zero-hit or uninvoked
probe. A positive basis relation cannot represent a result without a comparison,
a query with zero hits, or a never-invoked query. Overloading it would change its
FK semantics and B19 completeness rules. Current result lists, counts, timestamps
or a digest alone cannot enumerate these missing judgments after restart.

### 1. Owner decision — admit novelty_assessment_probes

**Proposed separate decision:** admit `novelty_assessment_probes` as a
literature-owned immutable child Relation of the existing NoveltyAssessment,
keyed by assessment/execution/query-index, with B20 §12.1's exact columns,
constraints and guards. It retains per-assessment dispositions and explanations
for intended probes, including zero-hit and never-invoked queries.

### 2. Owner decision — admit novelty_assessment_screening_results

**Proposed separate decision:** admit `novelty_assessment_screening_results` as a
literature-owned immutable child Relation of the existing NoveltyAssessment,
keyed by assessment/result, with B20 §12.1's exact columns, constraints and guards.
It retains per-assessment result dispositions, criterion ordinals and exact
comparison/resolution witnesses where applicable.

For both admissions, concrete RESTRICT FKs, closed enums and criterion ordinals
form the semantic core. Bounded narrative explains judgments. No top-level Probe,
Screening entity, criteria table, generic polymorphic JSON or new persistence
mechanism is admitted. Two typed shapes avoid an XOR table with nullable
execution/result targets. They reuse the existing Assessment + sealed Relation
pattern, including same-transaction attribution, immutability and deferred
bidirectional completeness checks (0042, 0066 and 0068).

All exact-plan executions visible under B20's first SHARE lock form the inventory;
all saved query-context positions and retained results must be represented.
This is a bounded retrospective declaration, not prospective preregistration or
proof of exhaustive external literature discovery. Later expanded inventories
change current usability only. An owner requiring prospective completeness must
approve a separate plan contract before negative admission, not weaken this label.

### 3. Owner decision — compatible outcome-specific material v2

Admit exactly B20 §5's complete new payload shape for screening INCONCLUSIVE and
NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE. Preserve ADR-0017 positive v2 and original v1
payloads byte-for-byte. A stored screening_captured BOOLEAN on the assessment
selects the new shape; outcome plus discriminator must agree with its material
version. The flag is not an extra JSON hash key: the mandatory screening_basis
object identifies the shape in canonical material. Old payloads acquire neither
new null fields nor rehashed digests. Coverage/comparison/resolution/Phase 1
material stays unchanged. Use sha256-cjson-v1 and each nested record's own version.

This choice extends v2's previously denied outcome and adds an explicit screening
shape for INCONCLUSIVE; it never changes a previously admissible payload. Dual
readers must precede writers. Old binaries remain unsupported for new shapes.
Unknown shapes fail closed; replay uses the saved shape/version. A new material
version would also be possible, but is not needed to distinguish these closed,
previously inadmissible shapes. Independent old/new literal hash vectors are
required before enabling writes.

Negative admission requires B21 v2 coverage, no omitted intended probe or result,
complete warning-free successful attempts, every frozen planned provider actually
invoked with no undeclared provider, zero unresolved results, all-result
NOT_CLOSE dispositions under exact criteria, and UNIQUE currently usable B22
terminal RELATED/CONTRASTING comparisons with independently HUMAN-VERIFIED
scientific evidence and captured exact resolution witnesses. Empty results require
at least one completed NO_HITS probe. EXCLUDED, CLOSE, UNCLEAR, partial overlap,
ambiguous roots or failed probes cannot prove absence. Authority and narrative
criteria cannot override deterministic facts.

### Architecture Question B20-AQ-02 — preserve B19 guard ownership

[0066](../../../migrations/versions/0066_b19_close_prior_art_basis.py)'s
b19_complete_basis() requires positive basis on every material_version=2 row.
Simply widening a CHECK would therefore reject every new screening assessment.
ADR-0017 also forbids silently replacing sibling/shared functions.

**Proposed explicit exception:** preflight the exact baseline; leave all shared
pr218_* and sibling b19_*/b21_*/b22_* function bodies unchanged. Replace only
ck_b19_novelty_material with B20's additive shape CHECK, and recreate only the
B19 parent constraint-trigger attachment trg_b19_novelty_complete with
WHEN (NOT NEW.screening_captured). Keep its DEFERRABLE INITIALLY DEFERRED behavior
and unchanged function. B20's own parent/child constraint triggers enforce complete
screening and reject B19 positive-basis children on screening parents. The B19
basis-child trigger stays unconditional and the B19 early prelock trigger stays
active on every assessment. Thus a screening parent cannot evade both guards.
Existing positive/v1 cases still execute the original function.

No new table-lock inventory or advisory namespace. First SQL is the existing N
SHARE statement in a READ COMMITTED UoW, then request advisory and exact Claim
FOR UPDATE; this coordinates comparison roots/corrections and assessment admission.
Read paths use one read-only REPEATABLE READ snapshot without explicit table,
advisory or row locks. Existing normal-role prelock/Claim coordination remains
mandatory. B20 guards check, rather than acquire, prelocks.

## Consequences and verification

Owner approval admits only this bounded architecture amendment; implementation
still requires separate authorization. One forward migration at the actual head
must preserve old hashes, preflight sibling guard definitions and fail on an
unexpected baseline. Populated screening history prevents downgrade. Empty
downgrade restores the exact original B19 CHECK/attachment and removes only B20
objects; no scientific history is deleted to permit rollback.

B20 §12.4 requires literal mixed-shape vectors, normal-role SQL, migration/catalog,
restart/replay, phantom and Claim-serialization races, final-clock authorization
and lock-free-read evidence on PostgreSQL 18.x. Baseline checks in a documentation
task do not verify proposed B20 behavior. No Phase 2 acceptance is implied.

## Alternatives

- Reuse existing exact execution/coverage/comparison facts alone: necessary but
  lacks per-assessment screening/negative-probe explanations.
- Put reference arrays in an ArtifactVersion, JSONB manifest or external Skill:
  moves primary-chain references away from concrete FKs and duplicates ownership.
- Add a new top-level screening subsystem or prospective plan lifecycle here:
  exceeds this bounded Assessment/Relation extension and needs separate review.
- Mutate coverage's screening flag or old hashes: changes historical facts and
  wrongly attributes one assessment's screening to every coverage consumer.
- Change all v2 payloads or replace b19_complete_basis(): breaks existing byte or
  guard ownership contracts. The proposed amendment changes only new shapes and
  the explicitly named attachment/CHECK.
