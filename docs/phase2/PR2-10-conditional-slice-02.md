# PR2-10 conditional slice 02 — durable discussion command boundary

**Base:** accepted conditional development HEAD
`d765db625c45ccafa855b1996906bd337978b33b`.

**Frozen contracts:** Phase 2 §§14, 26, 41.6, 42.4 and PR2-10; Global
Schema Registry DiscussionSession/DiscussionTurn; Cross-Phase Contracts
discussion ≠ decision and immutable scientific history. Migration 0032 may
install only these two admitted entities and necessary typed input/citation,
command-receipt and state-audit support tables. No generic reference JSON.

**Scope:** Add one synchronous Application service with authenticated
create-session, append-turn, close-session and readback commands. Use the
existing verified principal, live credential, project membership/role and
temporal checks. Treat OWNER/RESEARCHER as existing project writer roles;
turn speaker identity always comes from that authenticated principal.
Persist exact ResearchQuestionVersion, ClaimVersion and SourceVersion input
references in typed FK tables. New references must resolve to the same
project and an immutable FROZEN/SUPERSEDED version. Turns are append-only,
ordinal and citation rows immutable. Serialize commands under project/session
locks and durable idempotency receipts. Close records its actor/time and
returns the exact transcript and mechanical concept-map *candidates* built
from committed records. Readback after a new process must reproduce both
candidate hashes. No generated content becomes a canonical fact.

**Promotion boundary:** Expose no successful discussion-to-research or
discussion-to-decision promotion command. Explicit requests through this
service fail closed because the frozen contracts do not define a new
promotion authority in this slice. A future separately reviewed Application
command must validate evidence and target lifecycle before any promotion.

**Exclusions:** No retained M2/M3 write, Human B/C simulation outside tests,
real review, live provider, ResearchSummary or ArtifactVersion persistence,
CAS write, formal PR2-10 admission, schema change beyond the admitted typed
discussion aggregate. The absence of persisted derived ArtifactVersions and
ResearchSummary blocks formal PR2-10 completion.

**Verification:** On PostgreSQL 18 port 55442, use per-test disposable
databases named `researchbase_pr210_test_<random>`, verify server ID
`7695073913076924777` and pre-migration emptiness, run Alembic through
0032, exercise creation, readback, restart, duplicate/concurrent calls,
wrong-project and draft refs, unauthorized writers, denied promotion,
close/append rollback, source provenance and immutable triggers. Recheck
retained M3 read-only hash. Run focused unit/architecture/M2/M3 regression,
Ruff and Pyright.

**STOP:** Unexpected database identity or revision, migration failure,
untrusted credential path, schema beyond this contract, retained data change,
or inability to run real PostgreSQL integration tests.
