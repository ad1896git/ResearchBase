# PR3-05 read-only slice plan

Status: planning only; implementation requires the named owner approval below.
Reviewed base: `codex/phase3-wave3-base`, HEAD `1c44def`. The working tree was
clean before this file. The PR3-05 draft is unchanged from `c76c11a`.

## 1. Verdict and evidence

**Yes: the named read-only slice is implementable on this base without resolving
D1 or D2.** This is a source-based feasibility verdict, not implementation or
test acceptance. D1 (durable save/replay) and D2 (artifact-write lock upgrades)
remain blockers for saving. Neither operation is needed by the three proposed
read services. No new schema, write-lock protocol, execution persistence or
provider is needed to implement those reads.

The owner's decisions in this task approve the direction in draft §§9 D3–D5;
they supersede its historical “awaiting owner approval” label, but do not grant
implementation permission. Full PR3-05 acceptance still requires accepted
PR3-02-S2 and PR3-04 plus resolved D1/D2. Delivered PR3-04 code is available for
read composition; its presence alone is not a new acceptance claim.

Read authority, in order: [AGENTS.md](../../AGENTS.md); architecture
[01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md),
[02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md),
[03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md),
[08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md);
[Phase 3](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md)
§§17, 26–28, 51–52, 85.5; [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md);
the full [approved-direction draft](../proposals/PR3-05_Context_Memory_Contract_DRAFT.md);
[PR3-01 freeze](PR3-01-contract-freeze.md),
[PR3-04 freeze](PR3-04-contract-freeze.md), and
[PR3-02-S1 freeze](PR3-02-S1-contract-freeze.md). Migration and source references
below are inspected files at `1c44def`, not database inspection results.

### Delivered foundations

All line references below are repository-relative and refer to that base.

| Requirement, quoted from the draft or pack | Delivered source, quoted alongside | Disposition |
| --- | --- | --- |
| Draft lines 152–155: “one REPEATABLE READ READ ONLY snapshot”, “autoflush disabled” | `src/researchbase/persistence/uow.py:650–660`: `def begin_formal_read(self)`, `session.autoflush = False`, `"isolation_level": "REPEATABLE READ"`, `"postgresql_readonly": True` | Reuse before any Application SQL. The snapshot mechanism exists. |
| Draft lines 64–67: “Use `research_task_inputs` and `research_task_step_inputs` as canonical input bindings.” | `migrations/versions/0077_research_task_graph.py:92–107,134–153`: `CREATE TABLE research_task_inputs`, `CREATE TABLE research_task_step_inputs`, six concrete version FKs and `num_nonnulls(...) = 1`; `research_task_repository.py:99–103`: `def inputs(self, task, *, step=False)` | Both owners and all six families are delivered. |
| PR3-01 freeze lines 466–475: “Require status IN ('FROZEN','SUPERSEDED'), frozen_at IS NOT NULL and content_hash IS NOT NULL” | `src/researchbase/agent_runtime/application/research_task.py:111–120`: `row["status"] not in {"FROZEN", "SUPERSEDED"}`, `row["frozen_at"] is None`, `row["content_hash"] is None`; lines 156–159 compare saved hash/scheme | Historical versions already resolve without latest/current. No lifecycle change is needed. |
| Draft lines 59–63: “A global artifact with NULL project is not automatically readable.” | `src/researchbase/persistence/research_task_queries.py:37–49`: source links use `l.project_id=:project`; other families use `"o.project_id=:project"`. `manuscript_freeze_repository.py:132–143` also selects artifacts with `a.project_id=:project` | Preserve exact project checks. Do not add a global-artifact exception or claim one is already present. |
| Draft line 92: “exact safety policy IDs and snapshot gate projections” | `migrations/versions/0078_task_safety_policies.py:128–135`: three nullable policy FKs; `src/researchbase/agent_runtime/application/task_safety.py:701,715–738`: `def safety_projection(repo, task, at, *, history)` and `effective_status="EXPIRED" if ... else r["status"]` | Policies, accounting and checkpoint projections exist; read expiry never writes. |
| Draft lines 54–58: “Authenticate a trusted `VerifiedPrincipal`” and delivered read roles | `src/researchbase/agent_runtime/application/research_task.py:66–93`: principal type check, `_READERS`, live credentials, binding, membership and effective role checks; `migrations/versions/0079_agent_identity_versions.py:15,52,62,123`: `agent_versions`, `agent_availability`, `agent_command_receipts`, `agent_availability_events` | Reuse trusted Human/Agent read admission. S1 enrollment/version delivery is not execution admission. |
| Draft lines 122–125: “Use project-scoped `Artifact` and frozen `ArtifactVersion`”; “A locator is not identity or permission.” | `src/researchbase/domain/artifact.py:22–31,57–70,99–103`: immutable value classes, project/version/hash/frozen fields; `src/researchbase/foundation/artifact_store.py:83–95`: `open` reads exact bytes and `verify` compares SHA-256 | Read an explicitly supplied version after authorization; no save command is necessary to consume an existing artifact. |

