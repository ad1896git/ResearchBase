# R01 G6/F6 exact manuscript scenario evidence

This additive test-only candidate exercises the existing owner-approved M1-S1
contract. It does not change Application/domain/ports/persistence/migrations,
architecture, the frozen informational matrix, accepted Phase2 history or risk.
The scoped pack is `r01_manuscript_scenarios_pack.md`; baseline is main
`4ad4e834098b6bf111779752b897b00787a9dede`.

## Exact carryover mapping

The old PR2-19 revision-cycle test covers six result types and conclusion-domain
cycles. The old matrix's G6 manuscript-cycle/F6 manuscript-result reasons predate
M1's owning commands. Existing `test_m1_manuscript_revision.py` supplies the
Application successor/freeze/review/disposition path. The new
`test_r01_manuscript_scenarios.py::test_manuscript_completed_result_keeps_issue_open_until_independent_disposition`
joins those contracts into one explicit manuscript scenario:

| Requirement | Assertion in the new scenario |
|---|---|
| Frozen old/new target and exact typed result | v2 is the next same-Publication frozen version; original v1 cannot serve as completed result (`INVALID_STATE_TRANSITION`, zero protected count change). MANUSCRIPT_CHANGE has only the manuscript result field populated and reports VALID. |
| Completed action is separate from issue disposition | Original OPEN history remains exact after action; an independent exact-v2 review still does not close it. The readiness command denies `DECISION_BASIS_INVALID` with zero partial writes while that inherited blocker remains. |
| Independent concern resolution | A different actor performs exact-v2 review, links it to the action and separately records ADDRESSED. Original review ID, frozen target/hash and initial issue event remain; one disposition event is appended. A second disposition command denies with no partial writes. |
| New-target decision and permission | Readiness basis includes the exact v2 review and excludes old v1 review. Separate requester and independent approver obtain a usable READY_FOR_SUBMISSION grant, which is read back through Application. No grant consumption or external effect is performed. |
| History and reads | Full v1 DB row and Application readback remain unchanged. Decision/action/issue/grant/result reads execute under observed lock-free REPEATABLE READ READ ONLY snapshots and leave protected counts unchanged. |

The public B11 readiness command's existing blocker mapping is
`DECISION_BASIS_INVALID`; M1's later-same-Publication result guard maps an old
result to `INVALID_STATE_TRANSITION`. These are existing contracts, not new
error semantics. Exact-v2 review is created before testing the inherited blocker,
so the denial does not merely prove absence of an eligible review.

## Local measurements

Explicit local PG admin URL selected TCP127.0.0.1:5432/postgres as user fengwang;
fixture checked user/port/data_directory `/opt/homebrew/var/postgresql@18` and
system ID7696072587520791948 before CREATE. Only random fixture-owned
`researchbase_pr211_r2_test_...` databases were migrated and cleaned. No existing
project database, service or runtime configuration was changed.

New owning scenario (attempt2): **1 passed, 3 warnings in 2.36s**, exit0. Exact
command: `.venv/bin/python3 -m pytest -s tests/integration/phase2/test_r01_manuscript_scenarios.py`
with the explicit admin/database URLs and four identity pins above. Attempt1
remains **1 failed, 3 warnings in 1.39s**: its initial test expectation incorrectly
used PROVENANCE_CLOSURE_VIOLATION for an old result; it was corrected by checking
the existing M1 contract/source. No production behavior was changed. Initial
Pyright similarly found an un-narrowed union readback; an explicit owning DTO
assertion resolved it. Raw attempts remain separate under the external review
log directory; no failed run is counted as PASS.

Full Ruff check: **PASS**. Ruff format: **1011 files already formatted**.
Pyright: **0 errors, 0 warnings, 0 informations**. Existing Alembic
path_separator deprecation warnings and Pyright update notice are retained.
Owning regression: **20 passed, 60 warnings in 41.21s**, exit0. Command:
`.venv/bin/python3 -m pytest tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_pr2_19_revision_cycle.py`
with the same explicit admin/database URLs and identity pins. CI is a separate
exact-head gate; no CI result is inferred from this local run.

## Remaining gates and limits

This is an R01 evidence substep, not whole G6/F6 or R01 acceptance. It does not
cover F5c reconsideration, F9, Agent provenance, R4–R7 repairs or a Phase2 GO
change. Frozen matrix statuses remain unchanged. Independent review, exact-head
seven-check CI and medium-risk owner/fresh-base merge gates are separate; local
PASS alone does not authorize merge. No label, merge or deploy is performed.
