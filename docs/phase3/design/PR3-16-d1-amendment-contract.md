# PR3-16 D1 atomic node-budget amendment — contract draft

Status: PROPOSED

Date: 2026-10-27. Scope: closeout item 8 only. Companion:
[ADR-0027](../../architecture/adr/ADR-0027-pr3-16-d1-node-budget-amendment.md).
This draft schedules no implementation and does not authorize production admission.

Disposition counts: **RESOLVED 14; OWNER 10; MISSING 10**. Counts cover C01–C14,
O01–O10 and M01–M10, once each. RESOLVED means a source establishes the stated
requirement or existing behavior, not that the amendment is approved or tested.
OWNER identifies an unanswered decision for the project owner and architecture
review. MISSING means no executable D1 check exists for the stated obligation;
describing an assertion supplies neither a test nor coverage.

## Source-established contract boundary

### C01 — RESOLVED — delivery authority and precedence

The owner selected a separate contract and PROPOSED ADR now, with no implementation
scheduled and production node admission denied until that contract is approved.
The atomic amendment remains unconditional before activation. The later explicit
answers override historical conditional/open wording in ADR-0026 and the pack;
ADR-0026 remains ACCEPTED. This document does not amend those answers or declare
closeout item 8 fully resolved. Sources:
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:3`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14`,
`docs/phase3/PR3-16-execution-pack-r2.md:499`,
`docs/phase3/PR3-16-design-closeout.md:15`,
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:3`.

### C02 — RESOLVED — accounting ownership and scientific boundary

Every session of a task shares existing PR3-04 accounting; there is no search
balance, counter reset or separate ledger. Human and Agent use Application →
port/UoW → persistence → PostgreSQL. Search keeps failed/pruned history and exact
Run links; it cannot create, execute, cancel or change a Run or establish scientific
validity. PR3-17 selection/scoring and execution/promotion remain excluded. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:54`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:61`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:78`.

### C03 — RESOLVED — conservative storage proof remains the baseline

An append requires a previously committed same-task reservation under the active
budget, `tree_nodes=1`, operation identity equal to node ID, unused by another node
and not finally settled. `observed_depth` must equal both actual search depth and
the reservation's task-step ancestor depth; NULL step permits only root depth zero.
Current clock/deadline, checkpoints, task stop and caps still apply. If proof fails,
deny. This is the storage rule to be explicitly amended, not an atomic API already
available. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:194`.

### C04 — RESOLVED — the committed-reservation gap is real

PR3-04 admits equality with an additive cap and records the resulting stop in that
reservation's event. A later storage append must deny after stop, even if the
reservation is charged. It can therefore leave a charged reservation without a
node. A new append after stop is not reconciliation; gaps are not refunded.
Sources: `docs/phase3/PR3-04-contract-freeze.md:567`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:189`.

### C05 — RESOLVED — trust definition and present implementation limit

A trusted producer is a registered consumer capability calling the TaskSafetyService
reservation path. TrustedFakeConsumer is test-only; no production producer exists.
The current service accepts an injected `FakeConsumerCapability` and checks object
identity. A public flag, actor type, evaluator string or possession of a reservation
ID does not supply that capability. These existing checks do not define a production
registration mechanism. Sources:
`docs/phase3/PR3-16-execution-pack-r2.md:502`,
`src/researchbase/agent_runtime/application/task_safety.py:238`,
`docs/phase3/PR3-04-contract-freeze.md:611`.

### C06 — RESOLVED — full vector shape, not a selected node vector