### Bounded implementation work and excluded blockers

These comparisons identify concrete work or an already acknowledged blocker.
They do not allege that a delivered service violates its own narrower contract.

| Contract text, quoted | Delivered source line, quoted | Consequence for this slice |
| --- | --- | --- |
| Draft lines 9,155: “Build each response from one database snapshot”; “Entitlement, inputs, source/project links, validity and policy projections use that snapshot.” | `research_task.py:456–459`: `with self._factory() as uow:` followed by `uow.begin_formal_read()`; `task_safety.py:692–698` independently does the same. Paths are under `src/researchbase/agent_runtime/application/`. | R2 must compose reads inside one UoW, not call both transaction-opening public wrappers. Existing same-UoW helpers and ports support this; no isolation change is needed. |
| Draft line 93: “verified bytes/content identity”; lines 159–160: “A required canonical artifact failure fails the query” | `src/researchbase/agent_runtime/application/research_task.py:127`: `with saved_seal():`; `src/researchbase/application/manuscript_freeze.py:196–203`: saved-seal mode checks retained byte size, while `self._store.verify(content)` and `self._store.open(content)` are on the other branch | R2/R3 must explicitly verify required local bytes. Existing retained-seal verification alone is not evidence that bytes exist now. The delivered ArtifactStore supplies the needed operations. |
| Draft lines 129–135: “They do not supply a principal-scoped atomic task-memory receipt”; “closed command set and no memory result FK” | `migrations/versions/0078_task_safety_policies.py:264–266`: `pr304_command_names` permits six planning and six safety commands only; `0077_research_task_graph.py:179–199` stores task/revision receipt fields. `src/researchbase/application/commands.py:2394,2435,2552` each opens `with self._uow_factory() as uow:` for artifact create/version/freeze | **D1 remains blocked and OUT.** Do not nest commands, scan manifests for replay, or extend receipts. This is not a read prerequisite. |
| Draft lines 198–204: “A save that subsequently writes them would upgrade those locks”; “There is no approved write-lock recipe” | `src/researchbase/persistence/research_task_repository.py:16–17`: `"artifact_versions", "artifacts"`; line 33: `SHARE_SQL = "LOCK TABLE " + ", ".join(SHARE_TABLES) + " IN SHARE MODE"`; line 67 executes it | **D2 remains blocked and OUT.** Read services never call `lock_write`; no narrowing, upgrade or new serialization scheme is proposed. |

The file ancestry is `0077_research_task_graph` → `0078_task_safety_policies` →
`0079_agent_identity_versions` (their `revision`/`down_revision` assignments).
No Alembic or database command was used to establish this. No additional
read-blocking architecture gap has been established by this inspection. If one
is discovered, use the evidence-and-stop rule in §4; do not infer a gap from an
older pack's historical description of absent code.

## 2. Scope and read contract

