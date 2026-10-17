# Stabilization summary — review preparation, 2026-10-13

Review branch: `work/pr2-15-base`.
Base: `origin/backup/pr2-15-v51-verified-20261013` at
`76b60ed29ad220010bba9020401e10a962a5de60`.
Verified implementation HEAD: `820d514545f7a8d1f624d7aa1e85268c3e1d38da`.
The review range contains 12 existing local commits. Task 9 adds this summary and
verification evidence, and removes one inherited blank line at EOF from the
Basic Approval draft; it creates no commit or branch, rewrites no history,
and performs no push. `src/`, `tests/`, migrations and governing contracts are
unchanged by Task 9.

**Review preparation is not gate acceptance.** The nine known schema failures are
open **P1 MAJOR** findings. The director's recorded acceptance of those failures
as known does not authorize their repair, turn them into PASS, or permit a merge
or gate-success declaration under AGENTS.md §10. The two proposals remain DRAFT;
provisional transport mappings remain pending architecture-owner decision.

## What each commit changed and why

Listed oldest first, relative to the backup base; descriptions reflect the actual
changes and evidence rather than treating commit titles as completion claims.

| Commit | Change | Why |
| --- | --- | --- |
| `b8179f1` — Fix the four failing architecture tests | Scoped lineage/PR-12 guards to their protected historical obligations; removed Application SQLAlchemy handling by adding opt-in UoW deadlock normalization for Discussion/Conclusion. | Accommodate authorized Phase 2 work while preserving layering and PR2-04's default error/transaction behavior. |
| `90c92eb` — Fix the 24 failing unit tests | Refreshed error inventories and HTTP/CLI mappings, 0042 head expectations, cancellation/transport fixtures and portable CAS symlink handling; repaired failed-phase evidence recording and temporarily recorded inherited static debt. | Correct obsolete fixtures and evidence-tool defects without deleting protective assertions or presenting inherited lint/type debt as clean. See [per-failure remediation](../unit_test_remediation_20261013.md). |
| `e2a7ded` — Make disposable-cluster PostgreSQL tests portable | PR2-10/11/12 fixtures now require explicit local `RB_TEST_ADMIN_URL`, create/drop owned databases, and accept optional cluster identity assertions. | Remove dependence on another author's cluster while retaining real PostgreSQL assertions, explicit opt-in and cleanup. |
| `dd3982e` — Make ruff format and ruff check clean repository-wide | Formatting/lint cleanup, removal of Ruff/formatter baseline debt, frozen-migration exclusions, and full-history CI checkout. | Make static checks enforce current cleanliness and provide Git history required by lineage tests. |
| `6cfd971` — Make pyright clean and drop grandfathered type debt | Real annotations/narrowing and typed fixture corrections; emptied Pyright baseline debt; re-exported the M3 fixture for Phase 2 integration suites. | Eliminate type debt and fix cross-suite fixture discovery rather than suppress diagnostics. See [Task 4 review](task4-pyright-review.md). |
| `eb86f6d` — Make the full test suite pass against PostgreSQL | Normalized DB identity timestamps to UTC; corrected obsolete expectations, URL/proof/catalog/transaction fixtures and enabled two disposable historical migration tests; recorded schema blockers. | Fix permitted production/fixture/environment defects. **Despite its title, the suite did not pass:** recorded final run was 4938 passed, 9 failed, 0 errors, 1 skipped; no pristine pre-task baseline exists. See [Task 5](task5/REPORT.md). |
| `4c2f538` — Tidy task-5 evidence and scope architecture exceptions | Narrowed architecture exceptions to exact authorized migration/table pairs; retained global `run_versions` prohibition; corrected evidence whitespace and the report's baseline/director disposition. | Keep architecture exceptions bounded and make evidence accurate and reviewable. Its socket/DB failures were sandbox blocks, not passes; see [Task 5b](task5b/REPORT.md). |
| `35d4e24` — Narrow ruff exclusions | Replaced broad exclusions with the 30 exact SHA256-pinned historical migration paths through 0028; formatted unpinned 0039/0041 and governance/migration tests. | Protect frozen bytes while allowing Ruff to scan other migrations and the governance test file. Migration edits in this range are formatting, not the proposed schema repair. |
| `9eb3ad4` — Record the provisional error-code mappings as an Architecture Question | Added REVIEW-AQ-001 and comments linking both adapter tables; executable ASTs unchanged. | Prevent transport choices absent from frozen specs from silently becoming architecture. See [the Architecture Question](../../planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md). |
| `8bdc6c6` — Make hard-coded machine paths in runtime code configurable | Added environment-backed Runner/HG1 settings, portable shell-script overrides and README defaults; added host-configuration checks and local four-database Runner mode. | Permit verification on this host while preserving native credentials, UID, private storage, policy, loopback/HBA and DB identity checks. [Task 8](task8/REPORT.md) records 1837 unit/architecture and 36 affected PostgreSQL cases passing. |
| `09b3036` — Draft the RevisionAction contract (documentation only) | Added the [RevisionAction draft](../proposals/PR2-15_RevisionAction_Contract_DRAFT.md), with typed result shapes, completed-action trace, immutable correction, concurrency, planned tests and owner questions. | Make the unresolved revision/Issue dependency reviewable before contract freeze or separately authorized implementation. |
| `820d514` — Draft the Basic Approval contract (documentation only) | Added the [Basic Approval draft](../proposals/PR2-16_Basic_Approval_Contract_DRAFT.md), with request/decision/grant policy, replay, lifecycle dependencies, planned tests and owner questions. | Make approval scope and dependency gaps explicit; approve no release/effect and grant no implementation authority. |

