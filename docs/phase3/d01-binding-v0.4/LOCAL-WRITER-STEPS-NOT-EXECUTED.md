# Local restricted writer steps — DOCUMENT ONLY, NOT EXECUTED

PROPOSED. These commands are an owner/DBA checklist, not authorization to run them.
No SQL, connection, role, pg_hba, secret or facility was touched for this proposal.
Do not use the repository demo TCP/admin defaults. The local client path below was
verified as a file by root; that says nothing about an actual server/version/socket.
No actual `.env`, credential file or password is read or embedded here.

## 1. Owner supplies actual local facts and approves scope

Fill the **actual approved isolated** Unix socket directory, port, DBA login and
existing target DB from owner/DBA metadata. Do not guess `/tmp`, Homebrew defaults,
admin role or `researchbase` DB. Exact system_identifier/DBOID/PG18/unique Alembic,
helper owner/catalog and DB–CAS scope must be independently reviewed. No reference
facts are borrowed from tests; don't point these steps at production.

Choose a new dedicated lowercase role name, not an existing admin/owner. If role
exists, STOP: no automatic ALTER/reuse/reset. Local peer/authentication mapping must
be independently configured by DBA; these steps do not loosen `pg_hba.conf`, set
trust, copy a password or prompt for a credential. If authentication fails, STOP.

Proposed manual Bash session, to be typed only after that approval:

```bash
D01_PSQL=/opt/homebrew/opt/postgresql@18/bin/psql
read -r -p 'Approved absolute Unix socket directory: ' D01_SOCKET_DIRECTORY
read -r -p 'Approved socket port: ' D01_SOCKET_PORT
read -r -p 'Approved DBA login role: ' D01_DBA_ROLE
read -r -p 'Approved existing isolated database: ' D01_DATABASE_NAME
read -r -p 'New dedicated writer role (lowercase identifier): ' D01_WRITER_ROLE
[[ "$D01_SOCKET_DIRECTORY" == /* && -d "$D01_SOCKET_DIRECTORY" ]] || exit 1
[[ "$D01_SOCKET_DIRECTORY" != *,* ]] || exit 1  # No libpq multi-host list.
[[ "$D01_SOCKET_PORT" =~ ^[0-9]{1,5}$ ]] || exit 1
(( 10#$D01_SOCKET_PORT >= 1 && 10#$D01_SOCKET_PORT <= 65535 )) || exit 1
[[ "$D01_WRITER_ROLE" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || exit 1
[[ "$D01_DBA_ROLE" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]] || exit 1
[[ "$D01_DATABASE_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]] || exit 1
# Explicit socket parameters; strip inherited connection shortcuts/credentials.
env -u PGHOST -u PGHOSTADDR -u PGPORT -u PGDATABASE -u PGUSER \
    -u PGSERVICE -u PGSERVICEFILE -u PGPASSWORD -u PGPASSFILE -u PGOPTIONS \
    PGPASSFILE=/dev/null PGSERVICEFILE=/dev/null \
    "$D01_PSQL" -X -w -h "$D01_SOCKET_DIRECTORY" -p "$D01_SOCKET_PORT" \
    -U "$D01_DBA_ROLE" -d "$D01_DATABASE_NAME" \
    -v ON_ERROR_STOP=1 -v writer="$D01_WRITER_ROLE" <<'SQL'
-- Observe and compare to independently approved facts BEFORE role creation.
SELECT pg_catalog.current_database(),
       (SELECT oid FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()),
       (SELECT system_identifier FROM pg_catalog.pg_control_system()),
       pg_catalog.current_setting('server_version_num'),
       pg_catalog.inet_server_addr(), pg_catalog.inet_server_port();
-- STOP here unless actual target facts were independently matched. Execute the
-- following CREATE in a separate owner-approved invocation, not blindly after print.
SQL
```

The guarded manual steps support only plain approved role/database identifiers.
A `-d` conninfo string or URI can override other libpq connection arguments;
therefore reject `host=... dbname=...`, `postgresql://...`, spaces, separators or
other unsupported names, never reinterpret them or relax the guard. Complex valid
PostgreSQL names require a separately reviewed explicit-parameter procedure. A
comma-separated host list is also rejected. These restrictions do not assert the
actual local DB name has already been supplied.

Printing these facts is not a comparison or grant. Do not append CREATE to this
observation heredoc and pretend human review happened. In a **separate invocation**
with the same explicit approved socket/DB arguments and `-v writer=...`, after
actual owner/DBA target confirmation, use exactly:

```sql
BEGIN;
CREATE ROLE :"writer" LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE
  NOCREATEDB NOREPLICATION NOINHERIT;
-- No owner membership, IN ROLE, ADMIN option, password, DDL, project-table DML,
-- broad function permission or scientific activation grant is issued here.
COMMIT;
```

Role is cluster-level, not confined by connecting to one DB. This creates only a
restricted candidate identity; it is not yet an accepted scientific writer. DBA
must check all effective access and reviewed authentication. Do not infer isolation
from role name, flags or absence of explicit grants.

## 2. Minimum observation privileges, individually reviewed