**IN:** typed Application queries `get_canonical_context_for_task` /
`CanonicalContextLoader.load_for_task`, `get_task_working_memory`, and
`validate_promotion_context`; immutable, recursively closed read DTOs
`CanonicalContext`, `TaskMemoryRead`, `PromotionContextValidation`; narrowly
scoped read ports/adapters and their tests. Names are proposed PR3-05 work,
not delivered APIs or database columns. No HTTP/CLI route is frozen here;
Human and Agent callers use the same trusted Application boundary.

The six task/memory source families are exactly `RESEARCH_QUESTION_VERSION`,
`HYPOTHESIS_VERSION`, `CLAIM_VERSION`, `SOURCE_VERSION`, `ARTIFACT_VERSION`,
`MANUSCRIPT_VERSION`. Read exact FROZEN or historically frozen SUPERSEDED
versions with non-null frozen time/hash under their owning contracts. Four
Phase 1 families retain null binding `hash_scheme`; source/manuscript retain
their owning `sha256-cjson-v1`. No DRAFT scientific context or latest fallback.
Traversal of existing typed evidence/Run/placement/policy relations does not
admit those objects as additional task input or memory-source families.

Each public query owns one UoW and invokes existing `begin_formal_read` before
SQL. Capture one `transaction_timestamp()` for snapshot-time projections, using
the delivered safety query helper. Reuse trusted credentials and read roles;
authorize project before protected existence/hash/count/locator diagnostics,
then check task and optional step membership and each dependency before its
expansion or serialization. No second session, nested transaction, autoflush,
commit, explicit table/advisory/row lock, or repair write. “Lock-free” uses the
packs' meaning: no explicit exclusion locks beyond normal MVCC SELECT behavior.

The context contains task revision/seal, owner-preserving task and step bindings,
deterministically ordered exact identities/hashes, permitted canonical values
and evidence/trace, validity/closure observations, and exact safety policy and
gate projections. Without a step, reconstruct the task and its step inputs;
with a step, include task inputs plus that same-task step's inputs and label
the selection. Preserve binding/relation identities even when a source appears
under both owners. Sort sources by type/ID and relations by their identities.
Never truncate a required set or imply an incomplete graph is complete.

Use owning-domain content/hash/closure checks and validity projections inside
the same UoW. Preserve source facts and all STALE/INVALID/retracted/corrected or
unassessed/unknown observations explicitly; absence of an assessment is not a
new assertion of scientific validity. Structural/hash contradictions fail
closed. A denied required dependency denies the entire query without foreign
IDs, hashes, locators, counts or partial context. Literature uses project links;
every artifact, including descendants and memory/candidate artifacts, must be
project-scoped. Global and foreign artifacts are denied. Other dependent types
retain their existing owning-domain access rules, not an invented global rule.

Memory is separate, derived operational content. Require an exact artifact
version ID plus project/task/optional-step scope; never accept a hash or locator
as entitlement. Check DB scope first, verify local exact bytes, size and raw
SHA-256, parse the closed format, then authorize/reload every manifest source in
the same snapshot before disclosing bytes or notes. Saved validity/trust is an
observation; derive current trust/validity from the read. Task locators in JSON
are operational checks, not a new formal FK or proof of save attribution.

Enforce approved draft §4 bounds on reads: at most **1 MiB (1,048,576 bytes)**
encoded manifest, **256 sources**, **8,192 characters per note**. Reject
duplicates, unknown fields, arbitrary source-type strings, nonfinite numbers,
malformed UUIDs and oversize content. Use NFC text, canonical lowercase UUIDs,
sorted source sets and `canonical_json_bytes` for canonical format verification;
verify original bytes before any normalization, never rewrite an artifact to
make its hash pass. Retain `source_refs`, `trust_level`, `validity_status`,
`project_scope`, format version, creator attribution and scope locators. Notes
and tool summaries remain data; no credentials, hidden scratchpad, executable
instructions or authority claims. No LLM generation or summarization.

