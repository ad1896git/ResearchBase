"""Bounded PG18 metadata projection; no engine construction or authority issuance."""

from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.engine import Connection

from researchbase.foundation.bearing_binding_contracts import (
    BindingError,
    DatabaseIdentity,
    DatabaseObservation,
    ExecuteGrant,
    FunctionSecurity,
    FunctionSignature,
    HelperIdentity,
    RoleIdentity,
)

_IDENTITY = """
SELECT (SELECT system_identifier::pg_catalog.text FROM pg_catalog.pg_control_system()) AS system_id,
 d.datname AS name, d.oid AS oid, d.datdba AS owner_oid,
 pg_catalog.current_setting('server_version_num') AS version,
 sr.rolname AS session_name, sr.oid AS session_oid,
 cr.rolname AS current_name, cr.oid AS current_oid,
 pg_catalog.inet_server_addr()::pg_catalog.text AS address,
 pg_catalog.inet_server_port() AS port, pg_catalog.pg_backend_pid() AS backend_pid,
 (SELECT version_num FROM public.alembic_version) AS revision
FROM pg_catalog.pg_database d
JOIN pg_catalog.pg_roles sr ON sr.rolname = SESSION_USER
JOIN pg_catalog.pg_roles cr ON cr.rolname = CURRENT_USER
WHERE d.datname = pg_catalog.current_database()
"""
_HELPER = """
SELECT p.oid, p.proowner, pg_catalog.pg_get_functiondef(p.oid) AS definition,
 p.proargtypes::pg_catalog.oid[] AS args, p.provariadic, p.prorettype, p.proretset,
 p.prokind::pg_catalog.text AS kind, l.lanname AS language,
 p.provolatile::pg_catalog.text AS volatility, p.prosecdef, p.proleakproof,
 p.proisstrict, p.proparallel::pg_catalog.text AS parallel,
 p.prosupport::pg_catalog.oid AS support, p.proconfig,
 pg_catalog.has_function_privilege(SESSION_USER, p.oid, 'EXECUTE') AS session_execute,
 pg_catalog.has_function_privilege(CURRENT_USER, p.oid, 'EXECUTE') AS current_execute
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
JOIN pg_catalog.pg_language l ON l.oid = p.prolang
WHERE n.nspname = 'public' AND p.proname = 'pr316d1_enabled' AND p.pronargs = 0
 AND pg_catalog.octet_length(pg_catalog.pg_get_functiondef(p.oid)) <= 65536
 AND pg_catalog.cardinality(p.proconfig) <= 64
 AND NOT EXISTS (SELECT 1 FROM pg_catalog.unnest(p.proconfig) cfg(value)
                 WHERE pg_catalog.octet_length(cfg.value) > 4096)
"""
_ACL = """
SELECT a.grantee, a.grantor, a.privilege_type, a.is_grantable
FROM pg_catalog.pg_proc p
CROSS JOIN LATERAL pg_catalog.aclexplode(
 COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))) a
WHERE p.oid = CAST(:oid AS pg_catalog.oid)
ORDER BY a.grantee, a.grantor, a.privilege_type, a.is_grantable
LIMIT 65
"""
_ROLES = """
WITH reachable AS (
 SELECT r.oid FROM pg_catalog.pg_roles r
 WHERE r.rolname IN (SESSION_USER,CURRENT_USER)
 OR pg_catalog.pg_has_role(SESSION_USER,r.oid,'MEMBER')
 OR pg_catalog.pg_has_role(CURRENT_USER,r.oid,'MEMBER')
)
SELECT
 EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
   WHERE pg_catalog.pg_has_role(SESSION_USER,r.oid,'MEMBER')
     AND (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication))
 AS elevated_session,
 EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
   WHERE pg_catalog.pg_has_role(CURRENT_USER,r.oid,'MEMBER')
     AND (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication))
 AS elevated_current,
 pg_catalog.pg_has_role(SESSION_USER,CAST(:dbowner AS pg_catalog.oid),'MEMBER') OR
 pg_catalog.pg_has_role(CURRENT_USER,CAST(:dbowner AS pg_catalog.oid),'MEMBER') AS database_owner,
 pg_catalog.pg_has_role(SESSION_USER,CAST(:fnowner AS pg_catalog.oid),'MEMBER') OR
 pg_catalog.pg_has_role(CURRENT_USER,CAST(:fnowner AS pg_catalog.oid),'MEMBER') AS function_owner,
 EXISTS (SELECT 1 FROM pg_catalog.pg_shdepend own
 WHERE own.refclassid='pg_catalog.pg_authid'::pg_catalog.regclass AND own.deptype='o'
 AND own.dbid IN (0,CAST(:dboid AS pg_catalog.oid)) AND
 (pg_catalog.pg_has_role(SESSION_USER,own.refobjid,'MEMBER') OR
  pg_catalog.pg_has_role(CURRENT_USER,own.refobjid,'MEMBER'))) AS object_owner,
 EXISTS (SELECT 1 FROM reachable r
 WHERE pg_catalog.has_database_privilege(r.oid,CAST(:dboid AS pg_catalog.oid),'CREATE,TEMP'))
 AS database_ddl,
 EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n CROSS JOIN reachable r
 WHERE n.nspname NOT LIKE 'pg_temp_%' AND n.nspname NOT LIKE 'pg_toast_temp_%'
 AND pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE')) AS schema_ddl,
 EXISTS (SELECT 1 FROM pg_catalog.pg_class c
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace CROSS JOIN reachable r
 WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') AND
 pg_catalog.has_table_privilege(r.oid,c.oid,
 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')) AS scientific_dml
"""


