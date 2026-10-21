# B23 API and CLI contract

The first slice records an exact novelty review, a completed direct reassessment,
and exact re-review correspondence through the existing Application services.
Every call uses trusted deployment authentication and project entitlement.
Reviewer/creator identities, timestamps, hashes and material versions are derived.

All HTTP paths start with `/v1/projects/{project_id}`. POST returns 201 and GET
returns 200, including exact historical replay.

| Path suffix | POST fields | GET identity |
| --- | --- | --- |
| `/novelty-reviews` | `target_id`, `review_type`, `recommendation`, `summary`, ordered `issues`, `request` | `/novelty-reviews/{id}` |
| `/novelty-revision-actions` | `id`, `review_issue_id`, `result_novelty_assessment_id`, optional `supersedes_revision_action_id` | `/novelty-revision-actions/{id}` |
| `/novelty-revision-actions/{id}/re-reviews/{review_id}` | No body | Same exact pair path |

Each Issue contains only `severity`, `issue_type`, `description`. Summaries and
Issue descriptions are NFC text of 1–16,000 characters without NUL; the ordered
Issue array contains 0–100 entries. UUID strings use lowercase hyphenated form.
Enums and error HTTP/CLI mappings remain B23 §§11.2–11.3.

CLI operations are `researchbase novelty-review record/show` and
`researchbase novelty-revision record/show/link/show-link`. All require
`--project-id`; other flags use the DTO fields in kebab case. Review recording
uses `--request` and `--issues` (a JSON array, default `[]`). Action recording and
exact review/action reads use `--id`. Link operations use `--revision-action-id`
and `--internal-review-record-id`. Use `--json` for machine-readable output.

A revision result must already be committed, usable, non-superseded, and directly
supersede the Issue's exact reviewed assessment for the same ClaimVersion.
Re-review must independently target that result ID/hash. Recommendations,
including REJECT and UNCERTAIN, record correspondence without disposing Issues.
Novelty Decisions, NO_CHANGE and Issue disposition remain unavailable.

Novelty adapters invoke the reused `record_concern_re_review` method with
keyword-only `novelty=True`. This is service invocation context, not a transport
or command field. It selects the fixed B23 transaction protocol before any SQL;
the selected transaction verifies the saved action version and never falls back
to another protocol. Existing callers default to the legacy protocol.

Exact reads use one lock-free REPEATABLE READ snapshot. Each new write starts
with the fixed N SHARE inventory in READ COMMITTED, followed by its owning table
reservation and the approved lock order. Write replay retains that preamble,
requires current read entitlement, and preserves the saved scientific material
while observing current diagnostics.
