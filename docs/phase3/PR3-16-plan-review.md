# PR3-16 implementation-plan review

Review date: 2026-10-25. Review base: `d744074cfc0cf2fd1fbc6d155bea1353b6078541`.
Reviewed the supplied plan directly at
`.pipeline/work/lane133/docs/phase3/PR3-16-implementation-plan.md`, resolved from
the ResearchBase project directory. It was not copied or edited. All plan line
references below refer to that document, whose stated baseline is `fb734e6`.
Source references refer to this review checkout. Historical observations at the
plan's older baseline are distinguished from current acceptance evidence.

## Findings

### P2 MINOR — Refresh the prerequisite acceptance inventory for the review base

- **Plan lines:** 10–16, 91, 99–116, 509 and 547–548. The plan preserves a
  missing-acceptance discrepancy for PR3-03 and makes reconciling it part of G0;
  it identifies PR3-04 as necessary without assessing its acceptance record.
- **Sources omitted:** `docs/phase3/PR3-03-evidence.md:7331` begins Final
  acceptance; `docs/phase3/PR3-03-evidence.md:7333` records owner acceptance;
  `docs/phase3/PR3-03-evidence.md:7336` identifies successful final-code-head CI
  runs. `docs/phase3/PR3-03-evidence.md:7349` explicitly says the acceptance
  prerequisite for PR3-16 planning is satisfied.
  `docs/phase3/PR3-04-acceptance.md:3` records conditional owner acceptance;
  `docs/phase3/PR3-04-acceptance.md:24` identifies CI runs and their head;
  `docs/phase3/PR3-04-acceptance.md:31` records the owner's review waiver.
- **Rule violated:** prerequisite evidence must be assessed from the designated
  authoritative acceptance sources, rather than stopping at an earlier NOT RUN
  paragraph; see `AGENTS.md:128` and `AGENTS.md:158`. This is an omission when
  using the plan on the review base, not evidence that its explicitly historical
  observation was fabricated.
- **Impact:** a now-satisfied PR3-03 planning prerequisite remains apparently
  unresolved, and PR3-04's actual acceptance conditions are missing from the
  dependency handoff. This does not enable unsafe execution: G0 still blocks it.
- **Action:** in a separately authorized plan refresh or execution pack, record
  both acceptance sources, distinguish their recorded heads and conditions from
  the next execution head, and retire the stale PR3-03 discrepancy. Preserve
  PR3-16's independent owner-decision/ADR/pack/authorization requirements. Do not
  invent current CI results or treat historical test totals as new verification.

No P0 BLOCKER or P1 MAJOR finding was identified.

## Dependency checks

| Claimed seam and plan lines | Source check and result |
| --- | --- |
| PR3-03 accepted prerequisite, 10–16 and 99 | Accepted in the designated Final acceptance section (`docs/phase3/PR3-03-evidence.md:7333`). Its recorded CI is on `c5a91ba`, merged by `fb734e6`; the older local gate precedes subsequent changes (`docs/phase3/PR3-03-evidence.md:7335`). Finding above covers the stale inventory. |
| PR3-03 D303-04 accounting, 86, 112 and 330–352 | Supported. `docs/phase3/PR3-03-evidence.md:2061` records shared safety calculations; `docs/phase3/PR3-03-contract-freeze.md:1778` defines the internal in-UoW seam without transaction/revision/receipt ownership. Object-identity trust is required at `docs/phase3/PR3-03-contract-freeze.md:1789`; tree nodes remain zero at `docs/phase3/PR3-03-contract-freeze.md:1802`. Actual implementation is `src/researchbase/agent_runtime/application/capability_gateway.py:127`, with identity checks at line 132 and fixed fake resources at line 159. The plan correctly refuses to reinterpret an invocation as a search-node admission. |
| PR3-03 replay, wait checks and per-write cadence, 90, 113, 335–338 and 519–536 | Supported. `docs/phase3/PR3-03-evidence.md:2044` specifies entitlement/committed replay after acquisitions; line 2046 requires checks after DML and constraint forcing; line 2050 bounds transient retries. Actual callbacks are at `src/researchbase/agent_runtime/application/capability_gateway.py:841`, line 901 and line 1070. The own-uncommitted-effect exclusion is supported by `docs/phase3/PR3-03-evidence.md:2066`. The plan preserves the cadence and does not generalize the gateway's own-stop exception to conservative search admission. |
| PR3-03 performance and CI lessons, 521–571 | Supported as historical samples and proposed verification techniques. Final acceptance explicitly preserves the quadratic per-write limitation and says CI deadline margin was not measured (`docs/phase3/PR3-03-evidence.md:7345`). It records the fixture fixes at lines 7340–7341. The plan labels JIT attribution unverified and does not promise a latency bound. Its acceptance-evidence omission is covered above. |
| PR3-04 prerequisite and safety calculations, 79, 86, 101–103, 111 and 319–352 | Acceptance record identifies the delivered budget/checkpoint groundwork (`docs/phase3/PR3-04-acceptance.md:8`); its conditions are covered by the finding. Technical limitations are accurate: task-step ancestry supplies depth (`src/researchbase/agent_runtime/application/task_safety.py:122`), A2/A3 reserve admission is denied (line 149), and positive tree-node charges require an evaluator (line 160). The draft's committed-reservation proof, stop denial and charged gaps are explicit at `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`. Neither accepted groundwork nor D303-04 supplies a ready node-aware admission API. |
| PR3-01/04 lock composition, 109 and 253–285 | Supported by `src/researchbase/persistence/task_safety_repository.py:55` (SHARE/project/command/task prefix) and line 70 (task/step rows). The broader safety helper locks checkpoints at line 86. The plan correctly distinguishes that helper from the draft's immutable safety-read recipe (`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:238`), leaving Agent key composition open under Q7 rather than asserting incompatible locks are already composed. |
| Shared writer/formal-read UoW and PR3-04 projection, 114 and 382–410 | Supported. Current locations are `src/researchbase/persistence/uow.py:646` for READ COMMITTED and line 661 for REPEATABLE READ READ ONLY. `src/researchbase/agent_runtime/application/task_safety.py:692` opens the public safety query's read UoW; line 700 defines `safety_projection`. Composing that projection in the search read UoW avoids a second snapshot, as the draft requires at `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:261`. Some plan code citations reflect its older baseline; they should be refreshed with the inventory. |
| PR3-05 | The plan claims no PR3-05 consumer dependency and schedules no memory/save/promotion implementation. `docs/phase3/PR3-05-readonly-acceptance.md` is **absent on this base**. The similarly named slice evidence is not substituted as acceptance: `docs/phase3/PR3-05-readonly-slice-evidence.md:20` explicitly leaves whole-suite/G3 acceptance pending and excludes saving, D1/D2 and full PR3-05. Its demonstrated one-snapshot behavior at line 27 is consistent with the proposed read recipe, but does not authorize additional consumers. PR3-04 acceptance also excludes full PR3-05 at `docs/phase3/PR3-04-acceptance.md:38`. No unsupported accepted PR3-05 seam is claimed. |

