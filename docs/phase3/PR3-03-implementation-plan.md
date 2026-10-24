# PR3-03 implementation plan

Planning baseline: `codex/phase3-wave3-base`, HEAD
`8b52c74bf03fb72a2b589fbbb030492c2ebb8871`.
Authority: repository `AGENTS.md`, architecture 01/02/03/08, Phase 3
§§7–9/40–41/both §85 sections, Harness 09, and
[PR3-03 execution pack](PR3-03-contract-freeze.md), read through §12.
PR3-01 §4, PR3-04 §§3.3/4/5.2 and PR3-02-S1 §4 supply the delivered lock,
accounting and replay conventions. Section numbers below refer to PR3-03 unless
another document is named. This file plans work; it does not implement or verify
the gateway. The owner's task instruction establishes pack freeze and implementation
authorization despite the pack's historical `PACK DRAFT` status text. This turn
is authorized for documentation only.

## 1. Verdict and evidence

**Implementable as written on the inspected baseline; no demonstrated pack/source
blocker.** PostgreSQL compilation and behavior are unverified, not assumed to pass.
S1 is the mandatory compile gate. A future failure must be reported with its actual
diagnostic and the exact conflicting text, not relabeled a general “§7 gap.”
The reported t220 migration is absent from this clean baseline; do not restore
that attempt without checking it against the complete frozen pack.

The following comparisons resolve likely mistaken blocker claims. Paths and line
numbers identify delivered source at the baseline above; quotations are literal.

| Concern | Pack text | Delivered source and consequence |
| --- | --- | --- |
| Where registry/parameter bytes are validated | §4.4: “Registry entry eligibility, retained-byte canonical JSON validation, requested parameter hash versus byte content, and identity-based FakeConsumerCapability are Application obligations in §§6–8” | `migrations/versions/0077_research_task_graph.py:452–454`: `SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project` and `FROM artifact_versions v JOIN artifacts o ON o.id=v.artifact_id WHERE v.id=p_artifact;`. This helper validates owning pins, not retained bytes. Implement Application preflight; no missing SQL registry API is assumed. |
| Artifact byte size | §7.1: “parameters_byte_size must equal owning artifact_versions.byte_size (non-NULL) and verified retained bytes length.” | `migrations/versions/0006_artifact_version.py:42`: `sa.Column("byte_size", sa.BigInteger(), nullable=True),`. Existing nullable storage permits rejecting NULL for gateway admission; no schema change to ArtifactVersion is needed. |
| NFC and canonical hashing | §7.1: “Normalize NFC first (helpers do not normalize)” | `src/researchbase/foundation/canonical_json.py:14–16`: “Unicode code points are preserved (no normalization is performed)” and “Callers must normalize non-JSON-native values before invoking this function.” Lines 22–25 supply `ensure_ascii=False`, sorted keys, compact separators and `allow_nan=False`. §7.1a also matches the integer-only SQL number branch at `0078_task_safety_policies.py:311–315`. Closed validation precedes these helpers. |
| New capability-set/policy serialization | §7.1a: “The validator must reconstruct policy material from the typed rows with this exact SELECT” | `migrations/versions/0078_task_safety_policies.py:298–299`: `CREATE FUNCTION pr304_canonical_policy_json(p_value jsonb) RETURNS text` / `LANGUAGE plpgsql IMMUTABLE STRICT AS $$`. The pack supplies the new reconstruction SELECT; this existing serializer and built-in SHA-256 are sufficient. |
| Shared lock recipe | §5: “The existing safety repository's combined lock_write cannot simply be called and followed by pr302 locks: compose the prefix” | `src/researchbase/persistence/task_safety_repository.py:60–65` takes `pr301:command`, `pr301:task`, then `SELECT id FROM research_tasks WHERE id=:id FOR UPDATE`; `agent_version_repository.py:78/80` takes `pr302:actor` / `pr302:version`. Factoring before row locks is explicitly authorized work, not a contradiction. |
| Reusing accounting | §6: “Neither owns begin/commit/rollback, reacquires locks, increments task revision, inserts a second receipt/event, nor calls TaskSafetyService.execute.” | `src/researchbase/agent_runtime/application/task_safety.py:166–174` opens a UoW and locks; lines 591–606 write the task and receipt; lines 640–642 force constraints and commit. Calling that public command would violate the pack. Factor its reserve/settle calculations into the internal seam instead. |
| Existing constraints reject new commands | §4.5 explicitly adds gateway reservation/usage owners while retaining old cases | `migrations/versions/0078_task_safety_policies.py:363`: `WHEN 'budget_reservations' THEN ARRAY['reserve_task_budget'] WHEN 'budget_usage_records' THEN ARRAY['settle_task_budget']`; lines 678/680 restrict their effect counts. The complete forward replacements remove this expected incompatibility in 0080 without editing 0078. |

Source dependencies also checked: all bodies in migrations 0077/0078/0079;
`research_task_repository.py:104–126` saved receipt/result lookup;
`task_safety_repository.py:111–132` receipt-owned safety results;
`agent_version_repository.py:54–90` version/actor coordination;
`uow.py:633–660` write/formal-read setup, `848–879` diagnostics and
`1311–1331` startup timeouts/UoW factory. Existing `23505` normalization is generic
VALIDATION_ERROR (`uow.py:861`); §9 requires a narrowly scoped new-identity mapping
in the gateway path. This is an implementation delta, not a frozen-code blocker.

## 2. Rules shared by every sub-task

