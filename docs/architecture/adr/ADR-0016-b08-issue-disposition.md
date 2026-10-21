# ADR-0016 — B08 Issue disposition event refinement

Status: ACCEPTED — APPROVED by owner 2026-10-16; first slice authorized for implementation.

The owner's task instruction approves the first slice and implementation guide of
[B08](../../proposals/B08_Issue_Disposition_Contract_DRAFT.md), including the event
field and guard refinements. ADR-0015 already admits B07-AQ-01/02 and its exact
`revision_action_re_reviews` composite reference. This additive admission supplies
Registry 03 and Field Contract 13 refinements without rewriting frozen contracts.

Existing governance ReviewIssueEvent remains an IMMUTABLE_RECORD. Add nullable
`revision_action_id UUID`, `re_review_record_id UUID`, `decision_id UUID` and
`rationale TEXT` to `review_issue_events`; original OPEN events retain NULL basis.
The three concrete references and composite mapping FK use ON DELETE RESTRICT.
Terminal events require an exact committed completed action and exact committed
independent re-review mapping. The event UUID is its replay identity. No new
entity, table, receipt, JSON semantic core or hash scheme is admitted.

ReviewIssue.status is an operational OPEN→ADDRESSED/DISMISSED projection, changed
only with its immutable event in the same transaction. Original descriptors and
root history are immutable. All existing literal Review/Decision/action hashes
remain unchanged; event rationale/membership are not cryptographically bound by
those hashes. Populated terminal history cannot be downgraded away.

The finite authority, basis and acceptance policies are B08 §§3,11. SHARE-first
READ COMMITTED writes protect B07's exact inventory, reviews then sorted mixed-mode
Issue rows; actions are never row-locked by B08. Strengthen Issue INSERT parent
review exclusion to FOR UPDATE while retaining scientific coordination. Reads and
nested verifiers use one lock-free REPEATABLE READ, READ ONLY snapshot, checking
current entitlement against fresh database time before return. Historical reads
validate saved structure and report current validity without reapplying creation
validity, current writer authority or action-terminal requirements.

Application/port/repository modules retain ownership. B07's existing 26-table
REVISION_SNAPSHOT_TABLES already includes internal_review_records: reuse it directly
rather than adding a duplicate. The guide references 0041's Issue guard; its shipped equivalent is the 0049
replacement, which also coordinates manuscript INSERTs. Both the new guard and
downgrade preserve that complete latest definition. No other naming substitution
is required.
Later slices, API/CLI, reopening and scientific validity overrides remain excluded.
This ADR records authorization, not test acceptance or Phase exit.


The required real evidence-review race exposed a pre-existing owning-writer
inversion: evidence authorization held the same actor FOR UPDATE before its
INSERT waited for SHARE(B), while the new event's actor FK needed KEY SHARE.
The supporting repair reserves the evidence command's actual INSERT destination
ROW EXCLUSIVE before authorization rows (CREATE_EVIDENCE, REVIEW_EVIDENCE), exactly as the accepted review writer does. SERIALIZABLE,
command material, scientific state and B08's lock inventory/order are unchanged.
This reserves no table for reads and adds no B07 lock-order rewrite.


### Reviewer-remediation instruction — 2026-10-16

The owner requires fixing the reported full-check failures and repeating the
source/evidence concurrency checks. B08 §12.2's exact SHARE snapshot and §12.4's
required real mutable-writer commit orders require compatible owning-writer
reservation. This is a supporting implementation inference from those clauses,
not a new scientific command or expanded schema admission.

The source race exposed an actual table cycle between source_versions UPDATE and
literature_sources current-pointer UPDATE. Source transitions now reserve their
final ROW EXCLUSIVE table modes in lexical order before source/authority row locks.
Freeze reserves literature_sources and source_versions; create/update/abandon
reserve only source_versions. Existing SERIALIZABLE isolation/material remain unchanged.
The race retains the pause before pointer UPDATE to verify the repair rather than
hiding the unsafe interval. The same-actor audit also requires IMPORT_DOCUMENT's existing artifact INSERT
reservations: removing them restores the authority-row/event-FK cycle. Evidence
reservations remain limited to the actual IMPORT_DOCUMENT, CREATE_EVIDENCE and
REVIEW_EVIDENCE destinations. Six real-backend regression cases verify draft
source create/update and unrelated document import by the disposer in both orders.
B08's FIRST SHARE inventory and row-lock order are unchanged.