## Final verification

**Final suite result: FAIL — 4955 passed, 9 failed, 0 errors, 0 skipped**,
2617 warnings, 4800.74 seconds (1:20:00), exit 1; **4964 cases**.
Console and XML counts reconcile. All nine failed IDs exactly match the known
schema list; there are no new failed IDs and no NOT_RUN/skipped pytest cases.
Unit/architecture cases within this full run: **1837 passed**, 0 failed/errors/skipped.
The formerly skipped four-installation Runner case passes in real disposable local
mode. See [final counts](task9/final-counts.json), [console](task9/full-pytest.log.gz),
[XML](task9/full-pytest.xml.gz), [failed IDs](task9/remaining-schema-failures.txt),
and [command record](task9/commands.txt).

The initial full run completed with **4954 passed,
10 failed, 0 errors, 0 skipped**, 2617 warnings, 4802.37 seconds, exit 1.
[Initial counts](task9/initial-counts.json), [console](task9/full-pytest-initial.log.gz)
and [XML](task9/full-pytest-initial.xml.gz) record all 4964 cases. Its nine schema
failed IDs exactly match the known list. The tenth failure was the static gate
`test_candidate_static_gates_and_inherited_formatter_delta`: cumulative
`git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` detected an inherited
blank line at EOF in the Basic Approval draft, line 434. Task 9 removes that one
blank line without changing proposal content/status. The cumulative whitespace
check now exits 0; the [focused static-gate rerun](task9/static-fix.txt) has
**1 passed**, 0 failed/errors/skipped, exit 0, in 4.67 seconds. The final unfiltered
full run above also passes that case on the corrected tree.
The initial failure remains recorded rather than being relabeled PASS.

Verification runs from the repository root on Python 3.12.15 and [PostgreSQL 18.6
(Homebrew)](task9/postgresql-version.txt). [Tool versions](task9/tool-versions.txt) identify pytest 8.4.2, Ruff
0.12.12, Pyright 1.1.411, psycopg 3.3.4 and SQLAlchemy 2.0.52.
No dependency update was performed. Pyright's newer-version notice is not a type
diagnostic.

