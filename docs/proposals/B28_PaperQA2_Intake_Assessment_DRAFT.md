# B28 Real PaperQA2 Integration Intake Assessment — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B28 assesses whether a real PaperQA2 can sit behind the accepted PR2-07
`ScientificRAGCapability`. It authorizes no implementation contract, dependency,
provider activation or persistence change. The familiar contract-draft structure
below is an assessment checklist; its implementation sections are explicitly
inapplicable or conditional. Approval of this assessment alone cannot authorize code.

Read in this order:

1. Review the authority and offline baseline (§1), then the upstream evidence gaps (§3).
2. Decide whether to retain the fake and record deferral, or commission a separately
   authorized subprocess feasibility slice (§2). Full library embedding is higher risk.
3. Resolve rights, dependency inventory, data egress and sandbox questions (§§3–5).
4. Preserve the accepted DTOs and existing error mappings (§11); do not design a
   new API, migration or execution-record schema to finish intake.
5. Use §12 only to scope a later execution pack. Keep deterministic fake tests as
   the gate; live output cannot replace them. Record actual verification in §14.
6. Obtain the exact owner dispositions in §13, then stop.

Five review failures: claiming the fake is real PaperQA2 acceptance; inventing a
verified pin/license/dependency count; letting upstream tools write canonical
state; sending source text or secrets without reviewed policy; treating this
assessment or a successful live answer as Phase 2 exit approval.

Recommendation: retain fake + recorded deferral now. If the owner commissions
further work, assess a thin subprocess adapter first, subject to the full intake
gate. No network lookup or install was performed for this document.

## 1. Purpose, authority and inspected baseline

