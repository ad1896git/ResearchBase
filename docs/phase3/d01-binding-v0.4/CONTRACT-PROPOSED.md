# D01 binding v0.4 — simplified closed proposal

PROPOSED. NOT FROZEN. Three explicit questions in CROSSWALK.md block the owner's
conditional automatic freeze. No D02 source, database, role, migration, provisioning,
registration or activation is authorized by this document. PR57/v0.3 stays draft,
unmerged and unchanged until root's later gate. Parent D01 HIGH, owner authority
and all original dependencies remain. This folder is a compact alternative, not
an amendment to authoritative architecture/D1 documents.

## 1. Scope and authority

The seven owner instructions (2026-11-02) select: four database identity values,
Alembic revision and owner-confirmed append-only rebind, direct conservative role
queries, helper definition hash/owner/security/effective EXECUTE, Unix-only,
standard sorted-key JSON+SHA256, one engine-creator module and preflight before
returning a session factory. They do not remove actual D1 installation, protected
operator approval, fixed loaded-code closure, DB–CAS–root binding, continuous
lease, per-transaction check, actual commit/revoke coordination, current entitlement,
original receipt/UNKNOWN/full reservation, reference/production separation or gates.

Read AGENTS → architecture01 →02 →03 →08 →Phase3 →Harness09 →ADR0027 and D1
amendment O01/O03/O09 →this proposal. The full production amendment remains
PROPOSED; the separately accepted limited reference policy is not production GO.
Current Phase3 uses PostgreSQL18. A new approval alone cannot authorize PG19 or
an incompatible schema. Missing actual evidence blocks registration/activation;
BEFORE_CODING prerequisites are a separate unresolved gate, not satisfied here.

## 2. Record and byte contract

One protected local operator approval record per original root. It is neither a
canonical scientific entity nor a signed JSON truth service. SHA256 detects content
identity; it does not identify an approver, grant entitlement or authenticate a
caller. Protected OS ownership, independent owner confirmation and actual deployment
control remain the authorization source. No boolean or caller-selected path/digest
can issue approval. No second canonical DB schema, registry or signing framework.

Record is UTF8 standard JSON, one object with the exact required fields below.
No duplicate keys, unknown fields, missing fields, nonfinite/float values, malformed
UTF8/BOM, trailing JSON, invalid field types or unbounded parsing. Integers exclude
bool; all strings are valid UTF8 without Cc/surrogates. Strings are not silently
normalized. Keys are fixed ASCII. Whitespace, key order and JSON escape spelling
are ordinary JSON representations, not a new byte grammar: parse then serialize
with `json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
allow_nan=False).encode('utf-8')`, no LF. SHA256 over those bytes, lowercase64hex.
There is no binary prefix. Different Unicode codepoints remain different values;
JSON-equivalent whitespace/key ordering has the same digest.

Record<=32768 input bytes, structural depth<=8, integer tokens<=20 digits (minus
excluded); reject parse UnicodeError/ValueError/RecursionError rather than raising
limits or trying another decoder. General nonempty text<=4096 UTF8bytes; role/DB
names<=63; IDs/namespace/root/revision<=128. Local absolute paths are bounded4096,
no dot/dotdot, NUL/control, duplicate separators or symlink normalization. Actual
filesystem canonicality/owner/mode/inode is later observed, not proven by parsing.
Times are ISO8601 with T separator and explicit UTC Z/+00:00; preserve original
string, require approved_at<expires_at. Expiry denies at equality. Offline parse
success is not current, protected, observed or approved.