Scope remains CONTRACT_FAKE only, five new pattern tables, four commands and
three queries. Preserve task/step lifecycles, old hashes/results, immutable history
and `execution_enabled=false`. No S2 execution identity, real provider, transport
activation, SDK, queue, process/network execution, scientific promotion, new
dependency or governing Harness change. HTTP/CLI additions are optional in §8
and are omitted from this implementation plan.

**Stop rule G:** An agent must not stop with a claimed gap unless it quotes the
conflicting pack text and delivered `path:line` source text side by side, explains
why the prescribed forward changes cannot resolve it, and states the blocked
observable check. If only part is blocked, implement and verify the independent
remainder and record a **Deviation** with scope, evidence, impact and needed
disposition. Do not invent contract semantics to proceed. Environment failures
are NOT RUN/blocked verification, not architecture gaps. Never declare an affected
gate passed with missing evidence or an open P0/P1. Carry Deviation records in the
sub-task handoff and collect them in S8's evidence file.

**SQL rule L:** `pyproject.toml` sets line length 100. Use one named raw multiline
SQL constant per DDL statement, trigger statement or complete function definition;
wrap SQL clauses, column lists, predicates and RAISE diagnostics to at most 100
physical source characters. A PL/pgSQL definition remains one executable string;
never split it on internal semicolons. Execute constants in dependency order.
Use parameterized SQL and wrapped multiline constants for repository queries too.
Preserve regex backslashes, quoted literals, whitespace inside material values and
hash-vector bytes. Naming a constant alone does not fix E501: wrap its contents.
Do not add `noqa: E501`, lint exclusions, or change lint configuration. Existing
ancestor exemptions do not authorize new exemptions. Format changed Python files,
then run repository-wide lint and format checks; Ruff does not wrap SQL literals.

**Evidence rule:** Each sub-task supplies its diff, exact commands, stdout/stderr,
exit codes and actual pytest collected/passed/failed/skipped counts. Counts below
are minimum planned cases, not observed results; parameterization may increase
them. No zero-test selection or required skip is acceptance. Keep raw outputs in
ignored `tmp/pr3-03/` for later inclusion in S8. Each handoff identifies the next
sub-task and unresolved Deviations. No full-suite run by the implementation agent;
the external loop owns the six-shard gate in §9.1.

Common implementation gate C, run after every sub-task (not during this planning
turn):

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
```

Require exit 0 for each command, no Pyright errors, and the sole head output
`0080_capability_gateway (head)`. Run `uv sync --locked --group dev` once at
implementation setup; do not change `pyproject.toml` or `uv.lock`. PostgreSQL
commands require an explicitly selected disposable local PostgreSQL 18 admin via
`RB_TEST_ADMIN_URL`, per README and `tests/disposable_postgres.py`; PostgreSQL 18
`pg_dump` must be on PATH. Use existing random test-database prefixes. Never aim
compile/migration probes at the application database or substitute SQLite.

The eight primary scopes requested are retained, with two stated scheduling
adjustments to make them independently verifiable:

1. S1 includes mechanical current-head/inventory expectation updates, including CI.
   Otherwise an entirely correct 0080 immediately fails delivered head assertions.
   Historical migration targets and frozen byte manifests remain pinned. This is
   verification maintenance, not Application implementation.
2. S2–S6 seed small acceptance tests in the files ultimately completed by S7.
   Deferring every test to S7 would make the preceding pieces unverifiable. New
   PostgreSQL behavioral suites stay in S8; S1 first compiles, then may run existing
   migration regressions. Test doubles prove orchestration, not PostgreSQL locking.

## 3. Sub-tasks

### S1 — Forward migration and PostgreSQL compile gate

Goal: translate §§2–4.6 literally into the single forward-only 0080 revision,
including all five tables, three supporting keys, indexes, receipt/task-event
extensions, seven new functions, six replacements and nine new immediate
triggers. Retain the eleven existing trigger attachments and existing two deferred
task/receipt checks; append exactly one gateway validator call after the safety
call. No Application code. First establish that every complete body compiles on
PostgreSQL 18 before starting DDL/behavior tests.

**Files:** create `migrations/versions/0080_capability_gateway.py`; change exactly
the mechanical head-maintenance files listed in Appendix H. No accepted migration
is edited. Expose migration-local tuples `NEW_FUNCTION_SQL` (seven strings) and
`REPLACEMENT_FUNCTION_SQL` (six strings), assembled from the individually named
constants required by L, so the compile command below can execute each body.

**Contract/dependencies:** §§1–4.6, 7.1a, 9.1, 10, 12.2. Depends on delivered
0077 §§DDL/GUARDS, 0078 DDL and replacements at lines 322–375/467–730, and 0079's
AgentVersion tuple key at line 45; no earlier sub-task. Consult §4.5's preservation
map while transcribing. No SQL-time import of another migration or live parsing
of the Markdown pack in `upgrade()`.

**Verification:** gate C, then this exact disposable compile probe. It is a
future command, not executed for this planning task. The `CREATE OR REPLACE`
pass checks the seven §4.4 bodies and six §4.5 bodies separately after upgrade.

```sh
uv run python - <<'PY'
import os
import runpy
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database

