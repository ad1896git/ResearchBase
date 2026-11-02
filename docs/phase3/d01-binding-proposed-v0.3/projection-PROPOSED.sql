-- PROPOSED read-only projection text for D01 technical review. NOT EXECUTED.
-- Not a migration, not an operator script, no grant/DDL/activation authority.
-- A future fixed persistence adapter opens one bounded REPEATABLE READ READ ONLY
-- transaction; connection/role/permissions are operator provisioned, not supplied
-- by a scientific command. Runtime actual catalog/type inventory must match.

-- Fixed identity inputs. Roles are bound by OID and name, never caller-selected.
SELECT (pg_catalog.pg_control_system()).system_identifier,
       current_setting('server_version_num'),
       pg_catalog.inet_server_addr(), pg_catalog.inet_server_port(),
       current_database(), d.oid AS database_oid, d.datdba AS database_owner_oid,
       session_user, current_user
FROM pg_catalog.pg_database AS d
WHERE d.datname = current_database();
-- Same snapshot: SELECT version_num FROM public.alembic_version;
-- Require exactly one row/revision. No guessed head or repair.

-- Exactly one selected helper with fully qualified zero-argument signature.
SELECT p.oid, p.proname, p.pronamespace, p.proowner, p.prolang,
       pg_catalog.encode(pg_catalog.float4send(p.procost), 'hex') AS procost_bits,
       pg_catalog.encode(pg_catalog.float4send(p.prorows), 'hex') AS prorows_bits,
       p.provariadic, p.prosupport::pg_catalog.oid AS prosupport_oid, p.prokind, p.prosecdef, p.proleakproof,
       p.proisstrict, p.proretset, p.provolatile, p.proparallel, p.pronargs,
       p.pronargdefaults, p.prorettype, p.proargtypes::oid[], p.proallargtypes,
       p.proargmodes, p.proargnames, p.proargdefaults::text, p.protrftypes,
       p.prosrc, p.probin, p.prosqlbody::text, p.proconfig,
       CASE WHEN p.proacl IS NULL THEN 'NULL' ELSE 'ARRAY' END AS acl_kind,
       CASE WHEN p.proacl IS NULL THEN NULL ELSE
           ARRAY(SELECT item::text FROM unnest(p.proacl) WITH ORDINALITY AS a(item, ord)
                 ORDER BY ord) END AS acl_raw_items,
       n.nspname, l.lanname,
       pg_catalog.pg_get_function_identity_arguments(p.oid) AS identity_arguments,
       pg_catalog.pg_get_function_result(p.oid) AS result_signature,
       pg_catalog.pg_get_functiondef(p.oid) AS definition
FROM pg_catalog.pg_proc AS p
JOIN pg_catalog.pg_namespace AS n ON n.oid=p.pronamespace
JOIN pg_catalog.pg_language AS l ON l.oid=p.prolang
WHERE p.oid='public.pr316d1_enabled()'::regprocedure;

-- Independent typed rows for effective ACL; preserve NULL/raw status above.
SELECT x.grantor, x.grantee, x.privilege_type, x.is_grantable
FROM pg_catalog.pg_proc AS p,
LATERAL pg_catalog.aclexplode(
    COALESCE(p.proacl, pg_catalog.acldefault('f',p.proowner))) AS x
WHERE p.oid='public.pr316d1_enabled()'::regprocedure
ORDER BY x.grantor,x.grantee,x.privilege_type,x.is_grantable;

-- All membership edges of complete ancestry regardless of options.
-- The fixed adapter gets roots from actual authenticated session/current roles.
-- Returned graph must be complete; >256 edges/>128 role rows rejects rather
-- than truncates. The query is bounded by the future fixed read-only timeout.
WITH RECURSIVE ancestry(oid) AS (
    SELECT oid FROM pg_catalog.pg_roles WHERE rolname IN (session_user,current_user)
    UNION
    SELECT m.roleid FROM pg_catalog.pg_auth_members AS m
    JOIN ancestry AS a ON m.member=a.oid
)
SELECT m.roleid,m.member,m.grantor,m.admin_option,m.inherit_option,m.set_option
FROM pg_catalog.pg_auth_members AS m
JOIN ancestry AS a ON m.member=a.oid
ORDER BY m.roleid,m.member,m.grantor,m.admin_option,m.inherit_option,m.set_option;
-- Read role attributes for ALL ancestry IDs plus DB/function owner and every
-- returned grantor. Adapter uses typed array parameters, no interpolated names:
-- SELECT oid,rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,
--        rolreplication,rolbypassrls FROM pg_catalog.pg_roles
-- WHERE oid=ANY(:observed_required_role_oids) ORDER BY oid;
-- Missing IDs/unknown type inventory/permission/limits denies; not an auto-GRANT.