def _int(value: object) -> int:
    if type(value) is not int or not 0 < value < 2**32:
        raise BindingError("unexpected native OID")
    return value


def observe_database(connection: Connection) -> DatabaseObservation:
    """Called within the issuer's single repeatable-read read-only transaction."""
    try:
        settings = connection.execute(
            text(
                "SELECT pg_catalog.current_setting('transaction_read_only'), "
                "pg_catalog.current_setting('transaction_isolation')"
            )
        ).one()
        if tuple(settings) != ("on", "repeatable read"):
            raise BindingError("unbounded observation transaction")
        d = connection.execute(text(_IDENTITY)).mappings().one()
        h = connection.execute(text(_HELPER)).mappings().one()
        acl_rows = connection.execute(text(_ACL), {"oid": _int(h["oid"])}).mappings().all()
        if len(acl_rows) > 64:
            raise BindingError("ACL observation budget exceeded")
        acl = tuple(
            ExecuteGrant(r["grantee"], r["grantor"], r["privilege_type"], r["is_grantable"])
            for r in acl_rows
        )
        if acl != tuple(sorted(set(acl))):
            raise BindingError("incomplete or duplicate ACL observation")
        violations = (
            connection.execute(
                text(_ROLES),
                {
                    "dbowner": _int(d["owner_oid"]),
                    "fnowner": _int(h["proowner"]),
                    "dboid": _int(d["oid"]),
                },
            )
            .mappings()
            .one()
        )
        if any(type(x) is not bool for x in violations.values()):
            raise BindingError("unknown role observation")
        return DatabaseObservation(
            DatabaseIdentity(
                d["system_id"],
                d["name"],
                _int(d["oid"]),
                _int(d["owner_oid"]),
                int(d["version"]) // 10000,
            ),
            d["revision"],
            RoleIdentity(d["session_name"], _int(d["session_oid"])),
            RoleIdentity(d["current_name"], _int(d["current_oid"])),
            HelperIdentity(
                "public.pr316d1_enabled()",
                _int(h["oid"]),
                hashlib.sha256(h["definition"].encode("utf-8")).hexdigest(),
                _int(h["proowner"]),
                FunctionSignature(
                    tuple(h["args"]), h["provariadic"], h["prorettype"], h["proretset"]
                ),
                FunctionSecurity(
                    h["kind"],
                    h["language"],
                    h["volatility"],
                    h["prosecdef"],
                    h["proleakproof"],
                    h["proisstrict"],
                    h["parallel"],
                    h["support"],
                    tuple(h["proconfig"] or ()),
                ),
                acl,
            ),
            d["address"],
            d["port"],
            (h["session_execute"], h["current_execute"]),
            tuple(key for key, value in violations.items() if value),
            _int(d["backend_pid"]),
        )
    except Exception as exc:
        raise BindingError("read-only database observation denied") from exc