module = runpy.run_path("migrations/versions/0080_capability_gateway.py")
assert len(module["NEW_FUNCTION_SQL"]) == 7
assert len(module["REPLACEMENT_FUNCTION_SQL"]) == 6
with disposable_database("researchbase_pr212_test_") as url:
    os.environ["DATABASE_URL"] = url
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url, connect_args={"options": "-c check_function_bodies=on"})
    try:
        with engine.connect() as conn:
            version = int(conn.execute(text("SHOW server_version_num")).scalar_one())
            assert version // 10000 == 18
            print("SERVER_VERSION_NUM", version)
            print("DATABASE_ROLE", conn.execute(text("SELECT current_user")).scalar_one())
            assert conn.execute(text("SHOW server_encoding")).scalar_one() == "UTF8"
        command.upgrade(config, "0079_agent_identity_versions")
        command.upgrade(config, "0080_capability_gateway")
        with engine.begin() as conn:
            for sql in module["NEW_FUNCTION_SQL"] + module["REPLACEMENT_FUNCTION_SQL"]:
                conn.exec_driver_sql(sql)
                print("COMPILED", sql.split("FUNCTION", 1)[1].split("(", 1)[0].strip())
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0080_capability_gateway"
            )
        command.current(config)
        print("COMPILE_GATE 13/13")
    finally:
        engine.dispose()
PY
```

After that probe succeeds, run the exact H-static and H-PostgreSQL commands in
Appendix H. Do not treat CREATE FUNCTION success as executed-branch correctness;
S8 still must exercise guards, parity and normal-role DML. Record PostgreSQL
version/UTF-8/role, thirteen named compilation successes, revision, preserved
trigger-attachment review, and the old-branch preservation diff.

**Completion/gate:** C passes; `alembic heads` has only 0080; probe exits 0 and
prints `COMPILE_GATE 13/13`; H checks exit 0 with actual counts and no required
skips. `downgrade()` raises before any operation. No new deferred child trigger,
backfill or execution column; only the listed migration/verification files change.

**Two-round estimate/cut:** round 1 transcribes frozen SQL, wraps it and performs
the first compile; round 2 resolves mechanical compile/lint issues and verifies
head compatibility. This is large but mostly specified text. Cut only convenience
SQL generators and extra reporting; never cut a guard or alter ancestor bytes.
If compilation needs a semantic change, apply G and keep this gate open.

**Most likely failure/risk:** copied long SQL passes Python formatting but fails
E501, or compiles against the wrong replacement function. Mitigation: L before
the first compile, thirteen individually reported definitions, §4.5/4.6 callee
audit, and explicit parent/head assertions. **Stop rule:** G applies verbatim;
quote both sides, complete independent work, and record partial gaps as Deviations.

### S2 — Repository ports, composed locks and stored-row reads

Goal: add inert persistence mappings and read/lock ports, with the exact first
18-table SHARE and project → pr301 command → pr301 task → pr302 actor → pr302
version → row order. Split the safety prefix from task-row locking while preserving
the existing combined method for its callers. Supply after-wait callbacks at every
blocking acquisition. Do not introduce command admission, accounting or dispatch.

**Files:** create
`src/researchbase/agent_runtime/ports/gateway_repository.py`,
`src/researchbase/persistence/capability_gateway_repository.py`, and
`tests/unit/phase3/test_capability_gateway_repository.py`; change
`src/researchbase/agent_runtime/ports/task_safety_repository.py`,
`src/researchbase/persistence/task_safety_repository.py`,
`src/researchbase/persistence/models.py`, and
`src/researchbase/persistence/uow.py`.
Use existing research-task/Agent repositories as dependencies; no changes to their
accepted lock namespaces. Ports initially return closed-purpose stored mappings,
never Session/ORM handles; the Application DTO conversion follows S3–S5.

**Contract/dependencies:** §§2–3 (metadata only), 5–6, 8–9; S1 gate required.
Delivered sources: `research_task_repository.py:13–33/75–126/156–169`,
`task_safety_repository.py:16–24/51–89`,
`agent_version_repository.py:49–90/118–147`, and `uow.py:633–660/1311–1331`.
Read the eight safety tables in their delivered order, availability before new
tables, and new tables in §5 order. Registration omits target actor/version locks.
Resolve version→actor without row locks after project/command acquisition, then
reread under keys. Do not call the existing combined lock then append pr302 keys.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py
uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py
```

Minimum evidence: at least six recorded-session cases for first statement,
registration omission, exact advisory/row/table order, callbacks after waits,
unchanged safety combined recipe, and receipt/scoped read ordering. Verify
constructing the UoW/adapters emits no SQL. Retain SQL/callback traces with expected
versus actual sequences. No live-lock claim based on a recording session.

**Completion/gate:** C and both focused commands exit 0; all six behaviors are
asserted; existing ports/callers remain type-compatible; new mappings expose the
five tables and seven nullable receipt/event columns with correct relationships.
No dependency on not-yet-created S3 DTO modules and no new write behavior.

**Two-round estimate/cut:** round 1 factors and maps; round 2 checks recorded
sequences and regression/types. Reuse inherited task/read methods. Cut optional
query conveniences and ORM relationships; defer projections to S6. Do not cut
callback coverage or schema metadata fidelity.

**Most likely failure/risk:** an advisory lock is taken after a row lock, causing
cross-command deadlocks. Mitigation: assert the complete emitted order and keep
the safety compatibility wrapper; S8 later proves actual contention. **Stop
rule:** G applies verbatim; quote both sides, complete independent work, and
record partial gaps as Deviations.

### S3 — Closed domain/Application values, hashes and routing predicates

Goal: implement the complete §8 immutable DTO vocabulary, strict parsers, lifecycle
predicates, policy matching and pure registry/routing validation. Normalize before
hashing, retain separate artifact-owning and parameter hashes, and reproduce all
six §7.2 vectors. The bounded registry loader consumes already supplied bytes;
it does not discover plugins, import adapters or perform I/O.

