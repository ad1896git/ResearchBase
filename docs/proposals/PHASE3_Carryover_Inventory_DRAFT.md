# Phase 2 -> Phase 3 Carry-over Inventory

Status: DRAFT

| ID | Item | Source (file:line) | Kind | Consequence | Suggested owner |
|---|---|---|---|---|---|
| C-01 | B28 real PaperQA2 deferred (fake retained; `paperqa2` unselected) | docs/phase2/phase2_exit_report.md:52; docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md:30 | owner-accepted gap | No real retrieval capability; PR2-07 not complete; no Phase 2 success follows from B28 | Owner (commission decision); Phase 3 lead |
| C-02 | AQ-S3-08 positive G2 AGENT admission test pending | docs/phase2/phase2_exit_report.md:53; docs/proposals/B30S3_Architecture_Questions_2026-10-20.md:15 | owner-accepted gap | No Application path creates a bound AGENT; no positive AGENT admission claimed; never SQL-forge binding | Identity/Application owner (needs authorized fixture path or identity capability) |
| C-03 | Dedicated Linux benchmark host deferred (Row 17, benchmark-host part only) | docs/phase2/phase2_exit_report.md:51; docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md:4 | owner-accepted gap | Local macOS timings informational only; revisit before Phase 3 performance claims | Owner; Phase 3 performance/infra lead |
| C-04 | B20/B23 exclusion: Prospective preregistration / external search exhaustiveness | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-05 | B20/B23 exclusion: Automatic query planning / provider execution | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-06 | B20/B23 exclusion: Programmable criteria | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-07 | B20/B23 exclusion: Failed/adverse-branch replacement | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-08 | B20/B23 exclusion: Universal priority claims | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-09 | B20/B23 exclusion: Source-merge deduplication | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-10 | B20/B23 exclusion: Automatic selection across independent comparison roots | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-11 | B20/B23 exclusion: Automatic impact propagation | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-12 | B20/B23 exclusion: Novelty-target Decisions | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-13 | B20/B23 exclusion: NO_CHANGE (as novelty revision outcome) | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-14 | B20/B23 exclusion: Issue disposition / blocking-concern resolution | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-15 | B20/B23 exclusion: Direct PriorArtRelation/SearchCoverage review targets | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-16 | B20/B23 exclusion: Assessment creation inside review/revision commands | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-17 | B20/B23 exclusion: Novelty-driven approval, READY/package gate, generic Agent runtime | docs/phase2/phase2_exit_report.md:54 | deferred scope | Not delivered in B20/B23 slices; remains out of scope until separately authorized | Phase 3 novelty/review lead |
| C-18 | MANUSCRIPT_CHANGE RevisionAction as a novelty result (non-goal) | docs/phase2/phase2_exit_report.md:54 | deferred scope | Remains a non-goal; M1 supports MANUSCRIPT_CHANGE for manuscript concerns only | Phase 3 novelty/review lead |
| C-19 | Review finding R4: Revision guard FOR UPDATE vs reviewers FOR SHARE (migrations 0041/0044) | docs/phase2/phase2_exit_review_2026-10-20.md:29 | P3 finding | Correct but adds waiting; review disposition: Phase 3 backlog | Persistence owner |
| C-20 | Review finding R5: b04/b05_write_timeouts connection-level flags vs SET LOCAL (persistence/database.py) | docs/phase2/phase2_exit_review_2026-10-20.md:30 | P3 finding | Inconsistent style; review disposition: Phase 3 backlog | Persistence owner |
| C-21 | Review finding R6: Dead second DELETE block in 0074 pr212_draft_guard | docs/phase2/phase2_exit_review_2026-10-20.md:31 | P3 finding | Needs a forward migration to remove; review disposition: Phase 3 backlog | Migration owner |
| C-22 | Review finding R7: Single-peer DNS pinning without fallback; timed-out lookup leaves daemon thread (adapters/literature_http.py) | docs/phase2/phase2_exit_review_2026-10-20.md:32 | P3 finding | Accepted limitation; review disposition: Phase 3 backlog | Adapter owner |
| C-23 | Reference/provider intake: resolve revision, license/notice/terms, dated advisory review before enabling providers | docs/phase2/phase2_exit_report.md:64 | deferred scope | Providers must stay disabled until resolved; unresolved in adapter inventory (owner decision still open) | Owner; Phase 3 adapter lead |