Existing `ResourceVector` requires `wall_time_seconds`, `agent_steps`, `llm_calls`,
`search_calls`, `code_iterations`, `experiment_runs`, `tree_nodes`, `gpu_hours` and
`token_cost`; no dimension is omitted. Reservation wall time is positive; count
fields are nonnegative integers and GPU/cost use exact finite nonnegative six-place
decimals. Adapter GPU/cost conversion rounds up under the existing accounting contract.
Only `tree_nodes=1` is selected for the conservative node proof. Neither zeroes for
the other dimensions nor a node deadline follow from that selection. The gateway's
fake vector has `tree_nodes=0` and cannot be reused as node spend. Sources:
`docs/phase3/PR3-04-contract-freeze.md:544`,
`docs/phase3/PR3-04-contract-freeze.md:775`,
`docs/phase3/PR3-04-contract-freeze.md:777`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`,
`docs/phase3/PR3-03-contract-freeze.md:1802`,
`docs/phase3/PR3-16-execution-pack-r2.md:45`.

### C07 — RESOLVED — shared charges, gauges and bounds

For each additive dimension, existing charged amount plus proposed amount must
not exceed the active budget's cap. Charge is final measured usage if present,
otherwise the full reservation. Wall time is database elapsed time from the first
reservation, including Human waits. Depth and parallelism are gauges, not additive
costs. Current reservation depth comes from task-step ancestors; occupancy is one
plus all not-final task reservations, including UNKNOWN. Search root depth is zero
and child depth is parent plus one. The approved initial read bounds are 10 nodes,
depth 3 and parallel branches 1, matching existing BudgetSpec defaults; they do not
define a node resource vector or a new meaning for search parallel branches.
Sources: `docs/phase3/PR3-04-contract-freeze.md:530`,
`docs/phase3/PR3-04-contract-freeze.md:555`,
`src/researchbase/agent_runtime/application/task_safety.py:122`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:58`,
`docs/phase3/PR3-16-execution-pack-r2.md:504`,
`docs/phase3/PR3-16-design-closeout.md:194`.

### C08 — RESOLVED — evaluator binding is required, not supplied

Positive node/code/run charges require a comparable evaluator. Existing
`TerminationSpec` binds `score_metric_version_id`, `score_direction` and
`evaluator_version` together; direction is MAXIMIZE or MINIMIZE. The metric must
pass the owning domain's scope and frozen-version checks. Successful settlement
of a positively charged node/code/run iteration requires a score; a provided score
requires the policy's exact evaluator version and SUCCEEDED outcome. This defines
validation, not the production evaluator's algorithm or identity. Sources:
`src/researchbase/agent_runtime/application/task_safety.py:159`,
`src/researchbase/agent_runtime/application/safety_contracts.py:139`,
`src/researchbase/agent_runtime/application/task_safety.py:460`,
`src/researchbase/agent_runtime/application/task_safety.py:207`.

### C09 — RESOLVED — progress and failure semantics

Existing failure history is per logical task step (NULL is the task-level step),
ordered by receipt revision. FAILED increments consecutive failures; SUCCEEDED
resets them; CANCELLED/PRUNED retain them and UNKNOWN does not advance them.
Comparable successful iterations alone update progress: the first score establishes
the baseline, strict improvement resets no-improvement, ties/worse increment it.
Comparisons do not cross steps, metrics or evaluators. Scores are operational, never
Measurements. Optional minimum-progress, duplicate, confidence and success
evaluators stay disabled pending their own approved contracts. Sources:
`docs/phase3/PR3-04-contract-freeze.md:574`,
`docs/phase3/PR3-04-contract-freeze.md:45`,
`src/researchbase/agent_runtime/application/safety_contracts.py:117`.

### C10 — RESOLVED — stop and execution gates remain binding

Stops are sticky historical OR of all recorded causes, with priority Human, policy,
budget, repeated failure, no improvement, success; success remains disabled in the
existing slice. Newly recorded termination is a successful event/receipt, not an
exception that erases the stop. Subsequent admission denies. Current reservation
code denies A2/A3 because owning execution prerequisites are unavailable. Verified
actor-only planning requires no AgentVersion/availability, but is not production
resource trust or execution authority. Sources:
`docs/phase3/PR3-04-contract-freeze.md:586`,
`src/researchbase/agent_runtime/application/task_safety.py:149`,
`docs/phase3/PR3-16-execution-pack-r2.md:512`,
`docs/phase3/PR3-16-execution-pack-r2.md:502`.

### C11 — RESOLVED — settlement preserves admitted counters

Existing trusted settlement owns accounting. Final measurements cannot exceed the
reservation; admitted integer counters, including tree nodes, cannot be refunded.
Variable time/GPU/cost may reconcile down only with trusted evidence. UNKNOWN
retains the entire vector and occupancy without advancing final streaks; at most
one final settlement follows, with no further observations after final. Settlement
after stop/cancellation is bookkeeping and cannot clear a stop. PR3-16 failure,
pruning, closure or Run linkage supplies no settlement/refund. Sources:
`docs/phase3/PR3-04-contract-freeze.md:530`,
`docs/phase3/PR3-04-contract-freeze.md:544`,
`docs/phase3/PR3-04-contract-freeze.md:567`,
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:39`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:203`.