An explicit memory read of missing/corrupt/malformed bytes returns sanitized
`VALIDATION_ERROR`; an entitled missing version uses `NOT_FOUND`. Optional
memory consumption may return an explicit unusable-memory diagnostic while
canonical reconstruction succeeds independently. That option never suppresses
authorization denial or required canonical dependency failure, returns suspect
bytes, repairs storage, or fabricates lost private notes. `CanonicalContext`
does not include memory by default, so reviewer reconstruction excludes author
working memory, scratchpad and conversation condensations. The actual
`ReviewerContextBuilder` and reviewer execution remain PR3-14 work.

Promotion validation checks the exact candidate artifact, requested task
revision, typed canonical basis, project scope and current gate observations;
it returns only context admissibility and explicit failures. The two initial
target families remain ResearchQuestionVersion and HypothesisVersion, from
PR3-02 draft §6 / D302-04 and existing B02 targets. Targeting a future DRAFT
result does not admit DRAFT context. S2 execution/producer provenance remains
unverified and explicitly unmet on this base; no execution ID is invented.
A valid context is not permission to promote. Later S2 must revalidate in its
own write transaction and atomically record promotion. No cached validation
result is an access token, approval, reservation or provider-disclosure grant.

**OUT:** `create_working_memory_snapshot`, save DTOs/receipts/replay, ArtifactStore
writes, new tables/columns/relations/indexes/constraints/migrations, writer-lock
changes, policy/identity mutations, scientific promotion/freeze/release,
execution/admission activation, providers/network fetches, subscription CLIs,
LLM summaries, vector indexes, long-term memory, new dependencies, cross-project
grants and broader promotion families. Preserve existing error enums and
HTTP/CLI mappings. Validation and safety projections never enable execution,
promotion or providers, regardless of a successful query.

## 3. Subtasks after implementation authorization

Four sequential subtasks are proposed. Every file below is a **future** target;
this planning task creates only this plan. New modules must wrap SQL at the
configured 100-character limit. Add no `noqa`, per-file ignore or lint exclusion;
do not copy historical suppression headers into new files.

Before **any** future `uv` command, from the repository root:

```sh
mkdir -p tmp/pr3-05-readonly-uv-cache
export UV_CACHE_DIR="$PWD/tmp/pr3-05-readonly-uv-cache"
```

These verification commands are obligations, **NOT RUN** in this planning task.
Static success in R1–R3 does not establish behavioral acceptance; R4 owns the
focused test evidence. Do not run the whole suite; the director's check loop
owns that evidence.

### R1 — Closed read contracts and dependency boundaries

Goal: define immutable requests/results, the closed memory-manifest format and
a read-only port/UoW protocol sufficient for all three queries. Keep trusted
principal separate from caller fields; no save command or unrestricted JSON
payload. Specify missing/unusable memory and warning semantics in the contract.

Create:

- `src/researchbase/agent_runtime/application/context_contracts.py`
- `src/researchbase/agent_runtime/domain/task_memory.py`
- `src/researchbase/agent_runtime/ports/context_repository.py`
- `docs/phase3/PR3-05-readonly-slice-contract.md`

Depends on: owner approval at G1. Reuse `InputType`, `TaskInput`, existing
safety DTOs and ErrorCode without changing their semantics.

Exact verification:

```sh
git diff --check HEAD
uv run ruff check src/researchbase/agent_runtime/application/context_contracts.py src/researchbase/agent_runtime/domain/task_memory.py src/researchbase/agent_runtime/ports/context_repository.py
uv run pyright src/researchbase/agent_runtime/application/context_contracts.py src/researchbase/agent_runtime/domain/task_memory.py src/researchbase/agent_runtime/ports/context_repository.py
```

Observable completion: the documented field inventory matches the closed types;
all six source variants and §2 bounds are expressible; memory and candidate
content are distinct from canonical facts; no method grants execution or writes.
R4 must demonstrate recursive rejection and immutable results.

Stop rule: apply §4 to any claimed missing type/field or conflicting contract;
do not add schema, ErrorCode or a seventh input family to make a DTO convenient.
Most likely failure: an open nested dictionary accepts extra authority fields.
Mitigation: closed nested variants and boundary-value/adversarial tests in R4.

