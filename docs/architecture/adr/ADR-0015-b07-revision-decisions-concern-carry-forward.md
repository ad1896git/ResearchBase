# ADR-0015 — B07 revision Decisions and concern carry-forward

Status: ACCEPTED — APPROVED by owner 2026-10-16; first slice authorized for implementation.

## Context

Existing Decision review basis selects reviews, not one exact ReviewIssue. Existing
RevisionAction result references do not express a reviewer's explicit attestation
of correspondence to a completed action. Matching targets or free text cannot
establish either relation. B07-AQ-01 and B07-AQ-02 require architecture admission.

## Decision

The owner's 2026-10-16 task instruction explicitly approves both questions and
implementation of the first slice of [B07](../../proposals/B07_Revision_Decisions_Contract_DRAFT.md).
This instruction is the approval provenance; no signature or additional approver
is inferred. The owner also forbids changes to frozen numbered architecture
files. This ADR therefore supplies the additive Registry 03 and Field Contract 13
entries required by B07 §12.3, without editing those frozen documents.

Registry additions, owned by governance, are immutable typed relations:

- `decision_revision_concerns`: DecisionRecord → exactly one ReviewIssue;
  `decision_id UUID PRIMARY KEY/FK decision_records(id)`,
  `review_issue_id UUID NOT NULL UNIQUE/FK review_issues(id)`.
- `revision_action_re_reviews`: RevisionAction → InternalReviewRecord, attributed
  to its independent HUMAN reviewer; `revision_action_id UUID NOT NULL FK
  revision_actions(id)`, `internal_review_record_id UUID NOT NULL FK
  internal_review_records(id)`, composite primary key; `recorded_by UUID NOT NULL
  FK actors(id)`, `recorded_at TIMESTAMPTZ NOT NULL`.

All FKs use ON DELETE RESTRICT. The registered typed `decision_basis_claims` is
activated with `(decision_id,claim_version_id)` primary key, one target per
Decision, nonnegative unique ordinal, and concrete RESTRICT FKs. No top-level
entity, generic JSON reference, stored mapping state or receipt is admitted.

The admitted purpose policy is REVISION_RESPONSE × REQUIRE_CHANGE or
ACCEPT_NO_CHANGE, one Decision per exact Issue, XOR Claim/conclusion target and
complete exact-target review basis. Release PROCEED remains separate. Decision
and RevisionAction material_version=1 hashes remain unchanged. The two new
relations are **not cryptographically bound** by existing hashes; the owner
explicitly accepts immutable concrete membership and verified closure instead.

B07 §§3, 11–12 define the finite action/result/correspondence matrix, attribution,
error mappings, deferred guards and table-first write / lock-free snapshot read
protocols. B08, Issue disposition, release, API/CLI and later slices remain gated.

### Review-remediation amendment — owner instruction 2026-10-16

The owner's subsequent review-remediation instruction authorizes the global order
SHARE(B) → review records by UUID FOR SHARE → Issue → action/predecessor, across
B07 Application and trigger paths. This supersedes the draft's initial Issue-first
Decision and action-first re-review sequences. The deferred re-review trigger
revalidates without acquiring locks; BEFORE admission retains the inventory and
row locks through commit. First associations still serialize with corrections.

The same instruction authorizes fixing the existing Review writer. Every Review
creation/replay reserves ROW EXCLUSIVE on internal_review_records before any row
lock, using the existing bounded pre-BEGIN profile. Normal-role INSERT already
reserves that mode. Review writers remain compatible with each other and wait
against B07 SHARE before holding project/actor rows needed by B07's FK checks.
SHARE on the insertion destination would require an unsafe upgrade, so this is
the concrete compatible implementation of the authorized writer-order fix.
Historical hashes, references and authorization policies remain unchanged.

## Consequences

Concern selection exists before a completed response and Decision-only actions
resolve a deterministic effective Issue. Explicit action/review links preserve
independent, possibly adverse re-review without implying resolution or validity.
Additional completeness, immutability, exact-path and concurrency checks are
required. History is append-only; populated-history downgrade must refuse loss.
This ADR does not declare implementation verification or Phase 2 gate success.

## Alternatives

Combined Issue/Decision actions alone defer concern selection and lose the
one-Decision-per-Issue policy. Whole-review concerns cannot distinguish multiple
Issues. Target-matching candidate reviews cannot attest action-specific mapping.
A new Issue FK on Decision or action FK on Review also needs admission and changes
cardinality. Free text or JSON locators violate concrete provenance requirements.