### C12 — RESOLVED — atomic composition must preserve the command boundary

One Application command owns one synchronous transaction; failure rolls its effects
back. A nested public `reserve_task_budget` command is prohibited. The accepted
gateway has an internal in-UoW accounting composition that reuses safety rules
without another transaction, revision or receipt. It demonstrates a composition
pattern only: its fake trust, resource vector and lock helper do not constitute the
D1 node contract. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:198`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:215`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:251`,
`docs/phase3/PR3-03-contract-freeze.md:1778`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:13`.

### C13 — RESOLVED — receipt/replay and concurrency obligations

The storage append has one node and search event, one task revision increment,
receipt and task event/result link, using existing receipt tables. Current safety
reservation has one reservation and its own declared command effects. Combining
those requires an explicit amendment; neither existing shape silently permits
extra effects. Current entitlement precedes committed receipt replay, which
precedes fresh write/state/stop/expiry/CAS checks. Equal material recovers original
IDs with no effects; different material conflicts. Own uncommitted effects cannot
replay. Retain fresh validation after waits, writes and forced constraints and the
shared task coordination across sessions. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:174`,
`docs/phase3/PR3-04-contract-freeze.md:660`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137`,
`docs/phase3/PR3-16-execution-pack-r2.md:56`,
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:43`.

### C14 — RESOLVED — compatibility and approval boundary

The amendment must preserve old PR3-04 commands/vectors and scientific history;
no new ledger or unreviewed canonical schema is authorized. Exact inventory,
literal vectors and independent review precede implementation authorization.
This draft does not assign a migration revision, alter the other closeout items,
freeze F1 or accept ADR-0027. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:321`,
`AGENTS.md:49`, `AGENTS.md:164`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:3`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:18`.

## Decisions required for an approvable atomic amendment

### O01 — OWNER — production producer and trust composition

**Question:** which registered production consumer will call the TaskSafetyService
reservation path, and how are its registration, injected authority and revocation
validated inside the owning command's UoW? **Options:** review a concrete producer
and internal composition contract; or leave production admission denied while that
contract is unavailable. **Recommendation:** specify that contract before approval,
preserving object/capability trust and public denial; do not promote the fake or
call a public reservation command from another command. Sources:
`docs/phase3/PR3-16-execution-pack-r2.md:502`,
`docs/phase3/PR3-16-execution-pack-r2.md:52`,
`docs/phase3/PR3-03-contract-freeze.md:1778`.

### O02 — OWNER — evaluator identity, observations and meaning of success

**Question:** what exact frozen metric, direction, immutable evaluator version,
input provenance, computation and comparable observation define a node iteration,
and when can it truthfully be settled SUCCEEDED? **Options:** supply a reviewed
node evaluator compatible with C08–C09; or retain denial of positive node admission.
**Recommendation:** supply the evaluator contract and independent observation
vectors before approval. Node insertion alone does not supply a comparable score;
do not synthesize a constant score, a metric UUID or an evaluator version, use the
test evaluator as production, or enable deferred PR3-17 scoring. Sources:
`docs/phase3/PR3-16-design-closeout.md:258`,
`docs/phase3/PR3-16-freeze-inventory.md:255`,
`docs/phase3/PR3-04-contract-freeze.md:577`,
`tests/integration/phase3/test_pr3_04_accounting.py:138`.

### O03 — OWNER — full resource vector and deadline

**Question:** what operation does the node reservation cover, and what attributable
worst-case value or derivation supplies every C06 dimension, pricing basis and
deadline? **Options:** review the complete bounded producer vector and conversion
rules; or deny admission when an upper bound cannot be established.
**Recommendation:** retain the required node charge and specify every remaining
dimension explicitly with evidence. Existing defaults are policy caps, not node
spend; no zero-fill, fake price, gateway duration or new search deadline is chosen.
Sources: `docs/phase3/PR3-16-execution-pack-r2.md:52`,
`docs/phase3/PR3-04-contract-freeze.md:527`,
`docs/phase3/PR3-04-contract-freeze.md:539`,
`docs/phase3/PR3-16-execution-pack-r2.md:294`.

