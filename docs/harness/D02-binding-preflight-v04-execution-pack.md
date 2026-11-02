# D02 v0.4 bounded development preflight — exact execution pack

ENGINEERING SCOPE independently reviewed PASS before source (p01,
`independent-scope-review-1.json` in the D02-v04-implementation evidence directory).
This records development scope only; source/actual acceptance remain separate.
Parent D02 HIGH, frozen D01 v0.4 at d57a45f, base of this worktree d57a45f.
Authority: D01-v04-FROZEN.json and D02-D03-v04-ADMISSION.json, owner resolution
2026-11-02, and root's independently reviewed D02-dev-provision RESULT.json.
No new owner direction is requested for routine technical choices. Any material
public/scientific contract departure must be referred to root before coding.

## 1. Read order, accepted boundary and real facility

AGENTS→architecture01/02/03/08→Phase3→Harness09→D1 O09/ADR0027→frozen
`docs/phase3/d01-binding-v0.4/`→this pack. Frozen manifest is
`e46523d6b3e899f165c40573a0226ce098c24018709464af1fc946991f6cd853`.
The separately pinned facility receipt is
`.pipeline/logs/reviews/D02-dev-provision-20261102/RESULT.json`, SHA
`aa200178de3fc88379a33c4e524ce8694c99b5082ea5be15d0082235bb23f7aa`.

Use only its actual dedicated development DB and restricted writer, through its
Unix socket. Tests read only approved metadata/head/control data and temporary
protected CAS/lease/installations. No admin URL, DB discovery, actual `.env`/secret,
DDL, GRANT/REVOKE, new/drop DB/role, helper enablement or scientific DML. Root's
existing trust authentication is DEV_ONLY, not A2/reference/production proof.
No service/launchd/runtime/policy/index/registry changes. PG-heavy test slot=1.

Implement an actual read-only observation/installation/CAS/lease preflight and an
opaque process-local **development binding observation proof**, never a consumer
capability, human approval, entitlement or registration. Existing roots remain
unregistered for genuine D1. This child cannot accept a caller boolean, fabricated
observation or FakeConsumerCapability as a proof issuer. Root has not issued an
actual genuine reference/production binding approval; test setup's protected
records are explicit authorized development fixtures, not hidden live authority.

## 2. Exact allowed paths and deltas

No source before independent PASS of this list; any addition needs root scope review.
No migration version file, architecture/D1/frozen-contract change or dependencies.

| Path | Bounded delta |
|---|---|
| docs/harness/D02-binding-preflight-v04-execution-pack.md | This scope/interface/acceptance record |
| src/researchbase/foundation/bearing_binding_contracts.py (new) | Stdlib immutable neutral typed observations/expectations and non-I/O identity protocol; no DB/framework/business imports |
| src/researchbase/foundation/bearing_binding.py (new) | Frozen standardJSON codec, protected-record/CAS/path observation and pure exact comparisons; no DB or approval writer |
| src/researchbase/foundation/bearing_installation.py | Module-owned public one-shot consumption witness retaining original verified approval/manifest/callable/code/PID/expiry; consumer never reads private slots |
| src/researchbase/foundation/local_bearing_registration.py | Public owner-issued binding-identity check and checked local close observation for D02 resource cleanup; preserve existing acquire/check/close semantics; no registration/revoke state machine |
| src/researchbase/persistence/bearing_preflight.py (new) | Fixed PG18 read-only same-snapshot typed observation, bounded queries and whole normalized ACL; receives private connection, never creates engine or issues authority from supplied rows |
| src/researchbase/persistence/database.py | Sole engine/driver creator; retain ordinary APIs, add gated development bound-factory issuer/private pin; preserve no-I/O module import |
| src/researchbase/persistence/uow.py | Delegate existing search-result engine construction through sole creator, preserving exact startup timeout/options and UoW semantics; no actual D03 bound-write adoption |
| migrations/env.py | Delegate engine construction/connection opening through sole creator, preserve online/offline migration behavior; do NOT run migrations locally |
| src/researchbase/hg1_runtime.py | Delegate existing Engine.connect read path through creator's ordinary unregistered connection helper, preserve owning semantics |
| tests/unit/phase3/test_bearing_installation_process.py | Genuine protected fresh-start witness success/fork/consume/replacement negatives; retain existing tests |
| tests/unit/phase3/test_bearing_lease.py | Public identity/checked-close/unknown/fork and old API compatibility |
| tests/unit/phase3/test_bearing_binding.py (new) | Frozen codec/securityACL/record/CAS/error shape; pure comparison cannot mint runtime proof |
| tests/unit/phase3/test_binding_preflight_factory.py (new) | Factory-gate negative/legacy delegation/resource cleanup; no mocked positive DB proof |
| tests/integration/phase3/test_d02_dev_binding_preflight.py (new) | Explicit local facility receipt + writer-only real metadata snapshots, cold protected installation/CAS/lease/pin; never existing admin fixture |
| tests/architecture/test_d02_binding_boundaries.py (new) | Sole-creator alias/direct-driver/dynamic negative AST fixtures and actual shipped-source scan; layering/no activation |
| docs/phase3/D02-binding-preflight-v04-evidence.md (new) | Exact results/limits, dev-only and open D03/ref/prod gates; no whole-task claim |