Exact environment and required commands:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
uv run pyright > docs/verification/task9/pyright.log 2>&1
uv run ruff format --check . > docs/verification/task9/ruff-format.log 2>&1
uv run ruff check . > docs/verification/task9/ruff-check.log 2>&1
HG1_RUN_LOCAL=1 uv run pytest -o addopts='' -q -ra -p no:cacheprovider --junitxml=docs/verification/task9/full-pytest.xml > docs/verification/task9/full-pytest.log 2>&1
```

The pytest invocation has no marker, path or failure-limit filter. It includes
unit, architecture, integration, migration, constraint, concurrency and e2e
suites. `HG1_RUN_LOCAL=1` selects Task 8's real disposable four-installation mode;
it is not retained-host verification. XML and console counts are reconciled,
including every failed/error/skipped node ID.

| Check | Exact final result | Evidence |
| --- | --- | --- |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 | [output](task9/pyright.txt) |
| `uv run ruff format --check .` | 456 files already formatted; exit 0 | [output](task9/ruff-format.txt) |
| `uv run ruff check .` | All checks passed; exit 0 | [output](task9/ruff-check.txt) |
| Full pytest with both PostgreSQL URLs and `HG1_RUN_LOCAL=1` | 4955 passed, 9 failed, 0 errors, 0 skipped; 2617 warnings; exit 1 | [counts](task9/final-counts.json), [console](task9/full-pytest.log.gz), [XML](task9/full-pytest.xml.gz) |
| All `scripts/*.sh` syntax | 4 scripts passed; exit 0 | [output](task9/shell-syntax.txt) |
| Final diff/protected paths/summary links | PASS; exact counts in evidence | [validation](task9/final-validation.txt) |

Read-only post-run [database inventory](task9/database-inventory.txt) lists
`postgres`, `researchbase`, and
`researchbase_pr2_test_8208d2069f40464db72757d93c17dfdc`. The last has no active
sessions, but its ownership is not established by the run logs/XML; [read-only
metadata](task9/database-ownership.txt) has no filesystem creation time, and
modification time does not prove ownership.
There was no pristine pre-run database inventory. It is preserved; **zero remaining
test databases is not claimed**. No database was manually dropped by Task 9.

## NOT_RUN and historical evidence limits

Every unexecuted obligation is kept separate from executed failures. The nine
schema cases are FAIL, not NOT_RUN. Historical sandbox errors remain historical
errors even if corresponding tests execute successfully today.

| Item | Reason and current disposition |
| --- | --- |
| Retained four-M2 deployment Runner check (`HG1_RUN_LIVE=1`) and original host acceptance scripts | This host has no authorized retained four-installation evidence/root policy for the original host. Task 9 uses the owned disposable `HG1_RUN_LOCAL=1` mode; it does not claim retained-host deployment, onboarding, policy or Human Gate acceptance. Task 5's skipped Runner node is tracked separately in the final measured results. Shell scripts receive syntax checks only. |
| Manual deletion of the remaining fixture-named database | Ownership is unproven; a name prefix alone is insufficient authority to delete it. Read-only inventory/session checks ran. Owner must identify it before any cleanup. |
| Proposed post-0042 schema repair upgrade/preflight/downgrade acceptance | No repair migration is authorized or implemented. Existing migrations are tested by the full suite; acceptance of the proposed new migration cannot run before an owner decision and separate implementation authorization. |
| RevisionAction architecture obligations, draft §8 | All seven groups remain planned: Application layering; finite concrete schema/provenance; governance separation; frozen closure/hash compatibility; immutable correction history; authority/disclosure/replay; writer coordination. No implementation is authorized. |
| RevisionAction implementation acceptance, draft §9 | All eight groups remain planned: basis/relevance; seven result shapes; exact revision trace; no resolution/effect; idempotency/correction; PostgreSQL constraints/migrations; failure/temporal safety; later implementation regressions. Baseline regression execution today cannot prove behavior that does not exist. |
| Basic Approval implementation acceptance, draft §8 | All eleven groups remain planned: layer/boundary; semantic separation; finite policy; frozen closure; basis/blocking; actor/temporal policy; schema/history; rejection/revision; replay/failure; lifecycle/effect dependencies; future migration/regression acceptance. Draft status and unapproved dependencies prevent implementation acceptance. |
| Scientific/governance promotion | No live provider, authentic scientific approval/release, grant consumption/external effect, retained deployment acceptance, Human Gate, TDG2 or formal PR/M4 gate is exercised or advanced by this stabilization task. Synthetic PostgreSQL fixtures and a draft review are not that evidence. |
| Independent architecture review / owner contract decisions | This task prepares review material; it does not perform fresh independent architecture review or obtain owner decisions. |

Historical non-execution is documented in [Task 4](task4-pyright-review.md),
[Task 5b](task5b/REPORT.md), [Task 7](task7/REPORT.md), and both proposal §11
sections. Task 5b's DB selection had 133 setup errors; Task 7's DB selection had
1 pass, 15 failures and 50 errors; each proposal's four-suite DB selection had
56 setup errors because the sandbox denied PostgreSQL/shared memory/socket
operations. Those attempts did not prove PostgreSQL assertions. Task 5b did not rerun the
full suite because the same sandbox denied socket operations; Task 8 verified affected suites rather than rerunning the full suite.
Broader scientific suites were not run during the documentation-only draft tasks
because no executable behavior changed. Task 9's full suite supplies current
baseline execution evidence;
the drafts' future behavior, formal gates and retained-host checks remain NOT_RUN.

## Open follow-ups and owner decisions

| Follow-up | Owner/action required | Boundary and evidence |
| --- | --- | --- |
| Nine schema failures — **P1 MAJOR** | Architecture/project owner must approve or reject the existing-contract forward repair; an implementation owner can then implement it under separate authorization. | [SCHEMA-BLOCKERS.md](task5/SCHEMA-BLOCKERS.md) and [exact nine IDs](task5/remaining-schema-failures.txt). Three column/constraint inventory cases, five FK-index cases and one concrete scoped-FK case remain enabled. No startup-DDL workaround or historic migration rewrite. |
| Provisional review error transport values | Architecture owner must explicitly confirm `REVIEW_TARGET_NOT_FROZEN` = HTTP 409 / CLI 4 and `CONFLICT_OF_INTEREST` = HTTP 403 / CLI 3, or choose replacements and record governing amendment/ADR. | [REVIEW-AQ-001](../../planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md). Alternatives include validation/provenance categories for unfrozen targets and governance-conflict status for COI. A replacement requires synchronized adapters, docs and contract/integration tests. |
| RevisionAction contract freeze | Owner must resolve all draft §10 questions: initial breadth; revision-purpose Decision; open-Issue recording; writer/read/Agent authority; deterministic cross-domain relevance; stale historical admission; correction/basis semantics; Issue lifecycle; transaction writer/lock/retry realization. | [RevisionAction DRAFT](../proposals/PR2-15_RevisionAction_Contract_DRAFT.md). Completed revision recording does not resolve Issues, authorize PROCEED or create approval. Separate revision-purpose and disposition contracts are still dependencies. |
| Basic Approval contract freeze | Owner must resolve all draft §10 questions: bounded slice versus three purposes/consumption; later-review evidence; duplicate/resubmission policy; concern carry-forward/rejection recovery; typed conditions; symmetric REJECT gates; lifecycle/writer coordination; stale/expiry event transaction policy; DTO/replay/transport errors. | [Basic Approval DRAFT](../proposals/PR2-16_Basic_Approval_Contract_DRAFT.md). HUMAN independent APPROVER rules, immutable evidence and no invalid-fact override remain. Freeze approval alone is not IMPLEMENTATION_GO. |
| Remaining fixture-named database ownership | Local database owner must identify `researchbase_pr2_test_8208d2069f40464db72757d93c17dfdc` and decide whether it can be removed. | [Inventory](task9/database-inventory.txt); no active sessions; not attributable to a specific owned fixture from retained evidence, so Task 9 preserves it. |
| Formal acceptance and review disposition | Reviewer and project owner assess the diff against authoritative contracts and current evidence. No merge/gate success with open P0/P1 under AGENTS.md. | Minimal PROCEED is bounded by [companion 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); it is not full PR2-15 RevisionAction, Basic Approval or resolution of the blocking-Issue cycle. |

The proposed schema repair is **one additive child after 0042**, preserving all
historical migration bytes and existing rows/receipts. It adds UNIQUE on attempt
`query_record_id` and scoped query `(literature_search_execution_id,id)`, converts
receipt `result_dto_version` from INTEGER to SMALLINT, adds missing leading B-tree
indexes for execution actors, query/attempt same-parent reference, event
execution/attempt and actor, receipt project/result and actor, and the exact
execution listing index `(project_id,status,created_at,id)`. The new attempt
UNIQUE provides its query-FK index. Preflight duplicates and SMALLINT range must
fail closed without rewriting scientific history. Verify one head, unchanged
populated scientific/provenance/receipt material, exact catalog/FK indexes,
data-preserving/refused downgrade, regressions and full-suite execution. **This
proposal is not applied by any stabilization commit or Task 9.**

## Ready-to-paste pull-request description

Suggested title: **Stabilize PR2-15 baseline verification and document pending contracts**

### Before

The backup baseline had stale architecture/unit expectations, inherited Ruff and
Pyright debt, PostgreSQL fixtures and Runner/HG1 paths tied to another host, and
review error transport choices without an owner decision record. RevisionAction
and Basic Approval lacked bounded reviewable draft contracts.

### After

Scope architecture guards to authorized historical obligations, move deadlock
translation behind the Application UoW port, fix UTC identity-clock handling,
refresh protective fixtures and make disposable PostgreSQL/host verification
portable. Ruff and Pyright debt is removed; only 30 SHA256-pinned historical
migration paths are excluded from Ruff. Record REVIEW-AQ-001's provisional
transport choices and add non-authorizing RevisionAction/Basic Approval drafts.
Review preparation also removes one inherited blank line at EOF in the Basic
Approval draft so the cumulative branch whitespace gate passes.

Nine known schema contract failures remain open P1 findings pending the owner's
forward-migration decision. The suite is not all green. The draft contracts grant
no implementation authority, scientific approval, Issue resolution or gate
acceptance. No schema repair is included.

### How

PostgreSQL 18.6 / Python 3.12.15: **4955 passed, 9 failed, 0 errors, 0 skipped**,
2617 warnings, 4800.74 seconds, exit 1, in the final unfiltered full suite. The nine
failed IDs exactly match the known schema blockers. All 1837 unit/architecture
cases and the local four-installation Runner case pass within that run.
Pyright: **0 errors, 0 warnings, 0 informations**; Ruff format: **456 files already
formatted**; Ruff check: **all checks passed**; all three exit 0. Shell syntax:
**4 scripts pass**. Current and cumulative whitespace checks pass.

The initial full run had 4954 passed / 10 failed: nine schema blockers plus the
inherited EOF whitespace defect. That defect is fixed; its focused rerun has
1 passed, and the final full run passes it. Initial and final evidence is retained
in the stabilization summary.

Read-only database inventory contains one inactive fixture-named database of
unproven ownership; it is preserved pending identification. No zero-orphan claim
is made.

Use `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase`
and `RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres`
with `UV_CACHE_DIR="$PWD/.uv-cache"`; run `uv run pyright`,
`uv run ruff format --check .`, `uv run ruff check .`, and
`HG1_RUN_LOCAL=1 uv run pytest -o addopts='' -q -ra -p no:cacheprovider --junitxml=docs/verification/task9/full-pytest.xml`.
See `docs/verification/STABILIZATION_SUMMARY.md`,
`docs/verification/task5/SCHEMA-BLOCKERS.md`,
`planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md`, and `docs/proposals/`.

Retained-host deployment checks and all future RevisionAction/Approval/migration
acceptance obligations remain NOT_RUN for the reasons recorded in the summary.
Review preparation leaves the existing branch/history intact; no push is made.