### R2 — Canonical context in one scoped snapshot

Goal: implement the context query with scoped dependency expansion, exact
retained versions, required artifact verification and safety/validity projections.
Use one snapshot-time value for the whole response.

Create:

- `src/researchbase/agent_runtime/application/canonical_context.py`
- `src/researchbase/persistence/context_repository.py`
- `src/researchbase/persistence/context_queries.py`

Change:

- `src/researchbase/persistence/uow.py`: wire the read adapter to its existing
  session; leave `begin_formal_read` isolation and writer protocols unchanged.
- `src/researchbase/agent_runtime/application/research_task.py`: expose narrowly
  additive same-UoW authorization/input-resolution helpers for composition,
  retaining existing public query and mutation behavior.

Depends on: R1. Reuse `safety_projection` / `verify_saved_policies` with the
existing `uow.task_safety`, plus existing owning-domain same-UoW verification.
Do not call public transaction-opening task, safety or provenance wrappers from
the new query. New read adapters must scope every node before delegating a
traversal; internal raw rows/ORM objects never become public results. Do not
carry the write path's `saved_seal` shortcut into required-byte verification.

Exact verification:

```sh
git diff --check HEAD
uv run ruff check src/researchbase/agent_runtime/application/canonical_context.py src/researchbase/agent_runtime/application/research_task.py src/researchbase/persistence/context_repository.py src/researchbase/persistence/context_queries.py src/researchbase/persistence/uow.py
uv run pyright src/researchbase/agent_runtime/application/canonical_context.py src/researchbase/agent_runtime/application/research_task.py src/researchbase/persistence/context_repository.py src/researchbase/persistence/context_queries.py src/researchbase/persistence/uow.py
```

Observable completion: one public call returns the complete requested scope,
exact source material and warnings, policy IDs and non-authorizing gate state;
it has no writes, explicit locks or secondary UoW. Global/foreign dependencies
fail closed before disclosure. R4 supplies real snapshot/concurrency proof.

Stop rule: apply §4 if any required owning projection cannot be composed without
a second transaction, lock, mutation or unscoped disclosure. Do not broaden a
legacy verifier silently. Most likely failure: a helper opens another UoW and
mixes authorization, task revision and safety state from different snapshots.
Mitigation: an explicit in-UoW composition surface and R4 connection/SQL tracing
with a concurrent committed writer between reads.

### R3 — Exact memory reads and non-authorizing promotion validation

Goal: implement both remaining read services over R2's same-UoW composition.
Apply exact artifact/scope/manifest checks before returning content, reload
sources, and keep canonical facts authoritative. Implement only validation of
the two admitted target families, never promotion or a save fallback.

Create:

- `src/researchbase/agent_runtime/application/task_memory.py`
- `src/researchbase/agent_runtime/application/promotion_context.py`

Depends on: R1 and R2. Existing artifact domain/store are consumed unchanged.
Use DB byte size as an early bound and check actual bytes/hash/encoded size;
verify the bytes actually returned, not just a separate earlier store read.
Use existing project-scoped frozen artifacts as input, including test fixtures
created by existing artifact commands; do not require the blocked save command.
Required canonical artifact corruption fails; optional memory loss remains an
explicit diagnostic. No promotion success or producer attribution is inferred
from S1 identity, creator fields, caller assertions or a candidate hash.

Exact verification:

```sh
git diff --check HEAD
uv run ruff check src/researchbase/agent_runtime/application/task_memory.py src/researchbase/agent_runtime/application/promotion_context.py
uv run pyright src/researchbase/agent_runtime/application/task_memory.py src/researchbase/agent_runtime/application/promotion_context.py
```

Observable completion: an authorized exact-version read returns verified bounded
memory separately from current canonical context; unreadable sources disclose
nothing; invalid memory cannot alter facts, budget, gates or validity. Reviewer
context excludes memory by construction. Validation returns a checked basis and
explicit limitations without a persisted result, enabled action or reusable grant.

