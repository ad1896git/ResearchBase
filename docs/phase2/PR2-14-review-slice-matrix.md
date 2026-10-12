# PR2-14 conditional Internal Review slice: contract-to-test matrix

Base: `f40aaed866431a563aef0aa07dbf9b8910cbc749`.
Authority: Phase 2 specification §§19, 33.3, 37, PR2-14; Phase 2 correction
§§4, 6, 7; Global Registry §governance; cross-phase Review ≠ Decision ≠ Approval.

This first vertical slice creates one immutable InternalReviewRecord for an
exact frozen ClaimVersion and its initial OPEN ReviewIssues in one Application
transaction. The schema has the frozen contract's four concrete target FKs;
the Application command rejects other target kinds until their scientific
validity checks are implemented in a separately reviewed slice. Issue resolution,
DecisionRecord, RevisionAction, approval and manuscript freezing are later
frozen scopes and cannot be inferred from a review. All actors in tests are
disposable TEST ONLY identities, never genuine M3 human gate evidence.

| Contract | Persisted rule | Positive/negative test |
| --- | --- | --- |
| Exact target | One concrete FK to frozen ClaimVersion, ScientificConclusionVersion, ArtifactVersion or ManuscriptVersion; target hash is verified copy | This command accepts frozen same-project Claim only; draft, cross-project, absent, hash mismatch and multi-target direct SQL rejected; other target kinds fail closed. |
| Reviewer authority | Verified HUMAN with active REVIEWER or OWNER role and credential; reviewer independent of target author | Reviewer accepted; author/self, forged actor, expired/revoked role/credential and unrelated project rejected. |
| Immutable review | Own hash uses exactly `project_id`, frozen target ref, `reviewer_actor_id`, `review_type`, `recommendation`, `summary` with canonical-json-v1; no issue data in review hash | Exact recomputation and reconnect readback; direct UPDATE/DELETE rejected; no target write. |
| Initial issues | Review FK, severity/type/locator/description and optional exact related Claim/Source/Run FKs; OPEN, appended initial event | Zero or bounded issues; invalid related reference or cross-project reference rejected; direct update/delete rejected; issue event retained. |
| Transaction and replay | One UoW; stable request UUID identifies command replay; no partial review/issues | Identical replay returns same review; conflicting replay rejects; failure rolls back; concurrent identical requests yield one row. |
| Scientific meaning | Review is an evaluation, never Decision, Approval or scientific truth | No decision/approval/claim/manuscript mutation and no automatic HUMAN VERIFIED LiteratureEvidence event. |

No frozen contract authorizes using a DRAFT manuscript as a review target.
ReviewIssue resolution is excluded because dismissal of a blocking issue
requires PR2-15 DecisionRecord and RevisionAction. No retained database write,
live provider contact, formal M3/PR2-14 admission or root policy operation.