**Files:** create
`src/researchbase/agent_runtime/domain/capability_invocation.py`,
`src/researchbase/agent_runtime/domain/tool_policy.py`,
`src/researchbase/agent_runtime/application/gateway_contracts.py`,
`src/researchbase/agent_runtime/application/routing.py`,
`src/researchbase/agent_runtime/ports/capability_gateway.py`,
`tests/unit/phase3/test_capability_gateway_contracts.py`,
`tests/unit/phase3/test_agent_tool_policy.py`, and
`tests/unit/phase3/test_capability_routing.py`.

**Contract/dependencies:** §§4.2, 6–8, 9; S1–S2 gates required. Delivered
`foundation/canonical_json.py:11–26`, `foundation/hashing.py:26–35`,
`agent_runtime/domain/task_safety.py` ResourceVector/settlement/streaks,
`agent_runtime/domain/harness_manifest.py`,
`agent_runtime/application/contracts.py`, `safety_contracts.py`,
`agent_contracts.py`, and the existing FakeConsumerCapability and VerifiedPrincipal.
No changes to their hash envelopes or public material. Include NULL/default fields,
authenticated actor in command material, distinct stable invoke command IDs,
UUID rules, set ordering, six-place decimals and no serializable trusted context.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_contracts.py tests/unit/phase3/test_agent_tool_policy.py tests/unit/phase3/test_capability_routing.py
uv run pytest -o addopts='' -ra tests/unit/phase3/test_research_task_contracts.py tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_agent_version_contracts.py tests/unit/phase3/test_harness_manifest.py
```

Minimum evidence: six independently fixed vector cases, literal canonical-byte
comparison and exact digests from §7.2 (not self-generated expectations); all four
command variants roundtrip; negative nested extras, bool-as-int, excess decimal
scale/nonfinite numbers, aliases/patterns, duplicate refs/permissions/entries,
and byte limits. Policy cases cover allow/deny/absence, default 50/1 and task-wide
counter inputs; routing covers phase mismatch and reference-only denial. Old
vectors must remain unchanged. SQL/Python parity is reserved for S8.

**Completion/gate:** C and both commands exit 0; six of six frozen vectors match;
all §8 fields/types/defaults are accounted for; complete key+effect duplicates
reject while ALLOW+DENY coexist and DENY wins. No dynamic import, repository
access, new ErrorCode or executable SDK appears in domain/contracts/routing.

**Two-round estimate/cut:** round 1 implements values/parsers using existing
patterns; round 2 verifies vectors and closed validation. Cut generalized schema
engines, protocol registries and optional serializers. Keep only the closed fake
tuple, bounded registry and prescribed DTOs.

**Most likely failure/risk:** normalizing too late or hashing an ArtifactVersion
owning digest as if it were parameter bytes. Mitigation: separate typed fields,
fixed Café vector and normalization tests before hash comparison. **Stop rule:**
G applies verbatim; quote both sides, complete independent work, and record
partial gaps as Deviations.

### S4 — Register/request commands and reserve_in_uow

Goal: implement policy registration and invocation request through one command
UoW each. Verify retained registry/intake/harness/parameter bytes outside locks,
then recheck exact DB pins under the S2 recipe. Add internal GatewayAccounting
`reserve_in_uow`, factoring existing budget calculations so request atomically
creates one receipt, reservation, invocation, request event, exact input refs and
task event/link. Never invoke TaskSafetyService.execute inside a gateway command.

**Files:** create
`src/researchbase/agent_runtime/application/capability_gateway.py`,
`src/researchbase/agent_runtime/application/gateway_accounting.py`,
`tests/unit/phase3/test_capability_gateway.py`, and
`tests/unit/phase3/gateway_fixtures.py`; change
`src/researchbase/agent_runtime/application/task_safety.py`,
`src/researchbase/agent_runtime/ports/gateway_repository.py`,
`src/researchbase/persistence/capability_gateway_repository.py`,
`src/researchbase/persistence/uow.py`, and
`tests/unit/phase3/test_capability_gateway_repository.py`.
The extra `gateway_accounting.py` is an internal factoring choice allowed by §6,
not a new ledger or canonical object. Add only register/request persistence writes.

**Contract/dependencies:** §§3–8, 9 error mapping; S1–S3 gates required.
Delivered sources: `task_safety.py:42–119/131–144/372–443/591–643`,
`research_task.py:66–162`, `foundation/artifact_store.py`, S1 configuration pin
verification patterns in `agent_versions.py`, and S2 ports/UoW.
Use the injected capability by identity; a new instance or DTO flag cannot grant
trust. Registration needs current HUMAN OWNER; request needs trusted context,
entitled caller/live Agent, exact policy/registry, full safety bundle/checkpoints,
caps and no stop. Reserve the fixed §6 vector, rederive gauges and preserve sticky
flags when exact equality consumes the final unit.

Build the shared command runner now: stable IDs allocated outside the three-attempt
loop; after every wait, authenticate/current read entitlement and original
committed receipt lookup precede fresh-write diagnostics. Preflight failure must
not mask entitled historical replay. Ignore the command's own current-xmin receipt
as a completed replay. Use one fresh DB provenance timestamp, final advancing-time
checks after constraint forcing, and no I/O under locks. Scope uniqueness handling
to exact gateway identities/constraint diagnostics without changing old errors.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py
uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_budget_accounting.py tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_task_safety_transports.py
```

Minimum evidence: transaction-recording tests for successful registration/request,
Human-owner denial, identity-trust denial, exact-cap request, policy switch counter
retention, request rollback on each write stage, saved replay before stale CAS,
changed-hash denial, and stable IDs across retry. Assert one task write, one receipt,
one reservation for request and none for registration; zero effects on denial.
Record the no-I/O-under-lock trace and reuse of the original safety calculations.