Ordinary `create_database_engine/create_session_factory`, existing UoW factories,
HG1 and Alembic behavior stay compatible and **unregistered**. Their existing
ordinary Application rights are not genuine D1 authority. The new protected D1
bound-factory path, unlike ordinary factories, must preflight before returning its
new callable. No switch converts an ordinary factory into a verified one.

The import/construction scan covers shipped `src/researchbase` and `migrations/env.py`.
Existing external test/admin harnesses are not deployed D1 entry roots and are not
rewritten or used for D02 PG tests. Network/Unix-socket connects in runner/HTTP
adapters are not database engine creation. The scan resolves known SQLAlchemy/
driver aliases, constants and known dynamic construction patterns; it does not
claim a hostile-Python sandbox. No broad allowlist exemption or weakened existing
architecture test. Entire installed source/immutable import closure remains required.

## 3. Neutral values and genuine installation witness

Names below are engineering APIs, not new scientific commands/ErrorCodes/schema.
`BindingError` is sanitized local failure. Use exact frozen JSON required fields,
no bool/int/float or normalization coercion, duplicate/nonfinite/UTF8/depth/size
bounds. Pure `parse_binding_record` returns immutable closed values plus canonical
bytes/SHA; parsing is never approval. No rebind/approval-file writer in this PR.

Neutral data: DatabaseIdentity(five fields); RoleIdentity(name,oid);
FunctionSignature; FunctionSecurity; ExecuteGrant; HelperIdentity;
DatabaseObservation(identity/head/session/current/helper/Unix observations and
current conservative role/DDL predicate results). All recursively immutable typed
stdlib values. No Session/Connection/driver handle in foundation/Application.

`VerifiedInstallation.consume_for_binding(*, expected, fixed_callable)` returns
one module-owned nonserializable `InstallationBindingWitness` only after matching
original retained protected approval/manifest, actual loaded callable/code/PID,
namespace/host/UID/expiry and original file/import observations to expected v0.4
installation fields. Spent/forged/partially initialized/copied/fork witnesses deny.
Only the issuing installation module reads its private state. Runtime issuance is
never exposed as `make_proof(observed_dict)`; development tests use the actual
controlled installer, not object.__new__ with fake approved fields.

Witness continuity uses its original approved inventory/import roots/record and
callable identity, with only inventoried lazy imports. It exposes a public check
for its original scoped expectations; no raw slot, file descriptor or arbitrary
callable selector is accepted. This is still installation evidence, not owner
approval of any arbitrary DB. New protected binding records are test fixtures
only unless a separately genuine scoped operator approval has actually been issued.

## 4. Protected factory/observation/pin lifecycle

Only `persistence.database.create_binding_preflight_factory(...)` creates this
new bound factory. Inputs are a protected binding record path, genuine installation
proof and the one fixed callable, supplied by protected operator test setup.
**No URL, observation port, Connection, credential, callback or approved boolean
from ordinary callers**. URL is built from the record and matched to the fixed
actual development facility; no admin fallback. Reject connection-affecting ambient
PG variables rather than silently let PGHOSTADDR/service/password override Unix
parameters; no environment/credential contents in errors. Ordinary APIs retain
existing connection semantics, without D1 verification marks.

Private engine uses SQLAlchemy `NullPool`; ordinary compatibility pools are unchanged.
Private engine/one Connection/actual driver connection are captured in this sole
creator. Observe one REPEATABLE READ READ ONLY transaction, explicit bounded
connection/statement/lock timeouts; no SET ROLE, DDL or canonical changes. Complete
control/identity/role/helper/ACL/head projections come from that same snapshot.
Five DB values, role names/OIDs/forbidden direct+indirect predicates, actual Unix
endpoint, helper OID/signature/definitionhash/securityset and complete normalized
ACL match the same protected expected record. Native typed OIDs; explicit
`prosupport::pg_catalog.oid`; no regproc-name/coercion shortcut. ACL max64 actual
rows and normalized entries; never truncate an incomplete observation.

Before proof return: read-only transaction fully ends/idle; original approval,
installation/CAS/lease/owner PID+actual thread and expiry are rechecked. No valid
factory/proof returns on any failure. Hold the same owner-local Connection+driver
pin **without returning to pool/closing/reopening** until owned cleanup. Pool
replacement/auto-reconnect/invalidation denies, not fresh observation masquerading
as original pin. `BoundBindingFactory.preflight()` performs complete root-side
FS/DB revalidation and returns a fresh proof/observation identity; no scientific
transaction locks may be held during this I/O.