Stop rule: apply §4 before any proposed receipt, save composition, artifact write,
lock upgrade, execution placeholder or additional promotion target. D1/D2 remain
OUT even if implementing a save appears convenient. Most likely failure: a known
content hash reaches ArtifactStore before artifact/project/source authorization.
Mitigation: exact-version lookup and scoped checks first; denied-request store
spies and foreign-source manifests in R4 prove no bytes or metadata escape.

### R4 — Unit, architecture and PostgreSQL read evidence

Goal: write and run focused tests for R1–R3, and record actual commands, counts,
failures/skips and SQL/snapshot evidence. Database tests use disposable real
PostgreSQL 18 and normal application privileges, never SQLite. Setup may use
accepted existing commands/migrations in the disposable fixture; the query
under test remains read-only. No new migration is part of this slice.

Create:

- `tests/unit/phase3/test_context_contracts.py`
- `tests/unit/phase3/test_canonical_context.py`
- `tests/unit/phase3/test_task_memory.py`
- `tests/unit/phase3/test_promotion_context.py`
- `tests/architecture/test_pr3_05_readonly_boundaries.py`
- `tests/integration/phase3/test_pr3_05_context_reads.py`
- `tests/integration/phase3/test_pr3_05_memory_reads.py`
- `tests/integration/phase3/test_pr3_05_promotion_validation.py`
- `docs/phase3/PR3-05-readonly-slice-evidence.md`

Depends on: R1–R3. Reuse delivered `planning` and `agents` fixtures without
changing shared fixture behavior. Put new local fixture helpers in the new test
modules. Use the existing `RB_TEST_ADMIN_URL` disposable-cluster selector and
guard in `tests/disposable_postgres.py`; never guess credentials, start a database
implicitly, or point these tests at an application database.

Required observable coverage:

1. Closed DTO/manifest variants, no extra nested fields, duplicate sources/JSON
   keys, unknown families, nonfinite values, NFC/canonical UUIDs, ordering, exact
   byte/hash checks and at/over each of the three bounds. Equal scientific
   identities preserve owning hashes; different binding owners stay observable.
2. All six task and step input families; FROZEN and historically frozen versions;
   current-pointer changes never redirect reads; DRAFT/live refs reject. Values
   survive STALE/INVALID/correction with warnings. Missing or unknown projections
   never become invented VALID facts. Required graph/hash/byte failure fails
   the whole response. Source/tool instructions remain inert data.
3. **One lock-free REPEATABLE READ READ ONLY snapshot:** instrument the actual
   reader's connection/session and SQL, assert isolation/read-only/autoflush,
   one UoW and one snapshot-time sample across entitlement, inputs, expanded
   sources, validity and policies. With barriers, commit a legitimate writer
   between reader stages; the response remains wholly on its original snapshot
   and a new query observes the committed change. Observe no explicit LOCK,
   advisory call, row-lock SELECT, DML, flush, commit or second reader session.
   Also prove the reader completes while a writer holds the delivered exclusion
   locks. The separate writer/observer test connection is not a second query UoW.
4. **Denied cross-project hash guesses; global and foreign artifacts denied:**
   test direct input, descendant artifact, candidate and memory paths. Exercise
   same hash in different projects and a valid own-project memory artifact whose
   manifest names a foreign source. Check sanitized errors/diagnostics, no
   foreign IDs/hashes/locators/counts/partial graph, and no denied byte read.
   Source project-link rules, same-project wrong-task/step memory, revoked
   binding/membership/credentials, all read roles, enrolled Agents and denied
   unbound Agents are covered. Entitled archived history remains readable.
5. Missing/corrupt/oversize optional memory gives an explicit diagnostic and
   independent canonical reconstruction; explicit memory reads reject it.
   Required artifact loss fails. Fresh service construction can rebuild canonical
   context without cached memory; lost notes are never synthesized. Stored versus
   effective checkpoint expiry stays distinct and no read writes expiry.