**Completion/gate:** C and focused tests exit 0; both new commands produce the
closed saved result; request input/policy/harness/parameter provenance is complete;
reserve_in_uow owns no locks, task revision, receipt, event or transaction. Public
safety command hashes and default denial remain intact. PostgreSQL atomicity is
still pending S8, explicitly labeled so.

**Two-round estimate/cut:** round 1 factors reservation rules and wires two
commands; round 2 tests denial/rollback/replay and corrects diagnostics. Cut public
transport wrappers, generic command dispatch frameworks and optional telemetry.
Do not duplicate the safety command transaction to save time.

**Most likely failure/risk:** nested safety execution creates a second receipt or
charge. Mitigation: transaction-counting test double, explicit seam ownership and
shared calculations with old-safety regression. **Stop rule:** G applies verbatim;
quote both sides, complete independent work, and record partial gaps as Deviations.

### S5 — Start, finish, reconciliation and durable replay

Goal: implement REQUESTED→RUNNING, pre-start cancellation, all four running
outcomes, and append-only final reconciliation of UNKNOWN_OUTCOME. Add
`settle_in_uow` using existing settlement/streak rules. Preserve immutable unknown
invocation/usage/event/receipt and return saved event-owned IDs on replay, even
after later lifecycle changes. This step does not dispatch the fake.

**Files:** change
`src/researchbase/agent_runtime/application/capability_gateway.py`,
`src/researchbase/agent_runtime/application/gateway_accounting.py`,
`src/researchbase/agent_runtime/application/task_safety.py`,
`src/researchbase/agent_runtime/ports/gateway_repository.py`,
`src/researchbase/persistence/capability_gateway_repository.py`,
`tests/unit/phase3/test_capability_gateway.py`,
`tests/unit/phase3/test_capability_gateway_repository.py`, and
`tests/unit/phase3/gateway_fixtures.py`.

**Contract/dependencies:** §§4.1–4.6, 5–6.1, 7 command material, 8–9; S1–S4 gates
required. Delivered `task_safety.py:444–505/663–674`, domain task-safety
settlement/streaks, `0078_task_safety_policies.py:201/532–577`, original receipt
helpers and S4 runner. Finish after stop/CANCELLED requires current read entitlement
and trusted observation, not availability or fresh-spend authority. Exact-cap
start may ignore only its own request's first attributable budget stop; prior or
later stops, timeouts, checkpoint changes and revocation still deny.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_task_budget_accounting.py tests/unit/phase3/test_task_checkpoints.py
```

Minimum evidence: every §4.2 allowed edge plus forbidden edge matrix; start adds
zero reservations/usage; pre-dispatch cancel retains call count and zeros variable
usage; UNKNOWN keeps full charge/occupancy without final streaks; one reconciliation
event/final usage with no invocation write. Assert output refs only on success,
no trace/summary/error on reconciliation, retry-parent finality, saved start/finish
results after reconciliation, current entitlement before conflict disclosure,
three-attempt bound for 40001/40P01, no 55P03/57014 retry, and uncertain-commit
formal receipt lookup. Test stale task and invocation CAS after saved receipt.

**Completion/gate:** C and focused command exit 0; all allowed/denied lifecycle
cases accounted for; exactly one task revision/receipt/event per command; no
second usage after final; historical results do not grow with later refs/events.
S4 tests continue passing. No automatic restart/redispatch path exists.

**Two-round estimate/cut:** round 1 adds lifecycle and settlement using the S4
runner; round 2 exercises replay/stop/failure matrices. Cut orchestration (S6) and
optional cancellation APIs. Reconciliation and after-wait replay cannot be cut.

**Most likely failure/risk:** changing the UNKNOWN row or refunding its reservation
before final reconciliation. Mitigation: record before/after row equality, separate
event-owned effective outcome, and final-usage uniqueness in S8. **Stop rule:** G
applies verbatim; quote both sides, complete independent work, and record partial
gaps as Deviations.

### S6 — Snapshot queries and CapabilityGateway.invoke

Goal: expose the three entitled read operations and implement the finite fake
gateway: request commit → start commit → one pure echo outside UoW → finish
commit. Saved command results drive subsequent revisions. Completed replay returns
the saved finish result with zero fake calls; an uncertain prior start never
grants permission to redispatch. No persistent recovery or real adapter activation.

**Files:** create
`src/researchbase/persistence/capability_gateway_queries.py`; change
`src/researchbase/agent_runtime/application/capability_gateway.py`,
`src/researchbase/agent_runtime/application/routing.py`,
`src/researchbase/agent_runtime/ports/gateway_repository.py`,
`src/researchbase/persistence/capability_gateway_repository.py`,
`tests/unit/phase3/test_capability_gateway.py`,
`tests/unit/phase3/test_capability_gateway_repository.py`,
`tests/unit/phase3/test_capability_routing.py`, and
`tests/unit/phase3/gateway_fixtures.py`.

**Contract/dependencies:** §§5, 7–8, 9.1; S1–S5 gates required. Delivered
`uow.py:647–660`, `research_task_queries.py:35` input lookup,
`research_task.py:104–162` owning-domain warning/validation pattern,
`task_safety.py:663–699` formal reads, S3 routing and S5 receipts.
Each query calls begin_formal_read before SQL and uses one read-only repeatable
snapshot for authority/policies/refs/events/charges/current projections. Sort and
keyset-page exactly as §5/§8, limit 1–256; return stored status separately from
effective reconciled outcome and current availability. No repairs or byte I/O in
the query transaction. Use the already verified retained material at invocation.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway.py tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_capability_routing.py
```

