# C03 contract disposition

Status: **BLOCKED_BY_ARCHITECTURE_DECISION**

Date: 2026-10-10 (Asia/Shanghai). Reviewed F2 candidate: `86658eb83bb0552da36510368d70fe5c049ec086`. Remediation branch: `recovery/f2-p1-remediation`. Exact resulting commit is recorded in the external `P1_A_CHECKPOINT.md`; no historical identity is reassigned.

## Authority and independent confirmation

Read architecture 01 → correction02 → registry03 → cross-phase08 → Phase2 specification05 → Harness09 → PR2-04 execution pack, then the exact F2 review findings and relevant Contract13/ADR-0011/source/tests.

- `docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md:28`: executed_by is UUID, without NULL. Shared physical rules make optional columns explicit.
- `execution/phase2/PR2-04_Literature_Search_Execution_Execution_Pack_v1.0.md:74` (§5): initially requester; set once to first execution actor at PLANNED→RUNNING; historical attribution thereafter. §13.1 lines209/211 makes unmarked columns NOT NULL and allows that single assignment; §13.2 line222 refers back to §5.
- `docs/architecture/adr/ADR-0011-search-execution-attempt-accounting.md`: explicitly makes no change to Contract13 core execution/query/result semantic columns/statuses. Its header is proposed, not authority for an exception. The pack also has a design-only header; it cannot overrule incorporated contracts.
- Cross-phase08 requires governed compatible changes; AGENTS.md prohibits silent architecture changes. User explicitly prohibits trusted baseline migration edits and requires stopping for unauthorized migration.

Affected implementation and assertions:

- `src/researchbase/domain/literature_search_execution.py:90`: nullable default. create() omits executed_by; start() sets actor; cancel() leaves it unchanged.
- `src/researchbase/persistence/models.py:1055`: nullable UUID mapping.
- `src/researchbase/persistence/literature_search_execution_repository.py:163,181,215`: reads/inserts/updates the domain value directly.
- `src/researchbase/application/literature_search_execution.py:1882`: exposes null as null.
- `migrations/versions/0024_literature_search_execution.py:28,691`: nullable SQL column; assignment guard permits a changed actor only with OLD.executed_by IS NULL during first start.
- `tests/integration/phase2/test_pr2_04_schema_coverage.py:61` explicitly classifies it nullable; `test_pr2_04_planned_sql_completion.py:73` expects null in pre-start CANCELLED. Other authority/recovery/success tests require the initiating executor after start. Existing unit lifecycle test starts with another actor but does not assert initial requester attribution.

The database-free actual-domain diagnostic in external `C03_diagnostic.json` confirms initial null at version1, null after pre-start cancellation, and different executor attribution after start at version2. Literal SQL inspection independently confirms nullable column and old-null guard. No PostgreSQL result is claimed.

## Disposition and necessary human decision

The intended initial attribution is clear. A domain-only correction would conflict with the existing DB guard when the first executor differs from requester; a mapping-only correction would not repair deployed schema. A coherent correction requires an authorized additive migration for nullability/initial attribution admission and one-time assignment guard, plus domain/model/tests. Editing sealed0024 or0025 would violate this task's boundary.

No migration is authorized here. Stop C03 without implementation. Architecture owner must authorize the additive correction and decide how any existing null PLANNED/pre-start terminal rows are treated without silently rewriting immutable historical attribution. Alternatively, an explicit approved contract amendment would need architecture/compatibility review; historical source authenticity alone cannot authorize nullability.

No baseline migrations or product code were changed, and no partial attribution fix was introduced. Residual risk: current candidate still has the confirmed C03 contract violation and is not approved for F3. Required future tests include requester initialization, different first executor, pre-start cancellation, subsequent/recovery attribution immutability, direct-SQL guards and additive migration/preservation on PostgreSQL. Those tests are NOT_RUN here.