### O04 — OWNER — node-to-step depth and comparison scope

**Question:** which same-task step corresponds to a root/child node, and does the
atomic path retain the exact step/search depth equality or introduce a separately
reviewed node-aware derivation? How are same-step progress histories preserved
across sessions? **Options:** retain the equality proof with an explicit mapping;
or approve a node-aware rule with explicit compatibility for old reservations and
streaks. **Recommendation:** retain equality until a reviewed mapping establishes
the alternative. Do not invent steps, infer ancestry equality from matching depth,
or silently change the meaning of `observed_depth`. Sources:
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`,
`src/researchbase/agent_runtime/application/task_safety.py:122`,
`docs/phase3/PR3-04-contract-freeze.md:574`.

### O05 — OWNER — parallel occupancy and settlement timing

**Question:** how does a live node operation map to existing not-final reservation
occupancy, and when can the trusted producer release that occupancy by final
settlement? **Options:** retain reservation occupancy with an explicit node-operation
lifetime; or review an amendment to gauge derivation without changing old accounting
silently. **Recommendation:** retain the existing gauge pending a concrete lifetime
contract. The approved parallel bound does not establish that roots, all stored
nodes or Run links count as parallel branches. Sources:
`docs/phase3/PR3-04-contract-freeze.md:562`,
`docs/phase3/PR3-16-design-closeout.md:194`,
`docs/phase3/PR3-16-execution-pack-r2.md:52`.

### O06 — OWNER — atomic receipt effects and command identity

**Question:** which reviewed command envelope owns reservation plus node admission,
what exact receipt/event/result pointers and guards prove all-or-none effects, and
how does it coexist with the conservative append envelope? **Options:** separately
define an atomic command contract while preserving the storage command; or review
an explicitly versioned extension with compatibility and replay rules.
**Recommendation:** specify the combined effect manifest first, using existing
receipt/accounting families and one owning transaction/revision/receipt/task event.
Reservation plus node plus search event is the candidate composition for review;
no command name, new event literal, SQL identifier or result layout is assigned.
Sources: `docs/phase3/PR3-16-execution-pack-r2.md:52`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:174`,
`docs/phase3/PR3-03-contract-freeze.md:1778`,
`docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md:326`.

### O07 — OWNER — equality, stop ordering and session closure

**Question:** how does atomic admission distinguish a prior stop from the stop
caused by its own last-unit reservation, while preserving post-wait validation?
Does budget stop only block later work, or also produce an explicit session closure
effect? **Options:** review admission of the node with its last-unit charge and
durable task stop, with session closure remaining an explicit command; or review
an additional closure effect and its exact receipt/lifecycle implications.
**Recommendation:** the former, subject to review of the complete stop/effect
matrix. Preserve denial for prior stops and the existing conservative gap rule;
do not import the gateway's special start exception or treat all stops as ignorable.
Sources: `docs/phase3/PR3-04-contract-freeze.md:567`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:102`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:189`,
`docs/phase3/PR3-03-contract-freeze.md:1817`,
`docs/phase3/PR3-16-execution-pack-r2.md:52`.

### O08 — OWNER — attributable settlement owner and recovery