Minimum evidence: all three queries, empty/page-boundary/tie ordering and denied
scope; one snapshot without write/lock SQL; four deterministic outcomes and exact
summaries/errors; successful invoke logs exactly three committed commands and one
fake call between start commit and finish begin. Simulate response loss at all
three commits, terminal replay, unresolved start, and rejected arbitrary capability
objects. Result output/trace defaults empty; fixture artifacts remain candidates.

**Completion/gate:** C and focused command exit 0; invoke trace proves no adapter
call under transaction/locks and no replay redispatch; all DTO projections are
closed and snapshot-labeled; execution remains disabled and no execution UUID,
credential serialization, hidden subcall, network or filesystem execution is added.

**Two-round estimate/cut:** round 1 assembles projections/orchestrator; round 2
checks pagination and lost-response dispatch count. Cut optional transport surfaces,
UI formatting and adapter extensibility. Never cut explicit unknown-start handling.

**Most likely failure/risk:** replaying a committed start accidentally executes the
fake twice. Mitigation: use saved receipt metadata, dispatch only after a proven
fresh committed start, and assert call count under each lost-response scenario.
**Stop rule:** G applies verbatim; quote both sides, complete independent work,
and record partial gaps as Deviations.

### S7 — Complete unit and architecture boundary evidence

Goal: complete §9.1's unit matrix and enforce the Application/adapter/domain
boundaries over the actual implementation. Expand the acceptance seeds from
S2–S6 into closed-input, authority, policy, routing, accounting, replay and
injection regressions. Test behavior and import dependencies rather than mirroring
private method spellings or treating source-string presence as runtime evidence.

**Files:** create `tests/architecture/test_pr3_03_boundaries.py`; change
`tests/unit/phase3/test_capability_gateway_contracts.py`,
`tests/unit/phase3/test_agent_tool_policy.py`,
`tests/unit/phase3/test_capability_routing.py`,
`tests/unit/phase3/test_capability_gateway.py`,
`tests/unit/phase3/test_capability_gateway_repository.py`, and
`tests/unit/phase3/gateway_fixtures.py`.
Production defects return to the named owning step's file set and rerun that
step's gate; do not silently broaden this test-only step.

**Contract/dependencies:** §§1, 5–9.1 and Harness 09 §29; S1–S6 gates required.
Delivered `tests/architecture/test_pr3_01_boundaries.py`,
`test_pr3_04_boundaries.py`, `test_pr3_02_s1_boundaries.py`, and existing
`tests/unit/phase3/` tests provide boundary and immutable-vector conventions.

**Verification (plus C):**

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Minimum evidence: a §9.1 unit-case → test node-ID checklist; complete six-vector
and all-four-command coverage; all below/equal/above tool cap cases across policy
changes; unreviewed/reference-only/injection/self-weakening denials; absence of
domain ORM/transport/SDK imports, direct Agent persistence, hidden dispatch,
new dependencies, generic JSON refs or scientific promotion. Include trust-object
identity and no nested safety command/UoW assertions. Keep a deliberate boundary
violation fixture proving the scanner can detect a violation.

**Completion/gate:** C and both suites exit 0 with actual counts, no required
skips and no missing matrix row. Existing TaskCommand/SafetyCommand/S1 vectors
and disabled-execution tests still pass. This is unit/architecture acceptance;
it does not establish PostgreSQL lock correctness.

**Two-round estimate/cut:** seeds already exist; round 1 fills the case matrix and
architecture assertions, round 2 runs/fixes coverage omissions. Cut redundant
parameter combinations and cosmetic test restructuring. Do not cut a distinct
contract behavior, and do not update expected frozen hashes to match broken code.

**Most likely failure/risk:** tests pass because fakes omit a wait, rollback or
denied path. Mitigation: explicit event traces/failure injection and a separate S8
database matrix; never use mock results as concurrency evidence. **Stop rule:** G
applies verbatim; quote both sides, complete independent work, and record partial
gaps as Deviations.

### S8 — PostgreSQL behavior, races, replay and acceptance evidence

Goal: prove the complete fake slice on real PostgreSQL 18, including typed-row
hash parity, raw normal-role writes, clean/populated upgrades, exactly-once guards,
concurrency, response loss and lock-free reads. Produce
`docs/phase3/PR3-03-evidence.md` with the exact focused results and independent
external-loop gate status. This step closes evidence, not later-phase functionality.

**Files:** create
`tests/integration/phase3/gateway_fixtures.py`,
`tests/integration/phase3/test_pr3_03_schema.py`,
`tests/integration/phase3/test_pr3_03_guards.py`,
`tests/integration/phase3/test_pr3_03_migration.py`,
`tests/integration/phase3/test_pr3_03_application.py`,
`tests/integration/phase3/test_pr3_03_concurrency.py`,
`tests/integration/phase3/test_pr3_03_replay.py`, and
`docs/phase3/PR3-03-evidence.md`; change
`tests/integration/phase3/conftest.py` only to expose gateway fixtures, and
`README.md` for bounded fake-slice scope and focused commands.
Reuse S1's CI head update. Do not alter the shared S1 `agents` fixture's 0079
target or its no-invocation expectations; create a gateway-specific 0080 fixture.

**Contract/dependencies:** all §§1–12, particularly §9.1; S1–S7 gates required.
Delivered `tests/disposable_postgres.py`, phase3 `conftest.py` and
`agent_fixtures.py`, PR3-01/04/S1 migration, concurrency and replay tests,
`tests/integration/phase3/test_pr3_00_bootstrap.py` catalog/row snapshots,
`scripts/ci_pytest_files.py`, and `.github/workflows/ci.yml`.
Seed identity through accepted S1 commands; retain registry/intake/configuration/
parameters through owning Artifact commands before gateway locks. All file
artifacts use tmp_path; ordinary runtime role has DML only. No trigger disabling,
privileged canonical fixture insertion, or ORM create_all substitute for migrations.

