# Defensive Unresolved-FK Read (B27) Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B27 proposes the unresolved-formal-FK suffix of PR2-19 F2b: an authorized formal
read must fail if a required exact dependency cannot resolve, including after
privileged fixture corruption. This document authorizes no implementation.

Build in this order after approval and separate execution authorization:

1. Confirm the reader inventory and authoritative baseline (§1–2).
2. Preserve edge rows and distinguish missing roots from missing dependencies
   (§3–6, §11). Keep existing DTOs and hashes.
3. Wire every standalone reader through one lock-free REPEATABLE READ UoW;
   reuse that UoW for nested verification (§7, §12.2).
4. Add narrowly privileged corruption fixtures and normal-role controls,
   then reader and transport cases (§8, §12.3–4).
5. Run focused checks, publish exact evidence, and stop (§9).

Review essentials: preserve unresolved edges; distinguish missing root from
missing dependency; authorize before disclosure; use one snapshot without
explicit read locks; prove privileged corruption separately from ordinary SQL
denial. See glossary (§10), decisions (§11) and implementation guide (§12).
No B27 execution pack is supplied; this proposal does not replace authorization.

## 1. Purpose, authority and inspected baseline

| Authority | Rule carried into B27 |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 9–13 | Deterministic facts precede authority; formal provenance resolves exact frozen versions; immutable history is not repaired in place. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Focused Phase 2 corrections govern; current read entitlement and advancing trusted time remain required. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | Existing typed entities, relations and snapshots own facts; B27 adds no canonical concept. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§12–18, 24, 28 | Same Application boundary for Human/Agent, exact references, stable errors and additive compatibility. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§34, 37–39, 49–52 | Frozen closure, integrity/failure evidence and Phase 1 regression. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–5, 7 | Formal-provenance reads verify material/bindings; no silent hash warning; typed FK/RESTRICT and immutable history. |
| [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md) | Existing concrete FK shapes and literal hash material remain unchanged; SUPERSEDED frozen material can resolve historically. |
| [Minimal Decision Contract 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§5–6 | Exact complete saved basis; entitled replay preserves history; corruption cannot become successful replay. |
| [Harness Integration](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 19 | Application boundary and executed evidence precede completion claims. |

Inspected code locations; these are audit targets, not demonstrated end-to-end bugs:

| Evidence | Observation / audit required |
| --- | --- |
| [publication_repository.py:394–403](../../src/researchbase/persistence/publication_repository.py#L394) | CLAIM_SNAPSHOT uses inner joins through the selected snapshot. SQL omits that branch if its target is absent; audit whether another verifier already denies the request. |
| [publication_repository.py:355–368](../../src/researchbase/persistence/publication_repository.py#L355) | Experiment projection uses COALESCE across Measurement branches. Audit separate required-target resolution under privileged corruption; masking is not established by a test here. |
| [scientific_conclusion.py:764–769](../../src/researchbase/application/scientific_conclusion.py#L764) | `read` calls authorization and `_view` without an explicit isolation selection in this method; audit the injected UoW before concluding effective isolation. |
| [decision_repository.py:116–128](../../src/researchbase/persistence/decision_repository.py#L116) | Basis uses target inner joins; audit unresolved-edge retention independently of hash denial. |
| [test_pr12_closure.py:422–468](../../tests/integration/test_pr12_closure.py#L422) | Existing dangling-Measurement diagnostic fixture; reuse its narrowly disabled trigger pattern. |

[PR2-19 F2b](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md) and its
[dependency inventory](../../tests/integration/phase2/test_pr2_19_dependencies.py)
still list this suffix as blocked. B27 does not change that inventory.

## 2. Scope, dependency boundaries and non-goals

The bounded slice covers existing formal closure consumers: Run/Claim diagnostic
validation; manuscript scientific trace; exact ScientificConclusion and internal
review reads; the three exact novelty reads; and saved Decision verification on
`record_decision` replay. Decision has no standalone read method in the inspected
service; do not invent an endpoint. Shared nested literature/source/snapshot
verification is included only where reached by these consumers.

A **required reference** is a selected FK, owning identity or relation membership
required by the accepted reader contract. Optional nulls and permitted empty
collections stay optional. Dependencies are accepted readers and disposable
PostgreSQL corruption conventions; B27 approval alone does not accept Phase 2.

## 3. Invariants and conservative judgments

1. Enumerate stored edges before target lookup; preserve unresolved edges with
   LEFT JOIN or typed batches, including nonnull snapshot and statistical-result
   references. Target/project predicates must not erase them.
2. Verify exact identity, ownership, required frozen material and existing hashes;
   preserve occurrence order/multiplicity. Never substitute `latest/current`.
3. Detect removed membership using existing sealed hashes/cardinality, without
   a shadow manifest. MISSING and NEVER_REQUESTED both prevent formal success.
4. Authority cannot override deterministic corruption. Preserve intact historical
   reads under existing STALE/INVALID and supersession policies.

## 4. Proposed commands, DTOs and historical readback

Keep existing signatures and DTOs (§11.3); formal reads return a complete DTO or
raise. Diagnostic `ClosureReport(complete=False, ...)` remains a valid diagnostic,
never formal success. Formal consumers translate incomplete reports to
PROVENANCE_CLOSURE_VIOLATION; diagnostic NOT_FOUND and
PROVENANCE_CONTEXT_INCOMPLETE remain strings, not new transport enums.

## 5. Schema and literal hash proposal — no migration

No schema, persistence mechanism, dependency or hash material change. Existing
guards (§12.1) reject ordinary dangling references; B27 reads verify corruption
outside those guarantees without writing findings, events or corrections.

## 6. Error contract — proposed use of existing categories

Use §11.2. Normalize known absence/malformed shapes only at a saved-dependency
boundary, following `DecisionService._basis`. Never relabel arbitrary NOT_FOUND,
programming, connection or timeout failures as corruption. Unexpected exceptions
retain sanitized INTERNAL_ERROR; public corruption details are null.

## 7. Transactions, concurrency and failure recovery

Standalone reads follow §12.2: one REPEATABLE READ, READ ONLY snapshot, no explicit
locks or writes, including nested authorization. Automatic SELECT ACCESS SHARE
locks are expected. Check entitlement before disclosure and return with fresh
`clock_timestamp()` and external credential checks; the same durable snapshot
cannot see later committed revocation. Do not reopen or retry into success.
Nested write verification retains its caller's isolation and adds no locks.
Corruption is nonretryable and leaves zero canonical delta; exact UUID replay
must verify saved provenance rather than recreate it.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 requires committed dangling edges, restored guards, fresh reader UoWs and
zero canonical delta. Pair normal-role FK denial and intact controls. Cover both
all-missing and mixed batches so empty INNER JOIN output cannot appear complete.

## 9. Acceptance criteria and evidence boundary

Acceptance requires §12.4 coverage for every §2 consumer, PostgreSQL 18.x
corruption/normal-role evidence, SQL capture proving one snapshot without explicit
read locks/writes, and no open P0/P1. Report focused checks exactly and stop;
only accepted implementation can unblock F2b. The loop owns the full suite.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Requested root | Exact record named by caller, subject to existing project read policy. |
| Required dependency | Exact reference already stored in the selected root's accepted formal closure. |
| Unresolved FK | A stored selected reference whose required target cannot resolve in the read snapshot. |
| Privileged corruption | Test-only bypass of named guards in a disposable DB; never a normal write path. |
| Formal success | A complete verified trace/readback or accepted replay, not a diagnostic report. |
| MISSING / NEVER_REQUESTED | Requested lookup absent / required context never loaded; existing BatchLookupState values. |
| Protected reads | Existing UoW adapter mode avoiding locking queries; no independent snapshot or cache. |
| F2b suffix | The unresolved-formal-FK portion still blocked in the PR2-19 failure plan. |

## 11. Decisions taken in this draft

These are proposed pinned decisions for owner review, not implementation approval.

### 11.1 Scope and policy decisions

The bounded inventory is §2. Deny complete formal readback on any unresolved
required reference; retain existing diagnostic reports. Add no schema, persistence
side effect, recovery workflow, public error enum or broader authorization policy.
Standalone reads use §7; existing command replay retains its write protocol.

### 11.2 Pinned error mappings

Mappings below match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py). INTERNAL_ERROR is a fallback
string, not an ErrorCode member.

| Condition | Code | HTTP | CLI exit |
| --- | --- | ---: | ---: |
| Malformed exact identifier/input | VALIDATION_ERROR | 422 | 2 |
| No verified principal | AUTHENTICATION_REQUIRED | 401 | 3 |
| Current entitlement unavailable | FORBIDDEN | 403 | 3 |
| Authorized requested root absent | NOT_FOUND | 404 | 3 |
| Saved required dependency absent, unresolved context, or corrupt binding/hash | PROVENANCE_CLOSURE_VIOLATION | 409 | 5 |
| Normal write rejected by FK, where existing UoW normalization applies | REFERENTIAL_INTEGRITY_ERROR | 409 | 5 |
| Unexpected failure, sanitized fallback | INTERNAL_ERROR | 500 | 1 |

Cross-project root behavior follows each existing reader's nondisclosure policy;
B27 introduces no global existence lookup. After entitlement to the root, a
saved dependency's wrong ownership is closure failure, not an informative 404.
Normal-role SQL probes assert SQLSTATE 23503 for the FK itself; immutable guards
may reject UPDATE earlier, so use an allowed INSERT shape to isolate FK denial.

### 11.3 DTO fields, Python types, limits and enums

| Surface | Pinned contract |
| --- | --- |
| Existing exact read arguments | Exact `UUID` for project/root and required parent IDs, `VerifiedPrincipal` from trusted authentication; no strings masquerading as Application UUIDs, selector/latest, caller authority or new B27 options. Novelty retains `ExactReadQuery(project_id: UUID, id: UUID)`. |
| Formal readback | Existing dataclasses unchanged. Required target IDs remain `UUID`, required hashes `str` matching `[0-9a-f]{64}`; do not widen them to nullable for corruption. Optional fields retain their existing meaning and types. |
| Diagnostic report | `ClosureReport(complete: bool, visited_count: int, violations: list[ClosureViolation])`; nonnegative visited_count, complete iff no violations. Violation fields: `code: str`, `object_type: str`, `object_id: UUID`, `path: list[str]`, `message: str`. Preserve existing per-validator sorting in closure.py. |
| Batch context | Existing `BatchLookup[T](values: dict[UUID,T], requested_ids: frozenset[UUID])`, values a subset of requested IDs. Enum values exactly `found`, `missing`, `never_requested`; no UNKNOWN success state. Cache lifetime is one request/UoW. |
| Public error | Existing `{error: {code: str, message: str, details: dict[str, Any] \| None}}`; B27 corruption uses message `"saved formal provenance is unresolved"`, details null. No diagnostic identifiers in public details. |
| Bounds | One exact root per existing read invocation; no new batch/list endpoint, depth cap, truncation or size limit. Retain existing owner DTO collection/text limits. Exceeding an existing bound cannot yield partial success. |
| Existing material enums | No new status/relation literals. Frozen-material versions resolve under existing FROZEN/SUPERSEDED policy; optional nulls, current validity and diagnostic code strings are not newly invented enum members. |

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

**No migration to build.** This abbreviated existing DDL shape is a review/fixture
map, not SQL to execute or a proposal to recreate tables:

```sql
-- 0042: existing columns and PostgreSQL-generated FK constraint name
-- decision_basis_reviews:
decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
internal_review_record_id UUID NOT NULL
  CONSTRAINT decision_basis_reviews_internal_review_record_id_fkey
  REFERENCES internal_review_records(id) ON DELETE RESTRICT,
ordinal INT NOT NULL CHECK (ordinal >= 0)
-- decision_records: basis_set_hash CHAR(64), content_hash CHAR(64),
-- hash_scheme VARCHAR(32), decided_at TIMESTAMPTZ, all NOT NULL.
-- Existing completeness guards (not new B27 guards):
CREATE CONSTRAINT TRIGGER pr215_complete_decision
  AFTER INSERT ON decision_records DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
-- Same shape: pr215_complete_conclusion on decision_basis_conclusions,
--             pr215_complete_review on decision_basis_reviews.
```

Keep [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) unchanged,
including `pr215_{decision,conclusion_basis,review_basis}_immutable` and
`pr215_{conclusion,review}_basis_guard` (brace notation abbreviates existing names).
The Phase 1 fixture targets nullable UUID `evidence_relations.measurement_id`:
`evidence_relations_measurement_id_fkey`, `evidence_relations_draft_only` and
`pr17d_evidence_relation_update`. Discover exact FK triggers via
pg_constraint/pg_trigger as `_disabled_exact_triggers` does.

Fixtures use allowlisted names in disposable DBs: assert catalog presence,
disable only required triggers, restore in finally and verify tgenabled, then
commit before opening the reader. Restoration does not repair dangling rows;
drop the DB on cleanup. No DISABLE TRIGGER ALL, session_replication_role or
production bypass. DISABLE TRIGGER USER alone does not disable FK triggers.

### 12.2 Exact lock order and transactions

**B27 read protocol (proposed):** in-memory principal/UUID validation → new UoW →
REPEATABLE READ, READ ONLY before data SQL → protected adapters → read
authorization → scoped root → stored edges/targets and nested verification →
hashes/DTO → fresh-clock authorization → return/close without commit. No explicit
table, advisory or row locks, including FOR SHARE/KEY SHARE. Diagnostic Run/Claim
validation follows the same snapshot/edge order, retaining its existing caller
policy. Existing read-only setup example:
[manuscript_freeze_repository.py:46–47](../../src/researchbase/persistence/manuscript_freeze_repository.py#L46).

**Existing write protocols (observed, not B27 build instructions):** the checkout
differs from the task's blanket SHARE-first premise. Source evidence below pins
that discrepancy; B27 authorizes no write-order change. The SHARE-first rule
remains mandatory for the preheld-table snapshot protocol, as coverage and
manuscript freeze demonstrate.

| Command | Observed order and file:line evidence |
| --- | --- |
| `record_decision` (including saved-result branch) | Timeouts → `pr215:decision:{UUID}` advisory → conclusion version FOR UPDATE → `_SNAPSHOT_TABLES` SHARE → authorization/readback. Repository operations: [decision_repository.py:72–92](../../src/researchbase/persistence/decision_repository.py#L72); caller order: [application/decision.py:213–227](../../src/researchbase/application/decision.py#L213). |
| `record_search_coverage` | READ COMMITTED UoW → N SHARE as FIRST SQL → timeouts → `pr218:coverage:{UUID}` advisory → authorization/read/verify/write. [novelty_repository.py:71–82](../../src/researchbase/persistence/novelty_repository.py#L71); caller: [application/novelty.py:564–570](../../src/researchbase/application/novelty.py#L564). |
| `record_prior_art_relation` | Timeouts → `pr218:prior_art:{UUID}` advisory → ClaimVersion FOR UPDATE → N SHARE → authorization/read/verify/write. Conditional order: [novelty_repository.py:74–85](../../src/researchbase/persistence/novelty_repository.py#L74). |
| `record_novelty_assessment` | Same conditional order, namespace `pr218:novelty:{UUID}`: [novelty_repository.py:74–85](../../src/researchbase/persistence/novelty_repository.py#L74); later nonnull predecessor FOR UPDATE: [repository:155–158](../../src/researchbase/persistence/novelty_repository.py#L155), [caller:665](../../src/researchbase/application/novelty.py#L665). |
| Manuscript freeze (preheld-table example) | READ COMMITTED → SHARE as FIRST SQL → timeouts: [manuscript_freeze_repository.py:40–44](../../src/researchbase/persistence/manuscript_freeze_repository.py#L40). No SET LOCAL, advisory or authorization SQL precedes SHARE. |

Novelty forces deferred checks before final authorization/commit:
[application/novelty.py:717–721](../../src/researchbase/application/novelty.py#L717).
Nested B27 verification reuses these transactions and acquires no new locks.

### 12.3 Ordered build steps and module paths

1. In `src/researchbase/application/closure.py`, keep explicit missing/context
   states and diagnostic compatibility; configure standalone snapshot validation
   through the existing `src/researchbase/application/ports.py` /
   `src/researchbase/persistence/uow.py` boundary. In-UoW methods never reopen it.
2. In `src/researchbase/persistence/publication_repository.py`, preserve selected
   snapshot edges before joins; validate result identity separately from result
   inputs. In `decision_repository.py`, retain raw basis rows when targets miss.
   Audit `scientific_conclusion_repository.py`, `internal_review_repository.py`
   and `novelty_repository.py` for the same disappearing-edge pattern within §2.
   Keep fixed typed SQL, existing batching/order and no per-edge N+1 fallback.
3. In `src/researchbase/application/manuscript_scientific_trace.py`,
   `scientific_conclusion.py`, `internal_review.py`, `novelty.py` and
   `decision.py`, normalize known saved-dependency failure at the owning boundary.
   Shared nested literature verification lives in
   `src/researchbase/application/literature_evidence.py`; preserve standalone root
   errors there. Reuse existing validators and literal hash builders.
4. Wire lock-free snapshot authorization and nested protected adapters in
   `src/researchbase/persistence/uow.py`; extend typed ports only if needed.
   Existing error handlers need no new mapping. Keep API/CLI envelopes and
   signatures unchanged; verify transport behavior through their current adapters.
5. Add §12.4 tests, run focused checks and affected PostgreSQL regressions.
   Record exact results and limitations. Do not edit the frozen PR2-19 blocker
   inventory until a separately authorized acceptance update; stop at this slice.

### 12.4 Test files and required cases

All files/cases below are future work. Reuse exported builders and fixture
registration patterns; do not import a test function as a fixture implementation.

| File | Required cases |
| --- | --- |
| New `tests/unit/phase2/test_b27_defensive_closure_read.py` | MISSING vs NEVER_REQUESTED, all/mixed missing batches, unchanged diagnostic types/order; known nested NOT_FOUND normalization vs root NOT_FOUND; no broad exception swallowing; required DTOs never nullable; sanitized code/message/details and HTTP/CLI mappings. |
| New `tests/integration/phase2/b27_fixtures.py` | Reuse `phase2_database_url`, `pr2_19_support.py` builders and the narrow trigger-discovery pattern from `tests/integration/test_pr12_closure.py`; normal role versus explicit privileged connection, committed dangling edges, restored triggers, raw-state assertions and zero-delta snapshots. |
| New `tests/integration/phase2/test_b27_defensive_closure_read.py` | Every §2 reader: intact positive, absent root, missing direct and transitive required target, other-project dependency, optional null allowed. Include dangling Measurement/statistical input, selected missing literature snapshot (empty and mixed branches), missing evidence/SourceVersion/owning identity, missing saved Decision review/conclusion. No shortened trace, latest substitution or success replay. Fresh service after corruption; repeated denial unchanged; permissions deny before disclosure. Pair FK SQLSTATE 23503 controls and immutable guard controls. |
| Same PostgreSQL file | Two independent connections/backend PIDs: establish snapshot, commit test corruption on the other, show the first reader sees one intact snapshot and a fresh read denies; no hybrid. Fixture ALTER locks must be released before inspecting reader locks. Capture SQL and pg_locks: no explicit row/table/advisory lock, writes, hidden project-lock function, or second transaction. Scheduled credential/role expiry at final check denies. Ordinary SELECT ACCESS SHARE is allowed. |
| Extend `tests/integration/phase2/test_pr2_19_integrity.py` | F2b suffix invokes a real owning reader against committed unresolved FK, asserts PROVENANCE_CLOSURE_VIOLATION and zero canonical delta. Preserve existing CAS/hash tests and dependency inventory until acceptance. |
| New `tests/architecture/test_b27_defensive_closure_read.py` | Same Application boundary, Domain independent of ORM/transport; no repair persistence, schema/dependency/hash change, fallback current lookup or production corruption switch; standalone/nested SQL capture proves lock-free snapshot reads. |

After implementation run the new B27 tests, then affected existing suites:
`tests/integration/test_pr12_closure.py`,
`tests/integration/phase2/test_pr2_13_scientific_trace.py`,
`test_pr2_11_r2_persistence.py`, `test_pr2_14_internal_review.py`,
`test_pr2_15_decision.py`, `test_pr2_15_decision_schema.py`,
`test_pr2_18_*.py` and `test_pr2_19_integrity.py` in that same Phase 2 directory.
Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`,
and `uv run pytest tests/unit tests/architecture`; use real PostgreSQL 18.x for
integration. Reserve full-suite execution for the loop as instructed by the owner.

### 12.5 Not in this slice

No repair command, backfill, FK weakening/revalidation migration, new canonical
schema, quarantine/event store, generic graph engine, new DTO/endpoint, automatic
impact propagation, grant consumption, owner bypass, external effect, production
failure hook, stronger novelty outcome or implementation of other backlog items.
Do not replace current historical validity policy with universal “must be VALID”.

## 13. Open questions for the owner — override register

| Owner may override before approval | Decision adopted in this draft |
| --- | --- |
| Error versus partial read? | Formal read fails atomically with existing closure code; diagnostic reports retain false completeness and detailed internal violations. |
| Initial scope? | Existing §2 consumers and their reached dependencies, including Decision replay; no new Decision read endpoint or global graph audit. |
| Persistence or migration? | None. Existing typed FK, deferred completeness and hash contracts remain canonical. |
| Concurrent revocation visibility? | One snapshot plus advancing expiry/credential time checks; no claim of seeing post-snapshot durable revocation. A stronger policy needs a separate contract. |

Any override requires corresponding body edits before freeze. Approval and later
implementation authorization remain separate; PR2-19 remains blocked meanwhile.

## 14. Documentation verification note

Observed on 2026-10-16; only this proposal was added. Commands below use
`UV_CACHE_DIR=/private/tmp/rb-b27-uv-cache` to keep tool caches outside the repo.

| Command | Observed result |
| --- | --- |
| `uv run ruff check .` | All checks passed. |
| `uv run ruff format --check .` | 570 files already formatted. |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations. |
| `uv run pytest tests/unit tests/architecture` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 42.73s. Not PASS; no clean-baseline comparison was run. |
| `uv run pytest tests/unit/test_hg1_runner.py::test_socket_lifecycle_one_request_and_cleanup` | 1 failed in 0.06s; AF_UNIX socket bind raised PermissionError: Operation not permitted. |

The single HG1 rerun demonstrates a socket denial for that case only. Attributing
all four failures to the sandbox or calling any failure pre-existing is an
**unverified assumption**. The twelve errors reported missing admin configuration;
that failing set was not rerun with an admin URL or compared with a clean baseline.
These results support no test PASS or regression-free claim.

Review revision checks: static commands above passed again (same counts).
`uv run pytest tests/unit/phase2/test_pr2_15_decision.py tests/unit/phase2/test_pr2_18_novelty_contract.py tests/unit/phase2/test_pr2_19_report_contract.py tests/architecture/test_pr2_18_boundaries.py`
returned **110 passed in 1.63s**. This focused result does not replace the failed
broader run. PostgreSQL was not rerun during revision; its limits remain below.

`grep -n '^## ' docs/proposals/PR2-17_*.md docs/proposals/B27_*.md` was inspected:
PR2-17 has Start here and §§1–13; it has no §14. Exact heading comparison with
PR2-18 gives **15/15 identical top-level headings in order** (including §14),
and PR2-17's shared numbered section sequence matches **13/13**.
The task's exact scope check returned exit 0:
`test -z "$(git status --porcelain -- . ':!docs/proposals' ':!.pipeline')"`.

Focused PostgreSQL attempt (the listed Phase 2 paths share the same directory):

```sh
UV_CACHE_DIR=/private/tmp/rb-b27-uv-cache \
DATABASE_URL=postgresql+psycopg://rb_b27@localhost:5432/postgres \
RB_TEST_ADMIN_URL=postgresql+psycopg://rb_b27@localhost:5432/postgres \
uv run pytest --maxfail=1 \
  tests/integration/test_pr12_closure.py \
  tests/integration/phase2/test_pr2_13_scientific_trace.py \
  tests/integration/phase2/test_pr2_11_r2_persistence.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_18_*.py \
  tests/integration/phase2/test_pr2_19_integrity.py
```

Result: **1 failed in 0.49s**, stopped at the first closure test; PostgreSQL
connections to localhost were denied with Operation not permitted. Remaining
selected PostgreSQL cases were not executed. No live PostgreSQL version was
verified. Local PostgreSQL 18 `initdb` also failed on shared-memory creation
with Operation not permitted, including an attempt with mmap settings. No
database acceptance is claimed. The full suite was not run; it belongs to the
loop. Future tests in §12.4 are not present B27 acceptance evidence.