**Question:** which registered consumer owns node reservation settlement, what
evidence establishes completion/UNKNOWN/final reconciliation, and how is ownership
recovered after a crash or lost response? **Options:** assign a reviewed trusted
consumer to the existing settlement path; or retain charges and denied production
admission pending that assignment. **Recommendation:** specify responsibility and
evidence without granting PR3-16 terminal commands settlement authority. Preserve
integer charges, one final record and sticky stops; an existing Run link alone
cannot prove execution under the reservation. Sources:
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:39`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:201`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:203`,
`docs/phase3/PR3-04-contract-freeze.md:530`.

### O09 — OWNER — lock, guard and compatibility delta

**Question:** what exact per-caller coordination, post-write callbacks, changed and
unchanged guard bodies, privilege restrictions and receipt recovery mapping admit
the combined effects without weakening existing 0081 or safety behavior?
**Options:** review a complete D1 delta against the related Q1/Q2/Q7 designs; or
leave atomic admission unavailable. **Recommendation:** require the explicit delta,
preserving old command hashes/effects and historical reservations, with no new
ledger or implicit gateway lock composition. Migration identity and any forward
compatibility/rollback procedure remain unassigned here. Sources:
`docs/phase3/PR3-16-execution-pack-r2.md:50`,
`docs/phase3/PR3-16-execution-pack-r2.md:56`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:8`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:321`.

### O10 — OWNER — approval and evidence disposition

**Question:** after O01–O09 are answered, does the owner and architecture review
approve the complete separate contract and ADR with independent assertion/vector
review? **Options:** review that complete package before any separate implementation
authorization; or keep it PROPOSED with production admission denied.
**Recommendation:** keep the present draft PROPOSED until those decisions and
reviews exist. Approval is not supplied by baseline regressions or by drafting an
ADR. No implementation date, PR assignment or activation is scheduled. Sources:
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:18`,
`docs/phase3/PR3-16-execution-pack-r2.md:533`.

## Missing D1 checks

These are assertion requirements for review, not invented test names or an execution
schedule. The existing safety tests cover the earlier accounting contract; they
cannot establish atomic node behavior. All rows are NOT RUN for D1.

| Item | Status | Absent check and required observable evidence | Sources |
| --- | --- | --- | --- |
| M01 | MISSING | The proposed `tests/integration/phase3/test_pr3_16_budget.py::test_cross_session_caps_depth_gaps_and_terminal_no_refund` is absent. It must prove conservative proof/denial, shared caps, depth, charged gaps and no terminal refund; it cannot prove the atomic amendment. | `docs/phase3/PR3-16-design-closeout.md:274`, `docs/phase3/PR3-16-freeze-inventory.md:294`. |
| M02 | MISSING | Atomic admission, rollback and uncertain-commit recovery: establish the approved complete effect set, no partial new reservation/node/history, and original-ID recovery without a second charge. Count actual rows, revision and receipts across failures at each persistence stage. Exact atomic effect expectations depend on O06. | `docs/phase3/PR3-16-execution-pack-r2.md:52`, `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137`, `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:251`. |
| M03 | MISSING | Production trust and evaluator admission: positive control only for the approved registration/evaluator; reject forged public trust, missing/incomparable evaluator, unscoped/unfrozen metric and unverified callers with no effects. No production identity/vector fixture is approved. | `docs/phase3/PR3-16-execution-pack-r2.md:502`, `docs/phase3/PR3-16-execution-pack-r2.md:86`, `src/researchbase/agent_runtime/application/task_safety.py:159`, `src/researchbase/agent_runtime/application/task_safety.py:460`. |
| M04 | MISSING | Full node-vector and deadline checks: independently specified literals, every additive dimension below/equal/above cap, exact decimal conversion, UNKNOWN retention and deadline/wall-clock denial. O03 must supply the operation-specific expected values; fake gateway constants are not a fixture. | `docs/phase3/PR3-16-freeze-inventory.md:255`, `docs/phase3/PR3-04-contract-freeze.md:530`, `docs/phase3/PR3-04-contract-freeze.md:544`, `docs/phase3/PR3-04-contract-freeze.md:555`. |
| M05 | MISSING | Atomic depth/occupancy mapping: root/child and NULL/non-NULL step controls, wrong task/depth/operation/reservation rejection, cross-session totals and UNKNOWN occupancy. Expectations await O04–O05; equal numeric depth is not proof of an unspecified node-to-step mapping. | `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`, `src/researchbase/agent_runtime/application/task_safety.py:122`. |
| M06 | MISSING | Atomic stop races: actual PostgreSQL competing last-unit admissions, stop/admission and checkpoint expiry/revocation waits; fresh post-wait checks, sticky causes and exact approved equality/closure effects. Prior stop must still deny, including for a charged gap. O07 and O09 must settle the combined trace. | `docs/phase3/PR3-16-execution-pack-r2.md:56`, `docs/phase3/PR3-04-contract-freeze.md:567`, `docs/phase3/PR3-04-contract-freeze.md:1005`. |
| M07 | MISSING | Node evaluator/settlement end-to-end checks: attributable success score, first/tie/worse/improvement, step isolation, missing/mismatched observations, failure/prune/cancel counters, UNKNOWN then one final reconciliation, no post-final observation and no reset after stop. O02/O08 must supply actual observation provenance and recovery assertions. | `docs/phase3/PR3-04-contract-freeze.md:530`, `docs/phase3/PR3-04-contract-freeze.md:574`, `docs/phase3/PR3-16-execution-pack-r2.md:52`. |
| M08 | MISSING | Ordinary-role SQL attacks on the combined effect set: missing/extra effects, old receipt reuse, duplicate reservation/operation use, multiple flushes and immutable history mutation. Existing safety guards do not prove a future D1 guard delta or its PostgreSQL compilation. | `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:174`, `docs/phase3/PR3-04-contract-freeze.md:620`, `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:8`. |
| M09 | MISSING | Compatibility across the future amendment: unchanged old safety/gateway vectors and accepted guards, preserved historical receipts, scientific hashes/Run seals and retained failed/pruned lineage. Existing tests can supply baseline regressions, but no amendment or upgrade exists to compare. | `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:64`, `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:321`, `docs/phase3/PR3-16-execution-pack-r2.md:296`. |
| M10 | MISSING | Atomic command material/results/errors: independent literal input/bytes/digest/result vectors, equal versus changed-material replay, current read entitlement before replay, fresh authority/CAS/stop denial and multi-failure precedence. O06 must define the envelope; no new literal or pytest identifier is asserted here. | `docs/phase3/PR3-16-execution-pack-r2.md:51`, `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:130`, `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137`, `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10`. |