Required evidence is partitioned by file to keep failures attributable:

| Suite | Minimum contract evidence |
| --- | --- |
| schema | Every §2/§3 column, CHECK, index and FK; all eleven composite target keys; six input families with XOR/duplicates/scope/freeze/hash errors; 256/257 permissions and total refs; parameter 65536/+1 storage bounds distinguished from the stricter closed argument schema; summary 8192/+1 UTF-8 bytes; no cascade/JSON semantic storage. Both policy vectors reconstructed from typed rows using §7.1a yield exact §7.2 canonical text/digests and both capability-set hashes. Also reorder/non-ASCII, fixed resource strings and fractional SQL-number rejection. |
| guards | Positive normal-role protocol plus every immediate guard's denial; immutable no-op/update/delete, committed-receipt append, naked revision, missing/extra effect, multiple flush and wrong usage/reservation/nullable step. At maximum sets, measure exactly one existing task-final and one receipt-completeness firing, one gateway helper call, no child-deferred scan. Retained trigger OIDs/attachments and all invalid lifecycle/reconciliation edges. |
| migration | Empty base→0080 and populated 0079→0080; compare old scientific rows/hashes/traces and original planning/safety/S1 receipt results; only nullable additions on old rows, no UPDATE/backfill/dummy execution. Empty/populated downgrade refuses before catalog/data/revision change; explicit CHECK replacements, sole head and original command cases preserved. |
| application | Human/eligible Agent same Application boundary, owner-only registration, untrusted consumer denial; every command's rollback across write stages, exact effect counts and no scientific writes. Gates/caps/version/manifest agreement, pre-start cancel, all outcomes, unknown/final reconciliation and post-stop bookkeeping. |
| concurrency | Observe first SHARE and ordered advisory/row waits; two tasks sharing AgentVersion versus availability writer; last budget unit/call/parallel slot races. Actual DB-observed waits across expiry/revocation/stop/checkpoint changes, exact-cap own-stop start versus prior/later/additional stops, post-start finite finish only. Three fresh attempts only for 40001/40P01; timeouts do not retry. |
| replay | Same original key/hash saved IDs versus changed material; recheck entitlement/replay after each blocking stage before task/invocation CAS/state/expiry/availability. Lost request/start/finish responses and uncertain commits; no duplicate fake, reservation, usage or event; no unknown refund/redispatch. Query snapshots remain coherent under concurrent writers and issue no locks/writes/second session. |

