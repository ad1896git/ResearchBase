# R01 F9 Application-scheduled expiry evidence

This candidate adds the precise owning scenario missing from the carryover map:
`tests/integration/phase2/test_r01_application_role_expiry_wait.py`. It preserves
the existing SQL-based F9 tests and changes no Application, domain, repository,
migration, schema, architecture document or historical Phase2 acceptance.

The source authority is the owner-approved 2026-10-20 R1 scheduled-role-expiry
contract and TEMP-AUTH-01. The existing
`Phase2IdentityService.close_project_role(CloseProjectRole(...,
effective_until=expiry))` schedules each finite interval. The new cases cover the
requester's OWNER role and the issuing APPROVER role. Each reads back the exact
`effective_until`, row version 2 and paired CLOSED event/request; verifies the
grant is usable before expiry; then observes the consumer's real first-lock
wait using PostgreSQL PID/blocker evidence.

The transaction starts and is observed waiting before expiry. PostgreSQL's
advancing clock crosses expiry before the holder releases. The final credential
observation is at or after release, and consumption denies FORBIDDEN for the
caller role or GRANT_STALE for the issuer role. Protected-effect counts and
ACTIVE grant history remain unchanged; the scheduled role/event also stay exact.
There is no direct SQL role update in the new cases, blind pre-transaction sleep,
expiry daemon or caller-clock substitution.

Local initial owning-case result: **2 passed in 18.72s** on PostgreSQL 18.6,
using the existing disposable-database fixture. Its explicit local admin selector
and server identity pins were checked before creating random test databases.
Only fixture-owned random `researchbase_pr211_r2_test_...` databases were migrated
and cleaned up; no existing project database was migrated or written. The first
local setup lacked the explicit admin selector; a second setup hit the existing
Unix-socket URL/ConfigParser interpolation issue. Both failed setup transcripts
are retained separately; the successful run selected the same verified cluster
via TCP and does not reclassify those failures as PASS.

The owning F9 regression file, independent review and exact-head seven-check CI
are separate gates. This is a medium-risk R01 substep requiring the trusted
owner's label and fresh head/base before merge. The main F9 matrix and R01 remain
open: these two cases do not prove all larger cross-phase scenarios, close
R4–R7, accept a new deferral or reopen Phase2 GO. Candidate code and local evidence
alone do not establish main/release acceptance.