`BindingIdentityPort` is non-I/O: `factory_identity: object`,
`connection_identity: object`, `observation_id: object`, and
`assert_factory(identity: object) -> None`. Values are opaque same-object markers,
not UUID/string authority or raw handles. Its persistence-owned opaque proof checks
module-issued state, PID/actual owner thread, captured wrapper/creator/code/root,
expiry and current captured closed/invalidated state; it never queries SQL/FS,
checks a lease fd, triggers lazy pool checkout or reconnect. No arbitrary object
exposing the same public marker is an accepted bound factory. Proofs cannot be
constructed/copied/serialized into a new issuer.

D02 offers only scoped development read sessions from the captured idle connection;
all reads use the authorized restricted role and read-only transaction setup.
Track and close each read session; never pool-handback the pin between preflight
and that session. Normal return/exception clears transaction state before another
preflight. Active session, changed pin/record/lease/callable, expiry or unknown
cleanup invalidates proof and quarantines the new factory, denying further work.
Owner-only cleanup always attempts Session rollback/close then connection/engine
cleanup then module-owned checked local lease close, retaining all errors. Positive
local close is not DB rollback proof or D03 REVOKED acknowledgement. Unknown holds;
no silent retry, new identity or self-reactivation.

The exact public lease seam is `LocalLease.identity_token`,
`assert_binding(*, path, device, inode, uid, mode)` for root-side filesystem I/O,
and `close_checked() -> LeaseCloseObservation`. The latter exposes `lease_identity`
and non-I/O `assert_released_for(identity)`, issuing a positive observation only
after original owner continuity and an actual successful owned descriptor close.
Existing `close() -> None` never stands in for that observation. D03 may associate
this same local observation with its own future root/attempt receipt; no second
release API or private fd access is authorized.

Future actual bound-write UoW adoption/permit LA/LR/commit guard belongs to D03/D06,
NOT_IMPLEMENTED in this PR. A fresh observation marker or same-looking DB values
cannot substitute for actual same-connection handoff. D03 design may reference the
public identities and the retained pin, but must independently specify and later
implement the module-owned adoption path; it cannot read private proof/Conn/fd.
No new genuine ConsumerCapability, registry, Application wiring or activation.

## 5. Acceptance matrix and limits

| Group | Required actual evidence |
|---|---|
| JSON/security | Frozen19 vectors retained by semantics; required/unknown fields, uint/bool, UTC/expiry, duplicate/nonfinite/UTF8/depth/size; DBowner/OID/signature/support/security/config/completeACL/order/duplicates/excess deny |
| Installation | Cold protected temp installation of fixed real evaluate; public consume once, retained identity/expiry; fake/partial/deleted slots/copy/fork/replaced callable/record/origin/import-root deny |
| CAS/lease | Real private temp CAS/lease, path/device/inode/UID/mode/namespace and same owner; symlink/hardlink/replacement/unsupported topology/contended lease/lost continuity deny; no fake release from old close(None) |
| Real PG18 writer | Actual pinned facility receipt/DBfive/head/role/security/helper/completeACL, one RR RO snapshot/one backend PID, no scientific DML/CREATE/TEMP; before/after observer side-effect evidence |
| Wrong binding | Changed expected DB/owner/system/head/role/helperOID/def/security/ACL/CAS/lease with genuine witness creates no usable factory/proof; source facts never spoofed as live positive |
| Factory/pin | Caller URL/ambient PGHOSTADDR, false verification mark, second wrapper with copied IDs, fake observation/constructor, reconnect/pool replacement, session overlap/thread/fork/expiry deny |
| Failure cleanup | Fault each consume/acquire/connect/observe/compare/end/issue/close phase; all owned resources accounted, no returned live proof; unknown classified, no registration/DB-outcome claim |
| Compatibility | Original ordinary factories/HG1/Alembic config/timeouts/deferred error policies remain; only sole creator constructs engines; all old scientific guards/helperfalse/source hashes preserved |
| Architecture | Alias/create_async_engine/engine_from_config/direct psycopg/dynamic construction negatives; no foundation reverse/framework imports, no module activation or raw DB values through neutral port |

No actual negative DB attack mutates the approved development DB: change expected
record/test input or isolate pure comparisons. Actual stored roles/helper/schema
are read-only. No admin impersonation, schema/ACL patch or helper enablement.
Missing local facility configuration in GitHub cannot silently use its admin fixture:
new local-dev-only integration tests explicitly SKIP with reason, not PASS. Local
real PG evidence is separately mandatory and repeated independently on the authorized
writer; remote seven-CI still runs every existing test/benchmark/check unchanged.
No existing tests are deleted/deselected by source or workflow change.

Use this worktree's own `uv sync --frozen` environment with the already available
absolute Python3.12.15. Run focused new+existing installation/lease/ordinary factory/
architecture/typing, then appropriate pure regression. PG-heavy tests coordinate
one slot and only writer receipt. Preserve all failed attempts and exact head/base,
source hashes/queries/receipt provenance; no claimed full-suite PASS from missing
PG configuration. Independent exact-head source review, normal seven CI and HIGH
owner merge label remain. Stacked docs base is not permission to merge/deploy.

Completion can cover this bounded development implementation only. It does not
mean full D02 reference binding/installation/registration or D03/D06/production work
has passed. No whole-BACKLOG completion receipt or runtime activation is emitted.