DBA may need a separately approved `CONNECT` on this one database and `USAGE` on
this schema, and specific read access for D02. Determine actual existing privilege
first. If needed and expressly approved, pass `-v db="$D01_DATABASE_NAME"` and use
`GRANT CONNECT ON DATABASE :"db" TO :"writer";` (one DB only). A specific
`GRANT USAGE ON SCHEMA public TO :"writer";` does not grant schema CREATE/DML.
Neither is automatically necessary if PUBLIC already supplies it; don't create
redundant grants by script. No blanket `pg_monitor` or read-all role.

For the fixed read-only control-data builtin, DBA checks:

```sql
SELECT pg_catalog.has_function_privilege(:'writer',
         'pg_catalog.pg_control_system()', 'EXECUTE');
-- ONLY if false and a separate DBA/owner decision explicitly approves it:
-- GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO :"writer";
```

**Never grant/revoke/alter** `public.pr316d1_enabled()` or other frozen helpers in
these steps. Original PUBLIC EXECUTE and owner EXECUTE are expected and retained,
including nongrantable PUBLIC; NOINHERIT does not remove PUBLIC. No EXECUTE ON ALL
FUNCTIONS, GRANT ALL, new helper, new owner or global default-privilege change.
If current defaults conflict with allowed scope, HOLD instead of silently REVOKE
PUBLIC across the database. Builtin minimum-read grant is a separate DBA provision
choice, not role-creation or reference-activation authority.

## 3. Audit current effective privileges; failures HOLD

Using the same explicit approved DBA observation connection, fixed data queries
can inspect the proposed role (`:'writer'` is a quoted data value, not raw SQL):

```sql
WITH who AS (SELECT oid FROM pg_catalog.pg_roles WHERE rolname=:'writer'),
     db AS (SELECT datdba FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()),
     fn AS (SELECT proowner FROM pg_catalog.pg_proc
            WHERE oid='public.pr316d1_enabled()'::pg_catalog.regprocedure)
SELECT r.oid,r.rolname,r.rolsuper,r.rolbypassrls,r.rolcreaterole,
       r.rolcreatedb,r.rolreplication,
       (r.oid=db.datdba OR pg_catalog.pg_has_role(r.oid,db.datdba,'MEMBER')) AS db_owner_member,
       (r.oid=fn.proowner OR pg_catalog.pg_has_role(r.oid,fn.proowner,'MEMBER')) AS function_owner_member
FROM who JOIN pg_catalog.pg_roles r ON r.oid=who.oid CROSS JOIN db CROSS JOIN fn;
-- This is a predicate query, not an encoded membership graph.
WITH who AS (SELECT oid FROM pg_catalog.pg_roles WHERE rolname=:'writer')
SELECT (SELECT count(*) FROM who)=1 AS writer_resolved, EXISTS (
  SELECT 1 FROM pg_catalog.pg_roles ancestor CROSS JOIN who
  WHERE (ancestor.oid=who.oid OR pg_catalog.pg_has_role(who.oid,ancestor.oid,'MEMBER'))
    AND (ancestor.rolsuper OR ancestor.rolbypassrls OR ancestor.rolcreaterole
         OR ancestor.rolcreatedb OR ancestor.rolreplication)
) AS reachable_forbidden_role;
SELECT pg_catalog.has_database_privilege(:'writer',pg_catalog.current_database(),'CREATE') AS db_create,
       pg_catalog.has_database_privilege(:'writer',pg_catalog.current_database(),'TEMP') AS db_temp;
SELECT n.nspname,pg_catalog.has_schema_privilege(:'writer',n.oid,'CREATE') AS schema_create
FROM pg_catalog.pg_namespace n WHERE n.nspname NOT LIKE 'pg_%'
 AND n.nspname<>'information_schema';
SELECT pg_catalog.has_function_privilege(:'writer',
         'public.pr316d1_enabled()', 'EXECUTE') AS effective_helper_execute;
```

No row/missing function/permission/ambiguous result denies, not NULL-as-safe.
The first seven risk booleans and reachable_forbidden_role must be false;
writer_resolved must be true; helper EXECUTE is expected true.
Also inspect reachable elevated roles and effective object ownership/DDL rights;
ordinary flags alone do not prove no DDL or owner SET. PUBLIC schema CREATE/TEMP
and any unsupported access require explicit owner/DBA scope resolution, not a
silent default-ACL rewrite. Reconnect as the actual writer only via the approved
Unix authentication and repeat current/session identity and fixed read-only
preflight; DBA's successful observation is not writer access proof.

**Scientific DML allowlist remains EMPTY/HOLD here.** Exact approved tables,
commands, guards, RLS, identity/composition and current entitlement must be reviewed
before any targeted future grant. No project tables/grants are invented to make
D02 seem implemented. Role creation/readability is not an installation witness,
consumer capability, D02 proof, registration or reference/production activation.
After any separately authorized PG/migration/role change, use owner-confirmed
append-only rebind and all existing gates; no approval file or role was created now.

References: [PostgreSQL18 CREATE ROLE](https://www.postgresql.org/docs/18/sql-createrole.html),
[privilege inquiry](https://www.postgresql.org/docs/18/functions-info.html),
[Unix connection control](https://www.postgresql.org/docs/18/libpq-connect.html).