## Verification record

Measured on 2026-10-27 with CPython 3.12.15 and pytest 8.4.2 on Darwin. The provided
lane checkout's HEAD and `design-pr316` both resolve to
`20b718f2e60e4e4e33b4e9567eb2f1065e272b9b`; no branch was created or changed.
Only the two deliverable Markdown files are added. No code, migration, test,
dependency definition or owner decision changes. Results below are existing
baseline regressions, not D1 acceptance; static tools do not validate this proposed
contract's semantics.

Each `uv` command below used the exact prefix
`UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.

| Command (with the stated prefix for `uv`) | Observed result | Exit |
| --- | --- | --- |
| `uv sync --locked --group dev` | Resolved 38 packages; prepared and installed 34 | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `948 files already formatted` | 0 |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations`; separate available-version notice v1.1.411 → v1.1.414 | 0 |
| `uv run pytest -o addopts='' -ra tests/unit/phase3 tests/architecture tests/unit/architecture` | Collected 1436; **1436 passed**, 0 failed/errors/skipped; 50 Alembic `path_separator` deprecation warnings; 34.20s | 0 |
| `git diff --exit-code design-pr316 HEAD` | No output; checkout commit tree equals requested base | 0 |
| `git diff --check` | No output | 0 |
| `git diff --no-index --check -- /dev/null docs/phase3/design/PR3-16-d1-amendment-contract.md` | No whitespace diagnostics; exit 1 denotes the new-file difference | 1 |
| `git diff --no-index --check -- /dev/null docs/architecture/adr/ADR-0027-pr3-16-d1-node-budget-amendment.md` | No whitespace diagnostics; exit 1 denotes the new-file difference | 1 |

The extra no-index checks include the untracked deliverables, which ordinary
`git diff --check` does not inspect. A read-only citation/disposition audit checked
163 file:line references for existing files and nonblank in-range lines, confirmed
the stated counts and a question/options/recommendation for every OWNER item.
That mechanical audit does not establish semantic correctness or review approval.
The cited proposed search budget test is absent, and the repository search found
no PR3-16/search implementation or test file under `src` or `tests`.

PostgreSQL suites: **NOT RUN (0 invoked)**. These two proposed documents change no
database behavior or PostgreSQL suite; no D1 implementation exists to exercise.
In particular, existing PostgreSQL accounting/evaluator tests are cited as source,
not reported as executed in this task. Whole suite: **NOT RUN** by this task; the
external loop owns that run and its output is not available here. D1 checks
M01–M10 remain MISSING / NOT RUN, and independent review/approval remains pending.