## Item 8: skipped-as-pending tests and unavailable PR2-19 gate subcases

The pytest skip scan found only `tests/integration/phase2/test_hg1_runner_live.py:111` (`test_four_durable_deployments_authenticate_and_clean_up`), an opt-in environment skip (`set HG1_RUN_LIVE=1 ...`), not pending scope. Separately, all eight `SUBCASES` tuples whose fourth field is `False` in `tests/integration/phase2/test_pr2_19_dependencies.py` are recorded below, with their reasons quoted verbatim. This is informational owner availability, not acceptance evidence; historical reason strings may be stale. C-24 overlaps C-02 and C-28 overlaps C-11; totals count inventory rows, not distinct capabilities.

| ID | Item | Source (file:line) | Kind | Consequence | Suggested owner |
|---|---|---|---|---|---|
| C-24 | G2 s3-contract-reconciliation | tests/integration/phase2/test_pr2_19_dependencies.py:63 | owner-accepted gap | "AQ-S3-08: bound AGENT fixture requires owning Application admission path"; same owner-accepted gap as C-02 | Identity/Application owner |
| C-25 | G6 manuscript-cycle | tests/integration/phase2/test_pr2_19_dependencies.py:67 | deferred scope | "MANUSCRIPT_CHANGE denied"; unavailable gate subcase remains recorded; M1 manuscript-concern support does not itself establish this E2E cycle | Phase 3 governance/publication lead |
| C-26 | G7 lock-free-completed-command-replay | tests/integration/phase2/test_pr2_19_dependencies.py:74 | deferred scope | "Owner decision pending: authorize production snapshot replay or defer §7 requirement"; production replay disposition remains pending | Owner; novelty/Application lead |
| C-27 | G7 strong-novelty | tests/integration/phase2/test_pr2_19_dependencies.py:83 | deferred scope | "Exact screening/comparison basis absent"; stale reason after B20 (see reconciliation below); gate evidence still requires reconciliation | Phase 3 novelty/test lead |
| C-28 | F1 automatic-finding-impact-propagation | tests/integration/phase2/test_pr2_19_dependencies.py:98 | deferred scope | "No automatic finding/impact propagation owner"; overlaps C-11 | Phase 3 governance lead |
| C-29 | F5c manuscript-reconsideration | tests/integration/phase2/test_pr2_19_dependencies.py:105 | deferred scope | "B10 release-only scope"; manuscript reconsideration remains outside this gate slice | Phase 3 governance/publication lead |
| C-30 | F6 manuscript-result | tests/integration/phase2/test_pr2_19_dependencies.py:107 | deferred scope | "Seventh action type deferred"; unavailable manuscript-result subcase requires reconciliation with M1 support | Phase 3 governance/publication lead |
| C-31 | F9 scheduled-role-expiry | tests/integration/phase2/test_pr2_19_dependencies.py:117 | deferred scope | "BLOCKED: no owning Application command to schedule role expiry (AQ-S2-02)"; credential/grant expiry and role revocation do not cover scheduled role expiry | Identity/Application owner |

G7 strong-novelty reconciliation: **(b) stale after B20**, because B20 §§3–4 delivered the bounded negative assessment's exact screening/resolution/comparison basis (`0070_b20_screening_basis`, `src/researchbase/domain/novelty.py:662`), using B22 §3 terminal-comparison rules, whereas `tests/integration/phase2/test_pr2_19_novelty.py:65` tests denial without that basis and does not establish positive G7 acceptance (universal priority and publication gates remain excluded by B20 §12.5).

## Totals per kind

| Kind | Count |
|---|---|
| owner-accepted gap | 4 |
| deferred scope | 23 |
| P3 finding | 4 |
| accepted P2 | 0 |
| **Total** | 31 |

Note: no row has kind "accepted P2": no source item is an accepted P2 finding (R2/R3 are P2 but were not in the requested list; R3 concerns exit-report evidence, not provider intake). The provider-intake item is an open owner decision, classed as deferred scope.
