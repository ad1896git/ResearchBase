# docs/verification slimming inventory (DRAFT, report only)

Generated from `git ls-files docs/verification` (tracked files only) and `grep -rnI "verification/<dir>"` over tests/, scripts/, src/, .github/, docs/ (excluding docs/verification). Nothing was deleted or moved. Only path-qualified references (`verification/<dir>`) were searched; bare-name mentions are not counted.

Rules: KEEP = referenced from tests/scripts/src/.github, or a docs reference mentioning acceptance/evidence; CANDIDATE = no external reference; UNSURE = referenced from docs only without evidence wording. Classification is heuristic and needs human review.

| Dir | Size (KB) | Files | Largest files | External references (file:line) | Class |
|---|---:|---:|---|---|---|
| b01 | 40 | 4 | `b01/required-full-check.json` (18 KB)<br>`b01/implementation-evidence.md` (16 KB)<br>`b01/clean-head-static-acceptance.json` (5 KB) | none | CANDIDATE |
| b02 | 180 | 26 | `b02/implementation-temporal.txt` (59 KB)<br>`b02/agent-binding-blocker-pg.txt` (50 KB)<br>`b02/review-b07-before.txt` (16 KB) | `docs/proposals/B02_Strategy_Candidate_Promotion_Contract_DRAFT.md:5` | KEEP |
| b06 | 19 | 2 | `b06/implementation_2026-10-15.md` (13 KB)<br>`b06/clean-head-static-acceptance.json` (6 KB) | none | CANDIDATE |
| b09 | 14 | 6 | `b09/implementation-evidence.md` (7 KB)<br>`b09/unit-architecture.txt` (3 KB)<br>`b09/head-regressions.txt` (1 KB) | none | CANDIDATE |
| b13 | 9 | 1 | `b13/first-slice-evidence.md` (9 KB) | none | CANDIDATE |
| b17 | 39 | 26 | `b17/logs/reviewer-expiry-witnesses.txt` (7 KB)<br>`b17/implementation-evidence.md` (7 KB)<br>`b17/expiry-witnesses.txt` (2 KB) | `docs/proposals/B17_Prepared_Package_Freeze_Contract_DRAFT.md:674` | KEEP |
| b22 | 14 | 3 | `b22/implementation-evidence.md` (12 KB)<br>`b22/review-followup/quick-precheck-command.txt` (1 KB)<br>`b22/review-followup/baseline-identical-files.json` (0 KB) | none | CANDIDATE |
| b23 | 33 | 3 | `b23/implementation-evidence.md` (27 KB)<br>`b23/cross-expiry-witnesses.json` (3 KB)<br>`b23/api-cli-contract.md` (2 KB) | `docs/proposals/B23_Novelty_Review_Revision_Contract_DRAFT.md:647` | KEEP |
| b27 | 8 | 1 | `b27/implementation_2026-10-17.md` (8 KB) | `docs/proposals/H2_Phase2_Hardening_Followups_Contract_DRAFT.md:68` | KEEP |
| b31-s2 | 4 | 1 | `b31-s2/implementation-evidence.md` (4 KB) | none | CANDIDATE |
| b32 | 23 | 10 | `b32/unit-architecture.txt` (7 KB)<br>`b32/README.md` (5 KB)<br>`b32/postgresql-owners.txt` (3 KB) | none | CANDIDATE |
| batch-c | 145 | 14 | `batch-c/review-focused-postgresql.txt` (75 KB)<br>`batch-c/review-full-check.txt` (23 KB)<br>`batch-c/proposed-b10-compatibility.diff` (9 KB) | `docs/phase2/migration_inventory_phase2.md:79`<br>`docs/phase2/B10-first-slice-evidence-2026-10-16.md:6` | KEEP |
| batch-d | 5 | 1 | `batch-d/integration-evidence.md` (5 KB) | `docs/phase2/migration_inventory_phase2.md:86` | KEEP |
| batch-f | 4 | 1 | `batch-f/commands.txt` (4 KB) | `docs/phase2/migration_inventory_phase2.md:108` | UNSURE |
| batch-g-review | 38 | 9 | `batch-g-review/phantom-repeat.txt` (16 KB)<br>`batch-g-review/head-catalog.txt` (7 KB)<br>`batch-g-review/pre-fix-deadlock.txt` (3 KB) | none | CANDIDATE |
| h2 | 201 | 23 | `h2/retained-originals-000.json` (51 KB)<br>`h2/baseline.json` (35 KB)<br>`h2/attempts/h2-first.txt.gz` (31 KB) | none | CANDIDATE |
| hardening-2026-10-16 | 7 | 1 | `hardening-2026-10-16/README.md` (7 KB) | `docs/proposals/H2_Phase2_Hardening_Followups_Contract_DRAFT.md:48` | UNSURE |
| pr2_17 | 7 | 1 | `pr2_17/first_slice_2026-10-14.md` (7 KB) | none | CANDIDATE |
| pr2_17_18 | 47 | 1 | `pr2_17_18/integration_2026-10-14.md` (47 KB) | none | CANDIDATE |
| task12 | 3633 | 32 | `task12/full-pytest-serial.xml` (935 KB)<br>`task12/full-sharded/partition.json` (710 KB)<br>`task12/full-sharded-interrupted/partition.json` (710 KB) | `tests/unit/test_task12_migration_history.py:15`<br>`tests/unit/phase2/test_pr2_20_evidence.py:315`<br>`tests/unit/phase2/test_pr2_20_evidence.py:319`<br>`tests/contracts/pr2_20_reports.py:621`<br>`docs/proposals/H2_Phase2_Hardening_Followups_Contract_DRAFT.md:203` | KEEP |
| task13 | 3036 | 44 | `task13/final-run/full-sharded/partition.json` (719 KB)<br>`task13/shared-final.xml` (451 KB)<br>`task13/final-run/full-sharded/shard-0.xml` (451 KB) | `docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:445`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:446`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:447`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:448`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:470`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:479`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:480`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:481`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:482`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:483`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:484`<br>`docs/proposals/PR2-15_RevisionAction_Contract_DRAFT.md:485` | KEEP |
| task14 | 10234 | 120 | `task14/restart/full.xml` (2333 KB)<br>`task14/review/full.xml` (2055 KB)<br>`task14/review/check.txt` (1202 KB) | `tests/contracts/pr2_20_reports.py:622`<br>`docs/proposals/PR2-16_Basic_Approval_Contract.md:488`<br>`docs/proposals/PR2-16_Basic_Approval_Contract.md:490`<br>`docs/proposals/PR2-16_Basic_Approval_Contract.md:492`<br>`docs/proposals/H2_Phase2_Hardening_Followups_Contract_DRAFT.md:203` | KEEP |
| task5 | 2781 | 12 | `task5/nodes-verified.txt` (663 KB)<br>`task5/nodes-final.txt` (663 KB)<br>`task5/nodes-after.txt` (663 KB) | none | CANDIDATE |
| task5b | 4 | 1 | `task5b/REPORT.md` (4 KB) | none | CANDIDATE |
| task7 | 4 | 1 | `task7/REPORT.md` (4 KB) | none | CANDIDATE |
| task8 | 4 | 1 | `task8/REPORT.md` (4 KB) | none | CANDIDATE |
| task9 | 196 | 20 | `task9/full-pytest-initial.xml.gz` (82 KB)<br>`task9/full-pytest.xml.gz` (81 KB)<br>`task9/full-pytest-initial.log.gz` (10 KB) | none | CANDIDATE |

## Totals per class

| Class | Dirs | Files | Size (KB) |
|---|---:|---:|---:|
| KEEP | 9 | 267 | 17317 |
| CANDIDATE | 16 | 96 | 3412 |
| UNSURE | 2 | 2 | 11 |

Top-level loose files (not classified, not in totals): `STABILIZATION_SUMMARY.md`, `b01-b04-b05-integration.md`, `batch-g-integration.txt`, `batch-h-integration.txt`, `task4-pyright-review.md`