| Required path | Exact type / meaning |
|---|---|
| kind; schema_version | `ResearchBase.D01.BindingApproval`; exact int4 |
| approval_id; sequence | nonempty local approval label<=128; exact int1..2147483647, not scientific ID |
| previous_approval_sha256 | null iff sequence1; otherwise64lowerhex |
| approved_at; expires_at | UTC times above; runtime also checks original authorization lifetime |
| confirmation | object exactly event, decision_sha256, diff_sha256; event INITIAL iff sequence1, otherwise PG_UPGRADE/MIGRATION/ROLE_CHANGE/DEPLOYMENT_CHANGE; both hashes64lowerhex, referencing independently protected human decision and exact displayed diff, not self-approval |
| deployment | exactly id, host, uid, namespace, root_id, installation_manifest_sha256, artifact_sha256, callable_module, callable_qualname, callable_code_sha256; uid uint64; hashes64lowerhex; fixed callable `researchbase.agent_runtime.domain.bearing_evaluation.evaluate`; original actual inventory/source proof retained |
| database | exactly system_identifier canonical decimal text1..2^64-1, name, oid1..2^32-1, pg_major exact18; **no minor version or stored DB-owner identity** under this candidate |
| alembic_revision | exact unique approved head text<=128, not latest/current/main/head aliases; no automatic migration |
| roles | exactly session and current, each {name,oid}, plus policy literal `restricted-writer-v4`; no encoded membership graph; actual identity must match and direct query predicates below must hold |
| helper | exactly name=`public.pr316d1_enabled()`, definition_sha256, owner_oid, security_definer=false, leakproof=false, effective_execute={session:true,current:true}; hashes match exact UTF8 pg_get_functiondef output, no SQL normalization; **no OID/raw ACL/35-field catalog record** |
| connection | exactly transport=`UNIX`, socket_directory absolute local path, port exact int1..65535; operator fills actual values; inet_server_addr()/port must both be SQLNULL, never a TCP fallback |
| cas | exactly path, namespace, device, inode, uid, mode; uint64 identities, namespace equals deployment.namespace, uid equals deployment.uid, mode exact0700 |
| lease | exactly path, device, inode, uid, mode; uint64 identities, uid equals deployment.uid, mode exact0600; no release/reacquire during lifetime |

The helper/DB-owner omissions above are intentional representations of the requested
simplification, **not declared compatible with current O09 fixed checks**. See
CROSSWALK.md. D02 cannot drop original requirements just because this parser can
read the smaller record. No opaque v0.3 class hierarchy/full graph/35-position
serialization is required merely because it appeared in that earlier proposal.

## 3. Fixed observation and conservative role queries

All database observation uses one persistence-owned read-only snapshot with fixed
fully qualified queries, never caller SQL/URL or raw DB objects in foundation.
Obtain pg_control_system().system_identifier, current_database()/pg_database.oid,
server_version_num integer divided by10000, unique Alembic head, actual session_user
and current_user OID/name, actual DB/function owners, helper definition, flags and
effective EXECUTE. Server minor is not a binding value; actual PG/config still
belongs in O03 calibration evidence. An unannounced minor upgrade may leave this
record unchanged: maintenance revoke/rebind is a procedural requirement, not an
automatic fingerprint guarantee.

For both session and current roles, reject equality or **direct/indirect MEMBER**
in DB-owner or function-owner roles, regardless INHERIT/SET option. Use actual
queried owner OIDs, not caller-provided OIDs. Directly query forbidden role attributes
superuser/BYPASSRLS/CREATEROLE, retaining D1 NOCREATEDB/NOREPLICATION. Conservatively
reject reachable roles with those attributes as well; this uses server-side
pg_has_role(...,'MEMBER') predicates and need not serialize the graph. Missing
rows/privilege, ambiguous identity or unbounded/timeout observation denies.

No DDL, owner SET ROLE or helper replacement authority for ordinary writer. Audit
actual schema/object ownership and effective CREATE/TEMP/other privileges under
approved scope; NOINHERIT does not remove PUBLIC privileges. If an effective
privilege exceeds approved scope, HOLD for DBA/owner review: never silently revoke
PUBLIC or grant a broad role. Default helper PUBLIC+owner EXECUTE remains unchanged;
effective EXECUTE is expected **true**, not a reason to revoke existing grants.
Raw ACL/all-attribute preservation remains mandatory where current D1 requires it;
replacing that requirement is the explicit unresolved helper decision.

## 4. Rebind command design (not an existing executable)

Proposed operator-only `binding-rebind prepare` reads the original protected record
and fixed new observation, prints a sorted path-by-path old/new **binding** diff and
reason, and writes only an UNAPPROVED candidate. No trusted boolean/`--yes`/agent
self-confirmation. Major upgrade, migration, relevant role/owner/permission changes
and deployment changes require rebind; PG-minor maintenance requires an explicit
PG_UPGRADE event even if all compared fields/diff are unchanged. Do not claim an
unrecorded harmless role-graph/minor change can be detected from these predicates.

