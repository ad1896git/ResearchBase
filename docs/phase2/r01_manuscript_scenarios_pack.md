# R01 G6/F6 manuscript result and concern-cycle test pack

Authorized 2026-11-01 B queue substep, medium risk. Base main
`4ad4e834098b6bf111779752b897b00787a9dede`. This pack exercises existing approved
M1-S1 Application contracts; it changes no contract or scientific implementation.
The owner-approved M1_Manuscript_Revision_Reconsideration_Contract_DRAFT.md §3,
§11–12, architecture 05 §§22/42.6 and governance correction17 §4–5 require exact
frozen manuscript results, immutable predecessor history and independent issue
disposition. R01-RECONCILIATION's G6/F6 mapping identifies the missing cross-scenario
proof. Historical B30 blocked reasons predate M1 and remain untouched here.

Add one owning E2E through existing b05/M1 fixtures: freeze v1, record a blocking
review and REQUIRE_CHANGE decision, freeze same-Publication v2, reject original
v1 as a completed result without partial effects, record MANUSCRIPT_CHANGE to
exact v2, and prove the issue remains OPEN and readiness blocked. Independently
review exact v2, link concern re-review, record ADDRESSED disposition, then obtain
an exact-v2 readiness decision and a separately approved READY_FOR_SUBMISSION
grant. Read back typed decision/action/issue/result and preserve v1 and its
original review/issue event in lock-free read snapshots. Do not consume the grant
or infer external publication. This adds the seventh result type to a focused
cross-contract scenario, not a claim of all G6/F6 or R01 acceptance.

Only new tests and evidence/pack documentation are in scope. Preserve existing
M1 and PR2-19 tests, source, migrations, frozen matrix statuses, accepted deferrals
and R4–R7. No F5c reconsideration, F9 expiry, Agent/runtime or new schema work.
If source behavior contradicts the accepted contract, stop and report; do not
change scientific code or weaken a gate to make this test pass.

Required verification: new real PostgreSQL18 scenario; existing M1 revision and
PR2-19 revision-cycle owning regression files; Ruff/format/Pyright; independent
review; exact-head seven-check CI. Local PG must use explicit admin URL and user,
port, data-directory and system-ID pins before fixture-created random disposable
databases; no existing project database may be migrated or written. Keep every
failed attempt separate. Medium-risk owner label/fresh base gates remain, with
no merge, label or deploy authorized. Final state is candidate awaiting merge,
not a change to historical Phase2 GO or whole R01 status.