| Source | Binding consequence |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), scientific invariants and adapter boundary; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md); [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | One canonical owner; frozen exact-version provenance; third-party output is candidate material. No new canonical entity for an upstream index. |
| [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§18–19, 24, 26, 38, 52 | Common Application boundary; adapter version pin, security/license review and regression; no silent error or security-policy changes. |
| [Phase 2 Spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§11–12, 29, 41.4, PR2-07; [TDG2 11](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md), TDG2-04/06–10 | PaperQA2 is conditional on activation evidence; indexes are derived, untrusted serialization forbidden, credentials injected, project access and egress denied by default. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 22; [ADR-0008](../architecture/adr/ADR-0008-phase2-literature-technology-gate.md) | Review exact revision, license, scripts and permissions before approval; external tools never own or directly mutate canonical persistence. |
| [PR2-07 slice](../phase2/PR2-07-conditional-slice-01.md) and [evidence](../phase2/PR2-07-conditional-slice-01-evidence.md) | Accepted conditional boundary/fake; no real package, model, index, credential, network, retained write or live registration. Formal PR2-07 acceptance remains blocked. |
| [Reference inventory](../phase2/reference_system_inventory.md) and [exit report](../phase2/phase2_exit_report.md) | `paperqa2` is unselected/DEFERRED, rights/advisories unresolved; no Phase 2 exit success follows from B28. |

The current implementation is
[src/researchbase/application/scientific_rag_provider.py](../../src/researchbase/application/scientific_rag_provider.py).
`pyproject.toml` targets Python >=3.12,<3.13; neither it nor `uv.lock` includes
PaperQA2. `harness.lock.yaml` supplies no PaperQA2 execution pin. This repository
contains no verified upstream release metadata, source/license bundle or resolved
PaperQA2 dependency graph. Earlier draft descriptions of repository head are
historical; this assessment uses current code, including novelty persistence.

## 2. Scope, dependency boundaries and non-goals

| Alternative | Benefit | Cost / disposition proposed here |
| --- | --- | --- |
| Keep fake + recorded deferral | Existing offline candidate boundary remains reproducible; no added package or egress. | No real retrieval capability or PR2-07 completion. Recommended immediate choice; owner must explicitly retain the blocked milestone. |
| Thin subprocess adapter | Separate executable environment, credentials and disposable project/corpus workspace can limit dependency and filesystem exposure. | Requires a separately designed bounded wire protocol, process cancellation, pin/lock and OS sandbox. A subprocess alone is not a sandbox. Preferred next feasibility option, not authorized here. |
| Full library in ResearchBase process | Direct calls and fewer process-boundary conversions may be convenient. | Upstream imports, dependencies, secrets and tool behavior share the application's process. Python 3.12 and existing dependency compatibility must be proved. Defer pending stronger isolation evidence. |

No alternative may replace SourceVersion or LiteratureEvidence ownership, change
canonical hashes, or bypass the existing promotion and independent verification
paths. This assessment adds no runtime dependency or new infrastructure.

## 3. Upstream intake and evidence gaps

| Item | Verified offline / candidate | Human online evidence required before selection |
| --- | --- | --- |
| Authoritative project | TDG2 links `https://github.com/Future-House/paper-qa`. | Confirm repository ownership, release provenance, signed/tagged release where available and exact immutable commit. |
| Exact package and pin candidate | Investigate distribution **`paper-qa==5.0.0`**, import name **`paperqa`**, with no extras initially. These identifiers and this version are an unverified investigation target, not a repo-resolved or approved pin. | Confirm that this exact distribution/release exists, implements the intended PaperQA2 generation/API, supports Python 3.12 and matches the authoritative commit. Record wheel/sdist hashes and selected extras. If unsuitable, return a new explicit candidate for review; never silently select latest. |
| License | Unresolved in the inventory; no permission inferred. | Inspect the exact revision's LICENSE/NOTICE and distribution metadata, dependency licenses and required notices; record SPDX expression and redistribution obligations. Do not assume a project name or remembered license is sufficient. |
| Service and content rights | No provider or source license is approved by this intake. | Review each selected LLM, embedding, search/full-text service's dated terms: retention, training, region, subprocessors, deletion, rate limits, commercial use; check source access, upload, quotation, cache and redistribution rights separately from software license. |
| Transitive size | **Unknown**, both unique distributions and dependency edges; no tree is present to count. Zero locked PaperQA distributions in ResearchBase is not a zero-dependency tree. | Produce an exact hash-locked graph/SBOM for Python 3.12 and each target platform, including selected extras, markers and build dependencies. Report direct/unique transitive counts, edge count, download/installed size and native/system requirements separately. |
| Notable packages | No PaperQA2 membership is verified. Current ResearchBase uses Pydantic and dev-only `httpx2`; compatibility cannot be inferred. | Specifically inspect whether the chosen release brings `litellm`, `lmi`, `aviary`, `openai`, `tiktoken`, NumPy, PDF parsers such as PyMuPDF/`pypdf`, and HTTP clients. This is a risk checklist, not a claimed dependency list. Identify provider routers/telemetry, agent tools, native wheels, parser licenses and conflicts with current pins. |
| Security and maintenance | No dated upstream advisory review is attached. | Review advisories, release notes, install/build scripts, dynamic downloads, tools/hooks, telemetry and serialized-index loading at the exact commit. Assign a patch owner and retain review date and evidence. |

Human follow-up is necessary because this task is repository-only, with no
network installs. The candidate above is deliberately not advertised as current,
supported, vulnerability-free or activation-ready. Unknowns keep intake blocked.

## 4. Proposed commands, DTOs and historical readback

No new command or read API. The existing synchronous
`answer(request: ScientificRAGRequest, context: ScientificRAGCallContext) -> ScientificRAGResponse`
returns candidates in memory. §11 inventories that boundary without extending it.
There is no B28 history table, receipt, canonical event or retained answer write.
An owner-approved later execution pack must decide how authorized exact source
bytes are supplied: the current request carries IDs, not document bytes or file
paths. Do not resolve this gap by granting upstream database or CAS access.

## 5. Schema and literal hash proposal — no migration

None. Provider indexes, embeddings, prompts and tool state remain adapter-owned,
derived and rebuildable (TDG2-08/10). No vendor ID becomes a canonical reference;
a private mapping must resolve citations back to the exact requested SourceVersion.
Existing SourceVersion/LiteratureEvidence material and hashes stay authoritative.
Cache scope must distinguish project/corpus, exact versions, adapter/upstream/model
configuration and access scope; reuse cannot imply current validity or permission.

Data-flow assessment for a later adapter:

- Remote generation can disclose the question, instructions, retrieved excerpts,
  source metadata and intermediate summaries to the selected LLM endpoint.
- Remote embedding can disclose corpus chunks as well as query text to a distinct
  embedding endpoint. Calling a local index does not establish local processing.
- Discovery/full-text tools can disclose queries, identifiers and client/network
  metadata to additional services. Disable autonomous discovery initially: PR2-07
  confines answers to caller-selected exact sources.
- Keys authenticate to approved destinations only, injected into the isolated
  worker; never include them in prompts, DTOs, canonical rows, artifacts or logs.
  No key names/providers/default endpoints are confirmed by the repo for PaperQA2.
- Local providers would need separate feasibility evidence, model/license pins and
  proof of no downloads/telemetry; they are not an approved offline configuration.

These are exposure paths to verify against the chosen release, not assertions
about observed traffic. Require a destination/payload map, retention policy,
project data classification, allowed source rights and a cost budget before egress.

## 6. Error contract — use existing categories only

The current fake raises `ValueError` for invalid candidates and pre-dispatch
cancellation. It does not implement an HTTP endpoint or translate those failures
into ResearchBaseError. The table in §11 fixes existing transport mappings for
future assessment, not new behavior. Provider failures must eventually be
sanitized; raw exceptions may contain keys, URLs, source text or provider bodies.
Do not invent `PAPERQA_*` codes or claim cancellation is already normalized.

## 7. Transactions, concurrency and failure recovery

No B28 transaction or lock. A later isolated call must hold no SQLAlchemy Session,
UoW, DB connection or canonical write credentials while doing external work.
The parent controls authorized source material; the worker has only a disposable
project/corpus workspace, no repository/home/DB/CAS mounts, least-privilege user,
restricted process execution and deny-by-default network. Approved egress must
cover each configured model, embedding and retrieval destination; redirects and
DNS/IP destination policy need separate review. Existing transport policy must
not be assumed to cover upstream libraries automatically.

Bound wall time, memory, CPU, processes, disk, request/response bytes, tokens,
spend and retries; kill the process tree on cancellation/timeout. Numeric budgets
remain owner decisions, not new accepted port limits. No shell interpolation or
upstream tool execution from retrieved instructions. Treat PDFs and text as
untrusted data; reject downloaded serialized indexes/pickle and rebuild locally.
These are admission requirements; no sandbox or supervisor is implemented here.

Patching requires a new exact upstream pin and resolved lock, release/advisory and
license review, sandbox/egress review and deterministic compatibility regression
(Cross-Phase §19 and §52.2). Rollback disables live selection, revokes its keys,
terminates workers and restores the fake; retain failure evidence with secrets
removed. Rebuild disposable indexes under a previously reviewed pin only when
separately re-enabled. Do not downgrade or rewrite canonical scientific history.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

A later pack must name tests for upstream import/version mismatch, source-set
confinement and private-ID mapping, malformed/oversized response, locator/byte
mismatch, hallucination/contradiction retention, cancellation and process-tree
termination, timeout/uncertain result, bounded retries/cost, denied network and
filesystem access, secret redaction and no DB/CAS writes. Replaying approved
fixtures must not deserialize upstream indexes. Recorded samples need content
rights, redaction and exact upstream/config attribution.

The fake remains the deterministic merge gate. Freeze fixture text, timestamps,
source IDs and provenance; never require credentials or live model output in CI.
Opt-in live checks provide dated compatibility/quality evidence, not deterministic
scientific truth or a substitute for M3 promotion/verification tests. Do not
promise model-output determinism from temperature settings or model names.

## 9. Acceptance criteria and evidence boundary

B28 acceptance means the owner has an honest intake assessment and unresolved
items, not that PaperQA2 is enabled. Real activation still requires TDG2 evidence,
a separately approved execution pack, compatibility/security/rights review and
explicit enablement. Owner-recorded deferral cannot silently waive Phase 2's
required PaperQA2 milestone. No full-suite, live-provider or Phase-exit PASS is
claimed here; the loop supplies full-suite evidence separately.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| PaperQA2 / `paper-qa` / `paperqa` | Reference system / proposed distribution / proposed import; exact release mapping awaits verification (§3). |
| Pin / lock / SBOM | Exact version+commit+artifact hashes / resolved platform-specific dependencies / inspectable component and license inventory. |
| Capability / fake | ResearchBase-owned candidate port / disconnected caller-supplied test implementation, not real PaperQA2. |
| Candidate / promotion | Untrusted proposed answer or excerpt / existing Application path admitting validated canonical material. |
| SourceVersion / locator | Exact canonical source version / typed proposed span, whose syntax alone does not verify bytes. |
| Egress / sandbox | Data leaving the worker / enforced resource, filesystem, process and network boundary. |
| UoW / SHARE / REPEATABLE READ | Database transaction boundary / write-snapshot coordination lock / single-snapshot read isolation. |
| Deferral | Recorded blocked work; neither acceptance nor implementation authorization. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Intake only; retain the fake; prefer assessing subprocess isolation over shared
library imports if further work is authorized. No runtime registration, package
install, new schema, dependency changes or contract extension. Upstream and
service rights remain unknown. Every material upstream dependency must be pinned
when enabled; a reference URL or proposed version is insufficient.

### 11.2 Pinned error mappings

Mappings match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py). These are available categories,
not newly implemented RAG translations or routes.

| Code | HTTP | CLI exit | Existing category relevant to later review |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Invalid caller material; provider-shape failure classification needs the later pack. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing trusted caller identity. |
| FORBIDDEN | 403 | 3 | Denied project access. |
| SOURCE_VERSION_NOT_FOUND | 404 | 3 | Exact source missing. |
| VERSION_NOT_FROZEN | 409 | 4 | Required frozen input absent. |
| ADAPTER_UNAVAILABLE | 503 | 5 | Disabled/unavailable adapter. |
| ADAPTER_VERSION_MISMATCH | 409 | 4 | Selected adapter pin mismatch. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Existing canonical closure admission failure. |
| INTERNAL_ERROR | 500 | 1 | Sanitized unexpected-error fallback, not an ErrorCode enum member. |

### 11.3 DTO fields, Python types and limits

Inventory of the frozen dataclasses in `scientific_rag_provider.py`; no added DTO,
transport schema or enum. Bounds are Python character counts, not byte budgets.

| Type | Fields and existing bounds |
| --- | --- |
| RetrievalConstraints | `max_evidence_candidates: int = 20`, exact int (not bool), 1..100. |
| ScientificRAGRequest | `question: str`, nonblank <=16,000; `source_version_ids: tuple[UUID, ...]`, nonempty, unique, exact UUID objects; `retrieval_constraints: RetrievalConstraints`. No source-count maximum is enforced. |
| ScientificRAGCallContext | `cancellation_requested: Callable[[], bool]`. No deadline, budget, credential or project field. |
| SourceLocator | `page: int | None` positive exact int; `section`, `figure`, `table: str | None`, nonblank <=128, no surrounding whitespace, controls or URI-like prefixes; `paragraph: str | None`, positive decimal ordinal; `quote_span: str | None`, `char:start:end` with 0<=start<end and paragraph required. At least page/section/paragraph/figure/table must exist. Actual byte/span bounds await promotion. |
| EvidenceCandidate | `source_version_id: UUID` exact UUID; `locator: SourceLocator`; `excerpt: str`, nonblank <=4,000. |
| ScientificRAGResponse | `answer_candidate: str | None` <=16,000 nonblank if present; `evidence_candidates: tuple[EvidenceCandidate, ...]`; `contradictions`, `missing_evidence: tuple[str, ...]`, each note nonblank <=1,000; `adapter_id`, `adapter_version`, `provider_id: str` nonblank <=128; `model_id: str | None` nonblank <=256 if present; `retrieval_query: str` nonblank <=16,000; `retrieved_at: datetime` timezone-aware (UTC is not enforced by this DTO). |

Response validation requires retrieval_query == question, candidate count <=
requested maximum, evidence for a nonnull answer, requested-source confinement
and distinct `(source_version_id, locator)` pairs. It preserves supplied order;
there is no response sorting, note-count bound or aggregate byte limit. The
fake requires `fake-scientific-rag` / `1` / `test-only` provenance by default.
There are no RAG enum classes: these identifiers are strings, not a closed
production provider vocabulary. Proposed subprocess serialization and operational
bounds require separate review; do not quietly strengthen accepted DTO semantics.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

```sql
-- B28: no DDL. New tables/columns/types/indexes/constraints/triggers: none.
-- No migration revision is allocated; no generic JSON or soft-reference owner.
```

There are consequently no new SQL field types or constraint names to specify.
Existing DTO UUID/datetime types are not new database fields. Migration
[0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) uses
`pr215_complete_decision`, `pr215_complete_conclusion` and
`pr215_complete_review` constraint triggers, `DEFERRABLE INITIALLY DEFERRED`,
for existing Decision completeness; none is a RAG persistence mechanism.
A later request for canonical storage must return for architecture/contract
review rather than invent DDL inside this intake.

### 12.2 Exact lock order and transactions

| Operation | B28 order |
| --- | --- |
| `ScientificRAGCapability.answer` / fake | In-memory request screening → cancellation check → candidate validation/return. No UoW, table/advisory/row lock or retained write. The fake appends to its in-memory calls list after cancellation screening. |
| B28 commands and exact-ID reads | None added; no lock sequence to implement. |
| Later canonical promotion | Invoke the owning existing Application command separately; do not substitute an adapter transaction or copy Decision/Novelty locks. |

For any separately designed snapshot-consistent write, follow the **current**
[decision_repository.py](../../src/researchbase/persistence/decision_repository.py)
and [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py):
new READ COMMITTED UoW → `LOCK TABLE <owning command's exact ordered table set> IN SHARE MODE`
as FIRST statement → configured timeouts → that command's request advisory and
target locks → authorization/reads → writes and deferred checks → fresh-clock
final authorization → commit. Novelty `prepare` currently takes its N SHARE
before its advisory and Claim row locks; older proposal sequences are not a
reason to invert current code. B28 defines no table set, namespace or new command.
Read paths use one REPEATABLE READ snapshot and no explicit table, advisory or
row locks. External calls never occur while these database resources are held.

### 12.3 Ordered build steps and module paths

No executable build steps are authorized. A later pack should be prepared in
this order, with actual scope and paths approved before implementation:

1. Collect §3 evidence against `pyproject.toml`, `uv.lock`, `harness.lock.yaml`
   and `docs/phase2/reference_system_inventory.md`; approve a reproducible isolated
   dependency environment before touching these files. B28 changes none of them.
2. Reconcile the accepted `src/researchbase/application/scientific_rag_provider.py`
   with authorized source-material delivery, worker wire format and budgets.
   Inspect `src/researchbase/application/literature_evidence.py` for existing
   promotion; never import persistence into the worker.
3. Specify a new adapter location under `src/researchbase/adapters/` only in that
   later pack; no module or subprocess protocol is reserved by this assessment.
   Inspect `src/researchbase/api/app.py` and `src/researchbase/cli/composition.py`
   before proposing opt-in composition. No route or CLI command follows from B28.
4. Specify compatibility, sandbox, fault and rollback tests alongside the real
   adapter; preserve the current tests below. Run focused checks and collect
   dated optional live evidence, then obtain separate activation approval.

### 12.4 Test artifacts and required cases

| Existing file | Evidence relevant to this intake |
| --- | --- |
| `tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py` | Exact-source confinement, typed spans, opaque-ID rejection, duplicate and text/candidate bounds, query/provenance mismatch, cancellation and deterministic fake. |
| `tests/architecture/test_import_boundaries.py` and `tests/test_architecture.py` | Existing layering and repository architecture checks. |
| `tests/integration/phase2/test_m3_evidence.py` | Optional focused downstream regression: exact source bytes/locators, independent verification and immutable evidence. It does not exercise a real PaperQA2 or B28 write. |

No test file is added by documentation intake. §8 lists obligations for a later
pack, not present tests. Run static checks and focused unit/architecture checks;
no PostgreSQL suite is directly touched because no persistence behavior changes.
If a downstream M3 regression is attempted, report prerequisites/failures honestly.
Reserve the whole suite for the loop.

### 12.5 Not in this slice

Implementation contract; real adapter or worker; dependency resolution/install;
new DTOs/enums/error codes; sandbox enforcement; model downloads or inference;
network calls; credential provisioning; source uploads; new DDL, canonical write,
index service or vector database; automatic evidence promotion; PR2-07 or Phase 2
acceptance; Phase 3 runtime or agent orchestration.

## 13. Open questions for the owner — override register

Recommendation: approve intake as documentation, retain fake + explicit blocked
real-integration deferral, and commission subprocess feasibility only after named
owners can complete the evidence. Record each disposition explicitly:

| Decision required | Recommended disposition / exact missing choice |
| --- | --- |
| Accept B28 scope? | Intake only, no implementation authorization or acceptance waiver. |
| Choose alternative and milestone status? | Keep fake + recorded deferral now; real PR2-07 remains blocked. Any scope/gate change needs explicit architecture disposition. |
| Who owns upstream verification and by when? | Name technical owner and due date; verify or replace `paper-qa==5.0.0`, import/API mapping, commit and artifact hashes; approve exact extras/platforms and graph counts. |
| Who signs rights and security evidence? | Name license/security reviewers; require license/NOTICE/SBOM, dated advisories, service/content rights and patch obligations before activation. |
| Which data may leave, to whom? | Select LLM/embedding/retrieval providers, endpoints/models, region, retention/training policy, permitted projects/source licenses and secret custodian; default remains no egress. |
| Which isolation and budgets? | Prefer subprocess feasibility; specify supported OS, enforced sandbox, allowed mounts/destinations, source delivery, wall-time/CPU/memory/disk/process/byte/token/spend/retry limits and cancellation policy in a separate pack. |
| Who maintains and can stop it? | Name patch/on-call owner and disable authority; require key revocation, worker termination, fake fallback and reviewed rollback pins. |
| What authorizes further work? | Separate approved execution pack with bounded scope, test paths and admission evidence; live success never replaces fake/M3 gates or owner acceptance. |

## 14. Documentation verification note

Verification results are recorded below after focused commands complete. No
network installation, dependency change, implementation, commit or branch is
part of this task. Full-suite evidence belongs to the loop.

Commands executed from this worktree using the existing shared environment (no
install or sync). `E` below expands to
`/Users/fengwang/Documents/ResearchBaseProject/.venv/bin`; the worktree has no
local `.venv`.

| Exact command (`E` expanded as above) | Observed result |
| --- | --- |
| `$E/ruff check .` | PASS, all checks passed. |
| `$E/ruff format --check .` | PASS, 736 files already formatted. |
| `$E/pyright` | FAILED environment discovery: missing worktree `.venv`; 1,332 errors, 2 warnings. Not counted as PASS. |
| `$E/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS, 0 errors, 0 warnings, 0 informations. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $E/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/architecture tests/test_architecture.py` | Exit 1: 14 setup errors in `test_pr2_19_boundaries.py`, missing explicit disposable PostgreSQL admin URL. Quiet output did not print a passed-count summary. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $E/python -m pytest -o addopts='' -ra -p no:cacheprovider tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/architecture tests/test_architecture.py --ignore=tests/architecture/test_pr2_19_boundaries.py` | PASS, 183 passed, 4 Alembic deprecation warnings in 5.21s (17 PR2-07 unit cases; remaining 166 architecture cases). Excluded PostgreSQL-backed architecture file is not passing evidence. |
| `/opt/homebrew/opt/postgresql@18/bin/psql -X -h /private/tmp -p 5432 -d postgres -Atc "SELECT current_user, current_setting('server_version'), rolsuper, rolcreatedb FROM pg_roles WHERE rolname=current_user"` | Exit 2, local socket connection denied: Operation not permitted. No database query executed. |
| `git diff --check` | PASS. |

No PostgreSQL persistence suite is touched by this documentation-only change.
PostgreSQL-backed architecture coverage remains blocked as above; M3 integration
was not run. The full suite was not run. Only this proposal is changed.