A distinct protected finalize step requires the actual owner's explicit confirmation
of original SHA, candidate canonical SHA and diff SHA in independently retained
decision evidence. Operator cannot manufacture that decision. Under the original
namespace's exclusive owner protocol, recheck expected previous SHA/sequence and
all observations, then append a **new**0600 approval file with exclusive-create,
full write/fsync and directory fsync; parent0700. Never overwrite old approval,
replace history, or let a partial file become a valid record. Repeated finalize
returns the exact original append if already durably recorded; conflicting or
incomplete outcome HOLDs. SHA chain/sequence is consistency, not a signature.

Finalize is not activate/register/migrate/grant/restart. Before any bound identity
changes, old root must revoke and drain under D03, preserving original receipts and
unknown outcomes. Unknown old work/cleanup blocks a new live root, even if namespace
or approval changed. Startup selects one explicitly approved record through protected
composition, never “latest” by caller. Installation/source/lease proof and all
preflight facts must be fresh. A new approval cannot legalize forbidden roles,
helper mutation or bypass any separately required migration/activation/profile gate.
No actual command, approval decision or role setup has been executed here.

## 5. One engine creator, actual connection and lifetime

Proposed sole construction module is existing
`src/researchbase/persistence/database.py`. Future exact source pack must route all
first-party engine/driver construction through it, including current direct
create_engine in `persistence/uow.py:1416` and engine_from_config in
`migrations/env.py`. No hidden alias/dynamic-import/psycopg.connect escape or broad
allowlist. Preserve normal owning semantics and migration/test authorization; no
other root receives genuine D1 capability from centralization. Exact integration
scope and backward-compatibility must be reviewed before source changes.

The protected D1 entrypoint may privately create the fixed Unix connection for
observation; it returns a bound session factory only after actual installation,
record, role, DB/CAS/lease/helper preflight succeeds. No factory is returned after
failure. Plain imported factories, a matching digest, lint success or mocked
preflight result are not an issuer. No private installation-proof slot inspection.
Foundation uses neutral public witness/typed non-I/O verification seam; persistence
owns DB observations and actual captured connection/engine. Application receives
no filesystem/SQLAlchemy/driver objects.

**Startup checking is not enough.** Before each actual transaction, retain D1
filesystem/source/lease checks and same approved DB binding; actual connection
used by the UoW must be the one proved under the D02/D03 contract, including pool
reconnect/replacement denial. No pool-return gap between per-attempt observation and
bound UoW. Same owner-resource thread, continuous lease and C/commit-revoke guard
remain through actual commit/rollback and cleanup; foreign requester is latch-only.
Lost commit acknowledgement remains UNKNOWN, current-entitled original receipt
reconciliation first, no new identity/refund/evaluation. Checked release and unknown
cleanup remain D03's explicit gate; current close(None) is not proof. Static import
rules supplement, never replace actual captured-factory/connection/lifetime evidence.

Planned regression obligations: sole creator AST/import-alias/direct-driver/dynamic
negative probes; unapproved factory never returned; wrong DB/head/role/helper/Unix
endpoint denied; PUBLIC effective privileges and indirect owner membership tested;
real same-connection/reconnect/commit/rollback-cleanup/fork/expiry/replay boundaries.
No product tests or PG were run by this docs task. Small offline vectors establish
only JSON/shape/hash behavior, not any runtime binding or authority.

## 6. Freeze state

HOLD. Decide helper-catalog scope, four-DB-field scope and D02 stage/provision
prerequisites at09:00. Current D1 requirements remain in force until an explicit
accepted change/compatible interpretation is recorded and independently reviewed.
Do not auto-freeze, close57, start D02 source or claim D03 integrated acceptance.
The proposal can still simplify JSON/transport/version/role-query design without
pretending the three outstanding questions are solved.

Primary PostgreSQL18 references (technical interpretation only):
[privilege/function information](https://www.postgresql.org/docs/18/functions-info.html),
[role creation](https://www.postgresql.org/docs/18/sql-createrole.html),
[Unix connection parameters](https://www.postgresql.org/docs/18/libpq-connect.html).