## Draft-detail and scope audit

**Invented draft contract details presented as decided: none found.** The six
commands, three queries, four tables, limited lifecycle, Run relation
cardinality, saved hashes, budget proof and lock/read recipes have direct draft
support: `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:95`, line 119,
line 150, line 104, line 324, line 162, line 184 and line 215 respectively.

Details added by the plan, rather than frozen by the draft, are explicitly
identified and remain proposals or owner questions:

- Module/fixture/test filenames and node IDs, S1–S8 sequencing, two-round
  estimates, common gates and evidence organization (plan 24–29, 174–211).
- Full constraint/helper/index inventory, exact DTO/vector/error precedence,
  strategy pinning, and any atomic accounting amendment (plan 84–86).
- Historical reconciliation cutoff proof, duplicate-branch semantics and
  consistency between optional version references (plan 87–88).
- Pagination/size bounds, corrupt-ancestry handling, AgentVersion lock/proof
  composition, revision assignment and transport/release inventory (plan 89–91).
- Performance measurement strategy and proposed preservation checks, without
  invented latency thresholds or a search-node cap (plan 459–472, 529–536).

These additions are not misattributed as existing draft identifiers or admitted
semantics. Draft line 16 explicitly warns that its identifiers are proposals;
draft line 20 implies no transport path, SQL helper or test filename. The plan
honors that distinction. The draft's broader lifecycle staging still requires
owner approval; a review PASS does not approve it.

The PR boundary is preserved: the specification assigns session/node/lineage to
PR3-16 (`docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md:2568`)
and Experiment Manager decisions to PR3-17 (line 2572). The plan excludes ranking,
selection, scoring evaluation, SearchDecisionRecord and execution at lines
61–69. Retention and scientific-truth limits agree with specification line 1296.
The duplicate-branch test requirement at specification line 2327 is surfaced as
Q5 rather than silently replaced with an invented fingerprint algorithm.

## Owner decisions and authorization

Open questions are clearly separated from requirements: plan lines 71–95 label
all D1–D5 and Q1–Q8 **OPEN**, identify inferred questions, and forbid filling gaps
from the plan. G0 at line 509 requires their resolution, ADR/schema admission, a
reviewed execution pack and separate implementation authorization. This follows
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:12` and its decision table
at line 317. No owner decision was resolved by this review.

The plan **only plans implementation**. Lines 35–38, 158–164, 208–211 and
502–505 explicitly withhold implementation authority. Future command listings
and proposed gates are not executed evidence. PASS here means no P0/P1 in this
documentation review, not contract approval, PR acceptance or permission to
implement PR3-16/17.

## Review verification scope

Only this review file is written. The plan, draft, accepted evidence and code
remain unchanged. Required verification commands are `git diff --check HEAD`
and `test -s docs/phase3/PR3-16-plan-review.md && echo review-present`; their raw
outputs and exit codes are reported with the handoff. An additional untracked
file whitespace check inspects this file because ordinary Git diff omits it.
Runtime static tools, unit, architecture, migration and PostgreSQL tests are
**NOT RUN**: this documentation-only review touches no executable behavior or
database suite; there are no test counts to report. The whole suite is left to
the external check loop, as instructed. Source acceptance results cited above
were read, not rerun.

VERDICT: PASS (no P0/P1)