6. Promotion validation rejects wrong revision/scope/hash/target and reports
   missing S2 provenance. Both admitted target families are exercised without
   actual promotion. Memory cannot overwrite facts or clear stops. Valid query
   results still enable no execution/promotion/provider call; mutation, provider,
   ArtifactStore-write and commit spies are never invoked.
7. Import/boundary tests cover common Human/Agent Application entry, immutable
   DTOs, no ORM/vendor/transport imports in runtime/domain, no direct Agent SQL,
   no new schema/dependency, and canonical reviewer reconstruction with no author
   working-memory path. These tests do not claim PR3-14 or live-provider acceptance.

Exact verification, after the shared UV_CACHE_DIR setup and explicit disposable
PostgreSQL configuration:

```sh
git diff --check HEAD
uv run ruff check .
uv run ruff format --check src/researchbase/agent_runtime/application/context_contracts.py src/researchbase/agent_runtime/domain/task_memory.py src/researchbase/agent_runtime/ports/context_repository.py src/researchbase/agent_runtime/application/canonical_context.py src/researchbase/agent_runtime/application/research_task.py src/researchbase/persistence/context_repository.py src/researchbase/persistence/context_queries.py src/researchbase/persistence/uow.py src/researchbase/agent_runtime/application/task_memory.py src/researchbase/agent_runtime/application/promotion_context.py tests/unit/phase3/test_context_contracts.py tests/unit/phase3/test_canonical_context.py tests/unit/phase3/test_task_memory.py tests/unit/phase3/test_promotion_context.py tests/architecture/test_pr3_05_readonly_boundaries.py tests/integration/phase3/test_pr3_05_context_reads.py tests/integration/phase3/test_pr3_05_memory_reads.py tests/integration/phase3/test_pr3_05_promotion_validation.py
uv run pyright
uv run pytest -o addopts='' -ra tests/unit/phase3/test_context_contracts.py tests/unit/phase3/test_canonical_context.py tests/unit/phase3/test_task_memory.py tests/unit/phase3/test_promotion_context.py tests/unit/phase3/test_research_task_contracts.py tests/unit/phase3/test_task_safety_contracts.py
uv run pytest -o addopts='' -ra tests/architecture/test_pr3_05_readonly_boundaries.py tests/architecture/test_pr3_01_boundaries.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py tests/architecture/test_import_boundaries.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_context_reads.py tests/integration/phase3/test_pr3_05_memory_reads.py tests/integration/phase3/test_pr3_05_promotion_validation.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_01_concurrency.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_04_queries.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_replay.py
```

Observable completion: evidence includes actual commands and collected/passed/
failed/skipped counts, PostgreSQL major version, reader SQL/isolation and
controlled concurrency observations; every required case is mapped to a test.
Static checks and focused suites pass with no unexplained skip or open P0/P1.
No full-suite count is borrowed from an earlier run or asserted for this slice.

Stop rule: apply §4 to any mismatch; never relax a test, add a lint exclusion,
substitute SQLite, bypass guards or expand scope to obtain a pass. Most likely
failure: sequential/mock tests are reported as snapshot-concurrency proof.
Mitigation: real PostgreSQL barriers, observed reader connection/transaction,
a committed concurrent change and explicit evidence for both old and fresh reads.

## 4. Common stop and evidence rules

These rules apply separately to **R1, R2, R3 and R4**.

- Before calling something a blocker/gap, present a side-by-side pair: exact
  authoritative pack/draft path, section/line and quote; exact delivered source
  path, line and quote. Explain the conflict, impact and smallest required owner
  decision. Distinguish a missing planned PR3-05 feature from a missing prerequisite.
  No speculative schema, authority, provider or lifecycle gap is sufficient.
- If the conflict requires a material architecture change or crosses this scope,
  stop the affected subtask for an Architecture Question/owner decision. Do not
  silently weaken access, freeze/history semantics, accepted hashes or locks.
