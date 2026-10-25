# PR3-02-S2 execution pack review

Review subject: `docs/phase3/PR3-02-S2-execution-pack.md`, at HEAD
`dd30a22f1a8ec8c62a00184bbab3ae171d87e399`. Documentation review only;
the pack, ADR, contracts and code are unchanged. Source locations below are
repository-relative and refer to this checkout. The verdict assesses the pack
as a planning document, consistent with its lines 1–12, not as an implementation
contract or authorization.

## Finding

### P2 MINOR — Proposed predecessor gates require later-stage behavior

- **Pack location:** lines 110–111, 120, 128–129 and 206, together with the
  test definitions at lines 188, 198 and commands at lines 212, 215, 217.
- **Source/rule:** `AGENTS.md:128–141` requires actual evidence before completion
  and forbids converting not-run checks to PASS;
  `docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:401–419`
  requires meaningful focused PostgreSQL/application/concurrency verification.
  The pack's own line 206 additionally prohibits downstream implementation until
  predecessor evidence exists.
- **Evidence:** S1 requires D4's Python/PostgreSQL material parity before S2
  implements the Python values/hash material. S2 points to the focused unit
  command, which also names the execution/promotion service tests allocated to
  S4/S5. S3 requires the concurrency command including R2's promotion races,
  although promotion is implemented in S5, which depends on S3/S4. Consequently
  the strict progression rule cannot be followed literally while obtaining all
  stated stage-completion evidence.
- **Impact:** a future implementer must either cross a declared predecessor gate
  or leave that gate incomplete. This does not authorize implementation today
  and does not undermine the approved scientific contract, so it is a planning
  defect rather than a P0/P1 blocker for this expressly non-frozen document.
- **Action:** before freezing the execution plan, allocate each stage only the
  checks whose dependencies exist then. Retain deferred parity/service/promotion
  race obligations explicitly for the first applicable later stage and S7;
  update the exact commands and progression wording together. Do not count
  placeholders, missing nodes or required skips as passing evidence.

## Required scope and seam checks

- **PR3-03 acceptance:** pack lines 31 and 33–37 agree with
  `docs/phase3/PR3-03-evidence.md:7331–7349`: owner acceptance followed PR #8;
  final code-head CI succeeded; 14,179 passed / 66 skipped / 0 failed belongs
  to an earlier local head, not S2 or the final CI counts. The acceptance does
  not claim S2 execution readiness. Its documented performance limits remain
  limits; the pack makes no contrary performance claim.
- **Delivered gateway seam:** pack lines 33–34, 37 and 45–46 correctly preserve
  CONTRACT_FAKE and the disabled task/step gate, distinguish task→actor→version
  gateway keys from S2's actor→task→version→execution order, and identify the
  accounting seam as internal and identity-trusted. Evidence:
  `docs/phase3/PR3-03-contract-freeze.md:29,58–66,1661–1705,1770–1793`;
  `src/researchbase/persistence/capability_gateway_repository.py:93–131`;
  `migrations/versions/0080_capability_gateway.py:5–6,166`.
  No public execution authorization or composable lock recipe is presumed.
- **PR3-04 acceptance and safety seam:** pack lines 22, 32–33, 45, 51–52 agree
  with `docs/phase3/PR3-04-acceptance.md:3–10,23–38`. They preserve the
  green-head-CI condition, correctly identify the runs/head without inventing
  counts, and do not transfer the owner review waiver or PR3-05 saving decisions
  to S2. Policy/checkpoint groundwork does not enable execution, as confirmed
  by `docs/phase3/PR3-04-contract-freeze.md:30–44,611–618`.
- **S1 compatibility:** pack lines 16, 29–30, 36 and 239 preserve the distinct
  enrollment locking amendment and pending production verifier intake. These
  match `docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:18–27`
  and `docs/phase3/PR3-02-S1-evidence.md:22–44,123–141,538–541`. Application-only
  B02 Agent evidence is not presented as an S2 execution.
- **D302-03..05 and schema allocation:** pack lines 16–21, 58–77 and 108 retain
  staged execution, two atomic B02 DRAFT families, separate producer/promoter,
  four S2 tables and extensions to existing receipts. These match
  `docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:13–16`
  and `docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:35–48,193–207,235–252,425–427`.
  A mechanical comparison found exactly 23 entries in pack lines 65–71 and
  draft lines 297–303, with identical ordered names. The S1 enrollment amendment
  is not silently applied to S2. No ninth PR3-02 table, fingerprint entity or
  generic target core is proposed.
- **Owning promotion and read-only context seams:** pack lines 38–39, 50–51,
  144–149 and 153–158 correctly identify B02's transaction-owning wrapper and
  retained-byte I/O as extraction concerns, and PR3-05's validator as explicitly
  S2-unverified. Evidence:
  `src/researchbase/application/strategy_candidate_promotion.py:366–422,602–618,660–758`;
  `src/researchbase/persistence/strategy_candidate_promotion_repository.py:46–53`;
  `src/researchbase/agent_runtime/application/promotion_context.py:98–103`;
  `tests/integration/phase3/test_pr3_05_promotion_validation.py:51–59`.
  The pack does not claim these seams already provide atomic S2 provenance.
- **Questions versus decisions:** pack lines 43–52 isolate Q1–Q8; lines 96–104
  and 225 block dependent implementation/shipping until disposition and freeze.
  Approved D302 decisions remain fixed. Exact activation, persistence, vectors,
  authority, producer attribution and integration details remain unresolved,
  consistent with the draft at lines 383 and 425–431. An unresolved planning
  question is not itself a contradiction or an implicit decision.
- **Authorization:** pack lines 4, 12, 52, 60, 96, 102–104, 206 and 253 expressly
  withhold implementation authorization, consistent with ADR-0023 lines 3–5.
  Future imperative steps are conditional proposals. This review grants no
  implementation, DDL, activation, acceptance or contract-change authorization.

## Verification

Commands executed from the repository root; every command below exited 0:

```sh
UV_CACHE_DIR="$PWD/tmp/review-uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/tmp/review-uv-cache" uv run ruff format --check .
UV_CACHE_DIR="$PWD/tmp/review-uv-cache" uv run pyright
UV_CACHE_DIR="$PWD/tmp/review-uv-cache" uv run pytest -o addopts='' -ra tests/unit/phase3/test_agent_version_contracts.py tests/unit/phase3/test_harness_manifest.py tests/unit/phase3/test_capability_gateway_contracts.py tests/unit/phase3/test_task_safety_contracts.py tests/architecture/test_pr3_02_s1_boundaries.py tests/architecture/test_pr3_03_boundaries.py tests/architecture/test_pr3_04_boundaries.py
```

Observed results, respectively: `All checks passed!`; `931 files already
formatted`; `0 errors, 0 warnings, 0 informations` (plus a Pyright version
notice); `220 passed, 1 warning in 1.06s` from 220 collected items. The warning
is the existing Alembic `path_separator` deprecation. These are review-turn
regression checks, not positive S2 execution evidence.

PostgreSQL suites: NOT RUN; this review changes no executable, migration or
database contract and touches no PostgreSQL suite. Full suite: NOT RUN; owned
by the external check loop. No results from that loop are assumed.

No P0 BLOCKER or P1 MAJOR findings. One P2 MINOR finding remains for planning
refinement before an implementation-ready freeze.

VERDICT: PASS (no P0/P1)