**Verification:** C, then exactly these focused runs with the explicit disposable
admin selector already set. Capture JUnit plus console counts; `-s` on the races
retains observed lock/timestamp evidence. Do not execute the whole suite.

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
uv run pytest -o addopts='' -ra --junitxml=tmp/pr3-03/schema.xml tests/integration/phase3/test_pr3_03_schema.py tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_03_migration.py
uv run pytest -o addopts='' -ra -s --junitxml=tmp/pr3-03/behavior.xml tests/integration/phase3/test_pr3_03_application.py tests/integration/phase3/test_pr3_03_concurrency.py tests/integration/phase3/test_pr3_03_replay.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_04_*.py tests/integration/phase3/test_pr3_02_s1_*.py
```

`mkdir -p tmp/pr3-03` precedes these runs. Reuse H's already captured passing
head-only regressions unless a subsequent change affects them. If a production
defect requires an earlier step's edit, rerun that step's gate and affected S8
cases; do not waive a failing test or change frozen expectations.

Minimum final evidence: baseline/revision, exact commands and counts including
failures/skips, PostgreSQL version/role/encoding, clean/populated manifests, six
vector IDs and parity results, guard firing counts, transaction/fake call counts,
actual waiter/backend evidence and DB timestamps. Expiry races record
tx_started_at < expiry_at, wait_started_at < expiry_at, acquired_at >= expiry_at
and checked_at >= acquired_at and > expiry_at; a second wait needs its own fresh
check. Sleeps alone are not evidence. List all Deviations and P0–P3 dispositions.

**Completion/gate:** C and every focused suite exit 0, all §9.1 cases mapped to
passing node IDs, no required skip. Then attach the external check loop's six
shard commands/counts/JUnit and verify exhaustive file union without overlap.
The implementation agent does not launch those shards. If external output or
independent review is unavailable, write `PENDING`, hand off and do not declare
overall PR3-03 acceptance. Final acceptance requires six shards passing and no
open P0/P1. Stop at accepted PR3-03; no subsequent execution/provider work.

**Two-round estimate/cut:** this is the tightest step. Round 1 reuses existing
fixture/manifest/wait-observation machinery and implements six parameterized
suite files; round 2 runs focused suites, fixes test/evidence defects and writes
evidence. The estimate assumes earlier acceptance seeds have exposed logic defects
and disposable PostgreSQL is ready. Cut custom fixture frameworks, duplicated
setups, pretty report generation and repetitions beyond distinct contract cases.
If required cases still do not fit, hand off the exact remaining node-ID checklist
under the still-open S8 gate; do not omit them or turn a two-round estimate into
an acceptance waiver. External review/CI latency is outside the estimate.

**Most likely failure/risk:** misleading race evidence from sleeps or shared
fixtures, plus S1 fixtures accidentally running at the wrong revision. Mitigation:
gateway-owned isolated databases, explicit 0079→0080 setup, observed backend lock
waits, bounded joins/timeouts and persisted effect counts. **Stop rule:** G applies
verbatim; quote both sides, complete independent work, and record partial gaps as
Deviations.

## 4. Exact order and progression gates

Run sequentially: **S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → external six-shard
check and independent review → STOP**. No downstream step starts on an unpassed
predecessor gate. Earlier passing code may be reviewed separately; that does not
claim the complete gateway is accepted. No branch/commit/push action is authorized
by this plan.

| Before starting | Required predecessor evidence |
| --- | --- |
| S1 | Owner-authorized pack at inspected HEAD; sole delivered parent 0079; explicit disposable PG18 selector; implementation environment installed from uv.lock. |
| S2 | S1 C, thirteen compile successes, current head 0080, H regressions passing; no Application code in S1. |
| S3 | S2 C and six minimum lock/read cases plus compatibility checks; no key acquired after row locks. |
| S4 | S3 C, six fixed vectors and strict DTO/policy/routing tests, old vectors unchanged. |
| S5 | S4 C and atomic register/request/reserve, trusted-context and replay acceptance traces. |
| S6 | S5 C and full lifecycle/reconciliation/receipt tests, no unknown mutation/refund. |
| S7 | S6 C and all queries/invoke traces, exactly one fresh dispatch and zero replay dispatches. |
| S8 | S7 C and complete unit/architecture matrix with actual passing counts. |
| Overall acceptance | S8 focused results/evidence, external six-shard success, independent review with no open P0/P1. |

## Appendix H — Mechanical head maintenance owned by S1

These are exact paths, not permission for a repository-wide replacement. Change
only current-head assertions/inventories to include 0080 and its exact parent;
retain historical revision tests, SHA-256 pins and scientific expectations.

```text
.github/workflows/ci.yml
tests/fixtures/phase2_static_baseline.json
tests/architecture/test_import_boundaries.py
tests/architecture/test_b02_strategy_promotion_boundaries.py
tests/architecture/test_b04_boundaries.py
tests/architecture/test_b05_review_boundaries.py
tests/architecture/test_b20_screening_boundaries.py
tests/architecture/test_basic_approval.py
tests/architecture/test_pr3_02_s1_boundaries.py
tests/unit/test_batch_c_migration_history.py
tests/unit/test_task12_migration_history.py
tests/unit/phase2/test_pr2_04_r8a_host_topology.py
tests/unit/phase2/test_pr2_20_inventory.py
tests/integration/phase2/test_pr2_03_review_guards.py
tests/integration/phase2/test_pr2_04_execution_migration.py
tests/integration/phase2/test_pr2_04_migration_coverage.py
tests/integration/phase2/test_pr2_15_decision_schema.py
tests/integration/phase2/test_revision_action.py
tests/integration/phase2/test_pr2_17_authorship_schema.py
tests/integration/phase3/test_pr3_00_bootstrap.py
tests/integration/phase3/test_pr3_01_migration.py
tests/integration/phase3/test_pr3_04_migration.py
tests/integration/phase3/test_pr3_02_s1_migration.py
```

Specific traps: `.github/workflows/ci.yml:66` expects 0079 current head;
`test_import_boundaries.py:197` has an exact migration-file inventory;
`test_pr3_04_migration.py:96` and `test_pr3_01_migration.py:38` check repository
head while exercising older revisions. In `test_pr3_02_s1_migration.py:55`, change
the S1-only `upgrade(..., "head")` target to explicit `0079_agent_identity_versions`
while its repository-head assertion advances to 0080; retain its four-table delta,
0079 revision and downgrade evidence. Keep `agent_fixtures.py:102` at 0079 and
the S1-only absence assertion at `test_pr3_02_s1_migration.py:29` intact. Likewise
leave explicit 0079 historical setup in `test_pr2_20_migrations.py:187` unchanged.
The static baseline's migration_head is an active expectation; its baseline_commit
and Pyright data are not being rewritten.

H-static commands (after the compile gate):

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

H-PostgreSQL commands (after the compile gate; selected files only):

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py
```

Tests using `phase2_database_url` require `DATABASE_URL` to name a separate
disposable runtime database, as documented by their existing fixture; the admin
selector must still name `postgres`. Supply both using the existing test plumbing.
No application or production database is admissible. Report actual counts and
setup failures rather than predicting them. These focused historical suites check
only touched head assertions and their surrounding contracts; the external loop
continues to own the full suite.

## 5. Verification of this documentation-only task

Only this file is created in this turn. No code, tests, migration or database
execution is authorized here. The director commits this file after review; the
planning agent does not commit, push or create branches.

Required commands, with a writable repository-local ignored cache:

```sh
git diff --check HEAD
UV_CACHE_DIR="$PWD/tmp/pr3-03-plan-uv-cache" uv run ruff check .
```

Observed results on 2026-10-22:

| Exact command | Exit | stdout | stderr |
| --- | --- | --- | --- |
| `git diff --check HEAD` | 0 | Empty | Empty |
| `UV_CACHE_DIR="$PWD/tmp/pr3-03-plan-uv-cache" uv run ruff check .` | 0 | `All checks passed!` | Empty |

The new file was staged (`A`) and no other path changed. `git diff --check HEAD`
does not inspect staged-new content on its own; the director re-runs the check on the
committed file.
No commit, push or branch creation was performed. Unit, architecture, PostgreSQL,
migration, concurrency, replay and full-suite tests: **NOT RUN (planning only;
no test counts)**. All future gates above remain NOT RUN; no implementation PASS
is claimed.