- Report environment/setup failures as **NOT RUN** for checks that could not
  execute, with the failed command, exact error and any actual partial counts.
  An executed failing test is FAIL, never PASS. Do not turn an unavailable DB,
  missing tool, skip, assumed result or historical count into current evidence.
- If any git or uv command fails with a lock or sandbox error, quote it verbatim
  and stop. No alternative command to bypass the failure. Keep uv cache under
  repository `tmp/` before every uv invocation. No commit, push or branch creation.
- Wrap long SQL. No new `noqa`, lint exclusions, guard bypasses or governing
  Harness changes. A pre-existing suppression is not permission to add one.

## 5. Gates and ordering

1. **G0 — planning evidence:** deliver only this file, inspect sources and run
   the two requested static checks. No pytest, database, code or migration work.
2. **G1 — exact implementation approval point:** after director review of this
   concrete plan and before creating/changing the first R1 source, test or contract
   file, the owner must explicitly authorize **“PR3-05 read-only slice, R1–R4:
   context loader, memory read and promotion validation; save excluded.”** Approval
   of the draft's direction, this planning request, S1, or PR3-04 does not imply
   that authorization. The owner's planning-only instruction is the reason for
   stopping here; no permission is requested to perform the already authorized
   planning/static work.
3. **G2 — implementation order:** R1 contracts → R2 context/snapshot → R3 memory
   and validation → R4 focused verification. Review the R1 field/error contract
   before implementing its consumers. New evidence-backed scope conflicts stop
   the affected work under §4; otherwise proceed within the named authorization.
4. **G3 — slice acceptance:** director review uses authoritative specs, diff and
   machine evidence, with no author working memory as a required input. No open
   P0 BLOCKER or P1 MAJOR; report P2 MINOR/P3 SUGGESTION dispositions. The check loop
   supplies whole-suite evidence. Acceptance is only for this read-only slice.
5. **G4 — full PR3-05 remains closed:** PR3-02-S2 and PR3-04 acceptance plus
   resolved D1/D2 and a separately frozen/authorized write pack are still required.
   Do not design or enable saving during this slice. Stop after read-only evidence;
   no gateway/provider/execution/promotion activation follows automatically.

## 6. Verification of this planning task

Only this document is the deliverable. Unit, architecture and PostgreSQL tests
are **NOT RUN — explicitly excluded by the planning-only instruction**. No
database or migration command is run. Future commands in §3 are not evidence.

Required command:

```sh
git diff --check HEAD
```

Exit code **0**. Exact output: empty (no stdout/stderr).

Required Ruff invocation, including repository-local cache setup:

```sh
mkdir -p tmp/pr3-05-readonly-uv-cache && UV_CACHE_DIR="$PWD/tmp/pr3-05-readonly-uv-cache" uv run ruff check .
```

Exit code **0**. Exact combined output, in observed order:

```text
Using CPython 3.12.15
Creating virtual environment at: .venv
   Building researchbase @ file:///Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane117
Downloading pygments (1.2MiB)
Downloading pyright (5.9MiB)
Downloading ruff (11.5MiB)
Downloading pydantic-core (1.9MiB)
Downloading sqlalchemy (2.1MiB)
Downloading psycopg-binary (4.5MiB)
 Downloaded pygments
 Downloaded pydantic-core
 Downloaded sqlalchemy
      Built researchbase @ file:///Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane117
 Downloaded psycopg-binary
 Downloaded pyright
 Downloaded ruff
Installed 34 packages in 91ms
All checks passed!
```

`git status --short` showed exactly:

```text
?? docs/phase3/PR3-05-readonly-slice-plan.md
```

The new file remains untracked because no staging/commit is authorized, so the
required `git diff --check HEAD` does not inspect its contents. A supplemental
`git diff --no-index --check /dev/null docs/phase3/PR3-05-readonly-slice-plan.md`
returned **1** for the new-file comparison with empty output and no whitespace
diagnostics. This is recorded separately, not substituted for the required
command's exit-0 result. No git/uv lock or sandbox error occurred. Ruff's local
environment/cache creation changed no other tracked file.
