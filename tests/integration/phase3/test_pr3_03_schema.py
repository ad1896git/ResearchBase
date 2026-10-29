"""Frozen pack relational inventory and SQL/Python canonical material parity."""

import json
import re
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from tests.unit.phase3.test_capability_gateway_contracts import FIXED

from researchbase.foundation.canonical_json import canonical_json_bytes

PACK = Path("docs/phase3/PR3-03-contract-freeze.md")
TABLES = (
    "agent_tool_policies",
    "agent_tool_policy_permissions",
    "capability_invocations",
    "capability_invocation_refs",
    "capability_invocation_events",
)
COLUMNS_SQL = """
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name=:table ORDER BY ordinal_position
"""
CONSTRAINTS_SQL = """
SELECT conname, contype, confdeltype, condeferrable, condeferred,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint WHERE conrelid=CAST(:table AS regclass)
"""
INDEXES_SQL = """
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND indexname LIKE 'pr303_%'
"""


def test_every_frozen_column_constraint_index_and_fk(planning):
    pack = PACK.read_text().split("## 4.", 1)[0]
    type_names = {
        "uuid": "uuid",
        "text": "text",
        "integer": "integer",
        "timestamptz": "timestamp with time zone",
    }
    with planning.engine.connect() as conn:
        inspector = inspect(conn)
        for table in TABLES:
            ddl = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", pack, re.S)
            assert ddl is not None
            body = ddl.group(1)
            columns = re.findall(
                r"^  (\w+) (uuid|text|integer|timestamptz) (NOT NULL|NULL)", body, re.M
            )
            actual = [tuple(r) for r in conn.execute(text(COLUMNS_SQL), {"table": table})]
            assert actual == [
                (n, type_names[t], "NO" if null == "NOT NULL" else "YES") for n, t, null in columns
            ]
            constraints = conn.execute(text(CONSTRAINTS_SQL), {"table": table}).all()
            assert sum(c.contype == "c" for c in constraints) == body.count("CHECK (")
            assert sum(c.contype == "f" for c in constraints) == body.count("REFERENCES ")
            assert all(c.confdeltype == "r" for c in constraints if c.contype == "f")
            expected_targets = re.findall(r"REFERENCES (\w+)\(([^)]+)\)", body)
            actual_targets = [
                (f["referred_table"], f["referred_columns"])
                for f in inspector.get_foreign_keys(table)
            ]
            assert sorted(
                (t, [v.strip() for v in cols.split(",")]) for t, cols in expected_targets
            ) == sorted(actual_targets)
            expected_keys = [
                ([column], target, [v.strip() for v in keys.split(",")])
                for column, target, keys in re.findall(
                    r"^  (\w+) uuid [^\n]*REFERENCES (\w+)\(([^)]+)\)", body, re.M
                )
            ]
            expected_keys += [
                (
                    [v.strip() for v in local.split(",")],
                    target,
                    [v.strip() for v in remote.split(",")],
                )
                for local, target, remote in re.findall(
                    r"FOREIGN KEY \(([^)]+)\)\s*REFERENCES (\w+)\(([^)]+)\)", body
                )
            ]
            assert sorted(expected_keys) == sorted(
                (fk["constrained_columns"], fk["referred_table"], fk["referred_columns"])
                for fk in inspector.get_foreign_keys(table)
            )
        indexes = {r.indexname: r.indexdef for r in conn.execute(text(INDEXES_SQL))}
        declared = re.findall(
            r"CREATE (?:UNIQUE )?INDEX (pr303_\w+) ON (\w+)\s*"
            r"\(([^)]+)\)([^;]*);",
            pack,
        )
        assert set(indexes) == {name for name, *_ in declared} | {
            "pr303_reservation_operation_key",
            "pr303_usage_reservation_key",
            "pr303_receipt_scope_key",
        }
        for name, table, columns, predicate in declared:
            actual = indexes[name]
            assert f"ON public.{table}" in actual
            assert f"({columns.replace(',', ', ')})" in actual
            assert ("UNIQUE INDEX" in actual) == (f"CREATE UNIQUE INDEX {name}" in pack)
            assert (" WHERE " in actual) == bool(predicate.strip())
        print("catalog columns/check-counts/FK-targets/indexes", len(declared))


def test_all_eleven_composite_fk_targets_have_unique_keys(planning):
    with planning.engine.connect() as conn:
        targets = conn.execute(
            text("""
            SELECT DISTINCT c.confrelid::regclass::text AS target, c.confkey
            FROM pg_constraint c WHERE c.contype='f' AND cardinality(c.confkey)>1
            AND (c.conrelid::regclass::text = ANY(:tables) OR c.conname LIKE 'pr303_%')
        """),
            {"tables": list(TABLES)},
        ).all()
        assert len(targets) == 11
        for target, keys in targets:
            unique = (
                conn.execute(
                    text("""
                SELECT conkey FROM pg_constraint WHERE conrelid=CAST(:table AS regclass)
                AND contype IN ('p','u')
            """),
                    {"table": target},
                )
                .scalars()
                .all()
            )
            assert list(keys) in [list(k) for k in unique], (target, keys, unique)


def test_no_json_semantic_columns_and_nullable_old_row_additions(planning):
    with planning.engine.connect() as conn:
        assert (
            conn.execute(
                text("""
            SELECT count(*) FROM information_schema.columns WHERE table_schema='public'
            AND table_name=ANY(:tables) AND data_type IN ('json','jsonb')
        """),
                {"tables": list(TABLES)},
            ).scalar_one()
            == 0
        )
        for table, count in (("research_task_command_receipts", 4), ("research_task_events", 3)):
            cols = [
                r
                for r in conn.execute(text(COLUMNS_SQL), {"table": table})
                if r.column_name.startswith("result_capability_")
                or r.column_name in ("result_tool_policy_id", "resulting_invocation_revision")
            ]
            assert len(cols) == count and all(r.is_nullable == "YES" for r in cols)


SERIALIZE_SQL = """
SELECT pr304_canonical_policy_json(CAST(:value AS jsonb)),
encode(sha256(convert_to(pr304_canonical_policy_json(CAST(:value AS jsonb)), 'UTF8')), 'hex')
"""


@pytest.mark.parametrize(
    "vector",
    range(6),
    ids=[
        "schema_vector",
        "empty_capability_set",
        "fake_capability_set",
        "empty_policy",
        "allow_and_deny_policy",
        "parameters_vector",
    ],
)
def test_six_sql_python_vectors(planning, vector):
    payload, digest = FIXED[vector]
    with planning.engine.connect() as conn:
        result = conn.execute(text(SERIALIZE_SQL), {"value": payload.decode()}).one()
    assert tuple(result) == (payload.decode(), digest)
    assert canonical_json_bytes(json.loads(payload)) == payload


def test_resource_strings_unicode_and_integer_only_sql_numbers(planning):
    value = {"pin": "café-研究@1.0.0", "gpu_hours": "0.000001", "token_cost": "0.100000"}
    with planning.engine.connect() as conn:
        result = conn.execute(text(SERIALIZE_SQL), {"value": json.dumps(value)}).one()
        assert result[0].encode() == canonical_json_bytes(value)
    for number in ("0.1", "1.0", "-0.5"):
        with planning.engine.connect() as conn, pytest.raises(DBAPIError) as error:
            conn.execute(text(SERIALIZE_SQL), {"value": number})
        assert cast(Any, error.value.orig).sqlstate == "23514"
        assert canonical_json_bytes(json.loads(number))  # Python supports finite fractions.


RECONSTRUCT_SQL = """
WITH p AS (
  SELECT * FROM agent_tool_policies WHERE id = :policy
), permission_rows AS (
  SELECT q.* FROM agent_tool_policy_permissions q JOIN p ON p.id = q.policy_id
), permission_set AS (
  SELECT coalesce(jsonb_agg(jsonb_build_object(
    'capability_id', capability_id, 'capability_version', capability_version,
    'operation', operation, 'adapter_id', adapter_id,
    'adapter_version', adapter_version, 'parameter_schema_hash', parameter_schema_hash,
    'effect', effect) ORDER BY capability_id COLLATE "C", capability_version COLLATE "C",
    operation COLLATE "C", adapter_id COLLATE "C", adapter_version COLLATE "C",
    parameter_schema_hash COLLATE "C", effect COLLATE "C"), '[]'::jsonb) AS value
  FROM permission_rows
), distinct_keys AS (
  SELECT DISTINCT capability_id, capability_version, operation, adapter_id,
    adapter_version, parameter_schema_hash FROM permission_rows
), capability_set AS (
  SELECT jsonb_build_object('type', 'CapabilitySet', 'material_version', 1,
    'entries', coalesce(jsonb_agg(jsonb_build_object(
      'capability_id', capability_id, 'capability_version', capability_version,
      'operation', operation, 'adapter_id', adapter_id,
      'adapter_version', adapter_version, 'parameter_schema_hash', parameter_schema_hash)
      ORDER BY capability_id COLLATE "C", capability_version COLLATE "C",
      operation COLLATE "C", adapter_id COLLATE "C", adapter_version COLLATE "C",
      parameter_schema_hash COLLATE "C"), '[]'::jsonb)) AS value
  FROM distinct_keys
), envelope AS (
  SELECT jsonb_build_object('type', 'AgentToolPolicy', 'material_version', 1,
    'content', jsonb_build_object(
      'project_id', p.project_id::text, 'version', p.version,
      'capability_set_hash', p.capability_set_hash, 'permissions', s.value,
      'max_tool_calls', p.max_tool_calls,
      'max_parallel_invocations', p.max_parallel_invocations,
      'filesystem_scope', p.filesystem_scope, 'network_scope', p.network_scope,
      'compute_scope', p.compute_scope, 'external_effect_scope', p.external_effect_scope,
      'registry_artifact_version_id', p.registry_artifact_version_id::text,
      'registry_content_hash', p.registry_content_hash)) AS value
  FROM p CROSS JOIN permission_set s
)
SELECT pr304_canonical_policy_json(e.value) AS policy_text,
  encode(sha256(convert_to(pr304_canonical_policy_json(e.value), 'UTF8')), 'hex')
    AS policy_digest,
  encode(sha256(convert_to(pr304_canonical_policy_json(c.value), 'UTF8')), 'hex')
    AS capability_set_digest
FROM envelope e CROSS JOIN capability_set c;
"""


def test_typed_row_reconstruction_matches_saved_policy(gateway):
    from tests.integration.phase3.gateway_fixtures import install

    g = gateway
    install(g)
    with g.engine.connect() as conn:
        row = conn.execute(text(RECONSTRUCT_SQL), {"policy": g.policy_id}).one()
    assert row.policy_text.encode() == canonical_json_bytes(g.spec.material(g.project))
    assert row.policy_digest == g.spec.digest(g.project)
    assert row.capability_set_digest == g.spec.capability_set_hash


CREATE_VECTOR_POLICY_SQL = """
CREATE TEMP TABLE vector_policy (LIKE public.agent_tool_policies) ON COMMIT DROP
"""
CREATE_VECTOR_PERMISSIONS_SQL = """
CREATE TEMP TABLE vector_permissions (LIKE public.agent_tool_policy_permissions) ON COMMIT DROP
"""
INSERT_VECTOR_POLICY_SQL = """
INSERT INTO vector_policy (
    id,project_id,registration_task_id,receipt_id,version,capability_set_hash,
    max_tool_calls,max_parallel_invocations,filesystem_scope,network_scope,compute_scope,
    external_effect_scope,registry_artifact_version_id,registry_content_hash,content_hash,
    hash_scheme,created_by,created_at
) VALUES (
    :id,:project_id,:id,:id,:version,:capability_set_hash,
    :max_tool_calls,:max_parallel_invocations,:filesystem_scope,:network_scope,:compute_scope,
    :external_effect_scope,:registry_artifact_version_id,:registry_content_hash,:digest,
    'sha256-cjson-v1',:id,clock_timestamp()
)
"""
INSERT_VECTOR_PERMISSION_SQL = """
INSERT INTO vector_permissions (
    id,policy_id,project_id,capability_id,capability_version,operation,adapter_id,adapter_version,
    parameter_schema_hash,effect
) VALUES (
    :id,:policy,:project,:capability_id,:capability_version,:operation,:adapter_id,:adapter_version,
    :parameter_schema_hash,:effect
)
"""


@pytest.mark.parametrize("vector", [3, 4], ids=["empty_policy", "allow_and_deny_policy"])
@pytest.mark.parametrize("reverse", [False, True], ids=["original", "reordered"])
def test_fixed_policy_vectors_from_typed_rows(planning, vector, reverse):
    from researchbase.foundation.ids import new_uuid7

    payload, digest = FIXED[vector]
    content = json.loads(payload)["content"]
    policy_id = new_uuid7()
    # Fixed §7.2 identities cannot be arbitrary new canonical owners. Session-local typed
    # tables carry only serializer inputs, using the real column types and NOT NULLs.
    # Canonical persisted-policy reconstruction is exercised separately above.
    with planning.engine.begin() as conn:
        conn.execute(text(CREATE_VECTOR_POLICY_SQL))
        conn.execute(text(CREATE_VECTOR_PERMISSIONS_SQL))
        conn.execute(text(INSERT_VECTOR_POLICY_SQL), dict(content, id=policy_id, digest=digest))
        permissions = content["permissions"]
        for permission in reversed(permissions) if reverse else permissions:
            conn.execute(
                text(INSERT_VECTOR_PERMISSION_SQL),
                dict(
                    permission,
                    id=new_uuid7(),
                    policy=policy_id,
                    project=content["project_id"],
                ),
            )
        sql = RECONSTRUCT_SQL.replace("agent_tool_policies", "pg_temp.vector_policy").replace(
            "agent_tool_policy_permissions", "pg_temp.vector_permissions"
        )
        result = conn.execute(text(sql), {"policy": policy_id}).one()
        assert result.policy_text == payload.decode()
        assert result.policy_digest == digest
        assert result.capability_set_digest == content["capability_set_hash"]
        print(
            "TYPED_VECTOR",
            vector,
            "reordered",
            reverse,
            result.policy_digest,
            result.capability_set_digest,
        )


class StorageProbeComplete(Exception):
    """Force rollback after testing the complete SQL protocol, including deferred checks."""


@pytest.mark.parametrize("size", [65536, 65537])
def test_parameter_sql_storage_bounds_distinct_from_closed_arguments(gateway, monkeypatch, size):
    from tests.integration.phase3.gateway_fixtures import install, request_command
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    install(g)
    identity, digest = g.retain(b"x" * size)
    before = _rows(g.engine)
    insert = SqlAlchemyGatewayRepository.insert
    force = SqlAlchemyGatewayRepository.force_constraints
    observed = []

    def raw_insert(repo, table, row):
        if table == "capability_invocations":
            row = dict(
                row,
                parameters_artifact_version_id=identity,
                parameters_content_hash=digest,
                parameters_byte_size=size,
            )
        return insert(repo, table, row)

    def checked(repo):
        force(repo)
        observed.append(size)
        raise StorageProbeComplete()

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "insert", raw_insert)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "force_constraints", checked)
    # Retained bytes intentionally are not closed fake arguments. Only the SQL storage
    # contract is under test; no successful Application admission is claimed.
    if size == 65536:
        with pytest.raises(StorageProbeComplete):
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
        assert observed == [size]
    else:
        with pytest.raises(ResearchBaseError) as error:
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
        assert error.value.code == ErrorCode.VALIDATION_ERROR and not observed
    assert _rows(g.engine) == before


@pytest.mark.parametrize("size", [8192, 8193])
def test_summary_sql_utf8_byte_bounds(gateway, monkeypatch, size):
    from tests.integration.phase3.gateway_fixtures import finish, request_invocation, start
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    request_invocation(g)
    start(g)
    before = _rows(g.engine)
    update = SqlAlchemyGatewayRepository.update_invocation
    force = SqlAlchemyGatewayRepository.force_constraints
    summary = "é" * 4096 + ("x" if size == 8193 else "")
    assert len(summary.encode()) == size
    observed = []

    def raw_update(repo, identity, expected_revision, values):
        return update(repo, identity, expected_revision, dict(values, result_summary=summary))

    def checked(repo):
        force(repo)
        observed.append(size)
        raise StorageProbeComplete()

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "update_invocation", raw_update)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "force_constraints", checked)
    if size == 8192:
        with pytest.raises(StorageProbeComplete):
            finish(g)
        assert observed == [size]
    else:
        with pytest.raises(ResearchBaseError) as error:
            finish(g)
        assert error.value.code == ErrorCode.VALIDATION_ERROR and not observed
    assert _rows(g.engine) == before


@pytest.mark.parametrize(
    "family",
    [
        "RESEARCH_QUESTION_VERSION",
        "HYPOTHESIS_VERSION",
        "CLAIM_VERSION",
        "SOURCE_VERSION",
        "ARTIFACT_VERSION",
        "MANUSCRIPT_VERSION",
    ],
)
def test_six_input_families_positive_xor_duplicate_scope_freeze_hash(gateway, monkeypatch, family):
    from dataclasses import replace

    from tests.integration.phase3.conftest import draft_inputs
    from tests.integration.phase3.gateway_fixtures import install, owning_inputs, request_command
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.agent_runtime.domain.capability_invocation import GatewayRef
    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
    from researchbase.persistence.research_task_queries import INPUT_FAMILIES

    g = gateway
    frozen = owning_inputs(g.p)
    drafts = cast(Any, draft_inputs).__wrapped__(g.p, frozen)
    other = g.identity.create_project_with_owner(
        g.owner, name="Foreign gateway pins", request_id=new_uuid7()
    )
    foreign = owning_inputs(replace(g.p, project=other))
    install(g)
    with g.factory() as uow:
        pin = uow.gateway.input_version(family, frozen[family], g.project)
    assert pin is not None
    scheme = pin.get("hash_scheme") if family in ("SOURCE_VERSION", "MANUSCRIPT_VERSION") else None
    ref = GatewayRef(family, frozen[family], pin["content_hash"], scheme)
    before = _rows(g.engine)
    original = SqlAlchemyGatewayRepository.insert
    column = INPUT_FAMILIES[family][0]
    for case in ("zero", "multiple", "duplicate", "scope", "freeze", "hash", "scheme"):

        def insert(repo, table, row, case=case):
            if table != "capability_invocation_refs":
                return original(repo, table, row)
            row = dict(row)
            if case == "zero":
                row[column] = None
            elif case == "multiple":
                alternate = "ARTIFACT_VERSION" if family != "ARTIFACT_VERSION" else "CLAIM_VERSION"
                row[INPUT_FAMILIES[alternate][0]] = frozen[alternate]
            elif case == "scope":
                row[column] = foreign[family]
            elif case == "freeze":
                row[column] = drafts[family]
            elif case == "hash":
                row["content_hash"] = "0" * 64
            elif case == "scheme":
                row["hash_scheme"] = None if scheme else "sha256-cjson-v1"
            original(repo, table, row)
            if case == "duplicate":
                original(repo, table, dict(row, id=new_uuid7()))

        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
            with pytest.raises(ResearchBaseError):
                g.gateway_service.request_capability_invocation(
                    g.owner, request_command(g, input_refs=(ref,)), g.context
                )
        assert _rows(g.engine) == before, (family, case)
    saved = g.gateway_service.request_capability_invocation(
        g.owner, request_command(g, input_refs=(ref,)), g.context
    )
    assert saved.invocation_id == g.args.invocation_id


EXPECTED_CHECK_TABLE_SQL = """
CREATE TEMP TABLE {name} ({body}) ON COMMIT DROP
"""
CHECK_DEFINITIONS_SQL = """
SELECT pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid=CAST(:table AS regclass) AND contype='c' ORDER BY pg_get_constraintdef(oid)
"""


def test_every_check_expression_matches_postgresql_parsed_frozen_ddl(planning):
    pack = PACK.read_text().split("## 3.", 1)[0]
    with planning.engine.begin() as conn:
        for table in TABLES:
            match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", pack, re.S)
            assert match is not None
            body = match.group(1)
            # Only transient expected CHECKs are parsed here. No canonical DDL or rows
            # change, no production trigger is disabled, and no FK privilege is needed.
            body = re.sub(
                r"FOREIGN KEY \([^)]*\)\s*REFERENCES \w+\([^)]*\)\s*"
                r"ON DELETE RESTRICT,?\s*",
                "",
                body,
            )
            body = re.sub(r" REFERENCES \w+\([^)]*\) ON DELETE RESTRICT", "", body)
            body = body.rstrip().rstrip(",")
            expected = "expected_" + table
            conn.execute(text(EXPECTED_CHECK_TABLE_SQL.format(name=expected, body=body)))
            actual_checks = (
                conn.execute(text(CHECK_DEFINITIONS_SQL), {"table": table}).scalars().all()
            )
            expected_checks = (
                conn.execute(text(CHECK_DEFINITIONS_SQL), {"table": "pg_temp." + expected})
                .scalars()
                .all()
            )
            assert actual_checks == expected_checks, table


@pytest.mark.parametrize("gateway", ["maximum"], indirect=True)
def test_256_257_permissions_and_total_refs_storage(gateway, monkeypatch):
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    from tests.integration.phase3.gateway_fixtures import install, request_command

    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7

    original_insert = SqlAlchemyGatewayRepository.insert
    extra_ref, extra_hash = g.retain(b"257th candidate ref")
    for operation, table in (
        ("register", "agent_tool_policy_permissions"),
        ("request", "capability_invocation_refs"),
    ):
        before = _rows(g.engine)
        seen = []

        def insert(repo, target, row, table=table, seen=seen):
            original_insert(repo, target, row)
            if target == table:
                seen.append(1)
                if len(seen) == 256:
                    extra: dict[str, Any] = dict(row, id=new_uuid7())
                    if table == "agent_tool_policy_permissions":
                        extra["capability_id"] = "capability257"
                    else:
                        extra.update(artifact_version_id=extra_ref, content_hash=extra_hash)
                    original_insert(repo, target, extra)

        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
            with pytest.raises(ResearchBaseError):
                if operation == "register":
                    install(g)
                else:
                    g.gateway_service.request_capability_invocation(
                        g.owner, request_command(g), g.context
                    )
        assert len(seen) == 256 and _rows(g.engine) == before
        if operation == "register":
            install(g)
        else:
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
    with g.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM agent_tool_policy_permissions")).scalar_one()
            == 256
        )
        assert (
            conn.execute(text("SELECT count(*) FROM capability_invocation_refs")).scalar_one()
            == 256
        )


TEMP_RECEIPT_CHECKS_SQL = """
CREATE TEMP TABLE expected_receipt_checks (LIKE public.research_task_command_receipts)
ON COMMIT DROP
"""
TEMP_EVENT_CHECKS_SQL = """
CREATE TEMP TABLE expected_event_checks (LIKE public.research_task_events) ON COMMIT DROP
"""
ADD_EXPECTED_CHECK_SQL = """
ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})
"""


def check_expression(source, start):
    """Extract one balanced SQL CHECK, retaining quoted parentheses literally."""
    depth, quoted, i = 1, False, start
    while depth:
        c = source[i]
        if c == "'":
            if quoted and source[i : i + 2] == "''":
                i += 2
                continue
            quoted = not quoted
        elif not quoted:
            depth += (c == "(") - (c == ")")
        i += 1
    return source[start : i - 1]


def test_receipt_and_task_event_full_check_and_fk_catalog(planning):
    section = PACK.read_text().split("## 3. Constrained", 1)[1].split("## 4.", 1)[0]
    search_ddl = Path("docs/phase3/design/PR3-16-ddl-guards-events.md").read_text()
    renamed = {
        "pr303_command_names": "pr316_command_names",
        "pr303_event_names": "pr316_task_event_names",
        "pr303_event_states": "pr316_task_event_states",
        "pr303_event_reason": "pr316_task_event_reason",
    }
    with planning.engine.begin() as conn:
        conn.execute(text(TEMP_RECEIPT_CHECKS_SQL))
        conn.execute(text(TEMP_EVENT_CHECKS_SQL))
        checked = []
        for match in re.finditer(r"ADD CONSTRAINT (pr303_\w+) CHECK \(", section):
            name = match.group(1)
            receipt = name in {"pr303_command_names", "pr303_receipt_shape"}
            table = "research_task_command_receipts" if receipt else "research_task_events"
            temporary = "expected_receipt_checks" if receipt else "expected_event_checks"
            live_name = renamed.get(name, name)
            if name in renamed:
                definitions = list(
                    re.finditer(r"ADD CONSTRAINT " + live_name + r" CHECK \(", search_ddl)
                )
                assert len(definitions) == 1
                expression = check_expression(search_ddl, definitions[0].end())
                assert (
                    conn.execute(
                        text(
                            "SELECT count(*) FROM pg_constraint "
                            "WHERE conrelid=CAST(:table AS regclass) AND conname=:name"
                        ),
                        {"table": table, "name": name},
                    ).scalar_one()
                    == 0
                )
            else:
                expression = check_expression(section, match.end())
            if name == "pr303_command_names":
                expression = (
                    f"({expression}) OR command_name IN "
                    "('admit_bearing_evaluation_v2','settle_bearing_evaluation_v2')"
                )
            elif name == "pr303_event_names":
                expression = (
                    f"({expression}) OR event_type IN "
                    "('BEARING_EVALUATION_ADMITTED','BEARING_EVALUATION_SETTLED')"
                )
            elif name == "pr303_event_states":
                expression = (
                    f"({expression}) OR (event_type='BEARING_EVALUATION_ADMITTED' "
                    "AND prior_status IN ('CREATED','PLANNING') AND new_status=prior_status) OR "
                    "(event_type='BEARING_EVALUATION_SETTLED' AND prior_status IN "
                    "('CREATED','PLANNING','CANCELLED') AND new_status=prior_status)"
                )
            elif name == "pr303_event_reason":
                expression = (
                    "(event_type NOT IN ('BEARING_EVALUATION_ADMITTED',"
                    f"'BEARING_EVALUATION_SETTLED') AND ({expression})) OR "
                    "(event_type IN ('BEARING_EVALUATION_ADMITTED',"
                    "'BEARING_EVALUATION_SETTLED') AND reason IS NOT NULL AND pr316_reason(reason))"
                )
            elif name == "pr303_event_stop_kind":
                expression = (
                    f"({expression}) OR event_type IN "
                    "('BEARING_EVALUATION_ADMITTED','BEARING_EVALUATION_SETTLED')"
                )
            conn.execute(
                text(
                    ADD_EXPECTED_CHECK_SQL.format(
                        table=temporary,
                        name=name,
                        expression=expression,
                    )
                )
            )
            actual = conn.execute(
                text("""
                SELECT pg_get_constraintdef(oid) FROM pg_constraint
                WHERE conrelid=CAST(:table AS regclass) AND conname=:name
            """),
                {"table": table, "name": live_name},
            ).scalar_one()
            expected = conn.execute(
                text("""
                SELECT pg_get_constraintdef(oid) FROM pg_constraint
                WHERE conrelid=CAST(:table AS regclass) AND conname=:name
            """),
                {"table": "pg_temp." + temporary, "name": name},
            ).scalar_one()
            assert actual == expected, name
            checked.append(name)
        assert set(checked) == {
            "pr303_command_names",
            "pr303_receipt_shape",
            "pr303_event_names",
            "pr303_event_states",
            "pr303_event_reason",
            "pr303_event_stop_kind",
            "pr303_task_event_shape",
        }
        inspector = inspect(conn)
        for table, marker, end in (
            ("research_task_command_receipts", "## 3.", "ALTER TABLE research_task_events"),
            ("research_task_events", "ALTER TABLE research_task_events", "## 4."),
        ):
            whole = PACK.read_text()
            ddl = whole.split(marker, 1)[1].split(end, 1)[0]
            expected = re.findall(
                r"ADD CONSTRAINT (pr303_\w+) FOREIGN KEY \(([^)]+)\)\s*"
                r"REFERENCES (\w+)\(([^)]+)\)\s*ON DELETE RESTRICT"
                r"( DEFERRABLE INITIALLY DEFERRED)?",
                ddl,
            )
            actual = {
                fk["name"]: fk
                for fk in inspector.get_foreign_keys(table)
                if fk["name"].startswith("pr303_")
            }
            assert len(actual) == len(expected) == 3
            for name, local, target, remote, deferred in expected:
                fk = actual[name]
                assert fk["constrained_columns"] == [c.strip() for c in local.split(",")]
                assert fk["referred_table"] == target
                assert fk["referred_columns"] == [c.strip() for c in remote.split(",")]
                assert fk["options"]["ondelete"] == "RESTRICT"
                assert bool(fk["options"].get("deferrable")) == bool(deferred)
                if deferred:
                    assert fk["options"]["initially"] == "DEFERRED"
        assert (
            conn.execute(
                text("""
            SELECT count(*) FROM pg_constraint WHERE conname=ANY(:old)
            AND conrelid IN ('research_task_command_receipts'::regclass,
                            'research_task_events'::regclass)
        """),
                {
                    "old": [
                        "pr304_command_names",
                        "pr304_event_names",
                        "pr304_event_states",
                        "pr304_event_reason",
                        "pr304_event_stop_kind",
                    ]
                },
            ).scalar_one()
            == 0
        )


def test_all_composite_local_scope_mismatch_writes(gateway, monkeypatch):
    from dataclasses import replace

    from tests.integration.phase3.gateway_fixtures import (
        finish,
        request_command,
        request_invocation,
        start,
    )
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    request_invocation(g)
    start(g)
    finish(g)
    foreign_task = g.p.create()
    foreign_project = g.identity.create_project_with_owner(
        g.owner,
        name="Composite mismatch scope",
        request_id=new_uuid7(),
    )
    with g.engine.connect() as conn:
        old = dict(conn.execute(text("SELECT * FROM capability_invocations")).mappings().one())
    g.args = replace(g.args, invocation_id=new_uuid7())
    original = SqlAlchemyGatewayRepository.insert
    before = _rows(g.engine)
    changes = {
        "project": {"project_id": foreign_project},
        "task": {"research_task_id": foreign_task},
        "step": {"step_id": new_uuid7()},
        "version_actor": {"agent_actor_id": g.owner.actor_id},
        "version_scope": {"agent_version_id": new_uuid7()},
        "policy_scope": {"policy_id": new_uuid7()},
        "reservation_operation": {"reservation_id": old["reservation_id"]},
        "usage_reservation": {"usage_record_id": old["usage_record_id"]},
        "request_receipt": {"request_receipt_id": old["request_receipt_id"]},
        "start_receipt": {"start_receipt_id": old["start_receipt_id"]},
        "finish_receipt": {"finish_receipt_id": old["finish_receipt_id"]},
    }
    for label, change in changes.items():
        reached = []

        def insert(repo, table, row, change=change, reached=reached):
            if table == "capability_invocations":
                reached.append(True)
                row = dict(row, **change)
            return original(repo, table, row)

        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
            with pytest.raises(ResearchBaseError):
                g.gateway_service.request_capability_invocation(
                    g.owner,
                    request_command(g),
                    g.context,
                )
        assert reached == [True] and _rows(g.engine) == before, label
    print("COMPOSITE_DML_DENIALS", list(changes))


def test_output_ref_lifecycle_scope_freeze_and_hash_errors(gateway, monkeypatch):
    from dataclasses import replace

    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.phase3.conftest import draft_inputs
    from tests.integration.phase3.gateway_fixtures import (
        finish,
        owning_inputs,
        request_invocation,
        start,
    )
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    frozen = owning_inputs(g.p)
    drafts = cast(Any, draft_inputs).__wrapped__(g.p, frozen)
    foreign_project = g.identity.create_project_with_owner(
        g.owner,
        name="Foreign output scope",
        request_id=new_uuid7(),
    )
    foreign = _artifact(g.factory, g.store, g.owner, foreign_project, b"Foreign output")
    request_invocation(g)
    start(g)
    before = _rows(g.engine)
    original = SqlAlchemyGatewayRepository.insert
    for case in (
        "scope",
        "freeze",
        "hash",
        "non-artifact",
        "FAILED",
        "CANCELLED",
        "UNKNOWN_OUTCOME",
    ):
        reached = []

        def insert(repo, table, row, case=case, reached=reached):
            if table == "capability_invocation_refs" and row["direction"] == "OUTPUT":
                reached.append(case)
                row = dict(row)
                if case == "scope":
                    row["artifact_version_id"] = foreign
                elif case == "freeze":
                    row["artifact_version_id"] = drafts["ARTIFACT_VERSION"]
                elif case == "hash":
                    row["content_hash"] = "0" * 64
                elif case == "non-artifact":
                    row["artifact_version_id"] = None
                    row["research_question_version_id"] = frozen["RESEARCH_QUESTION_VERSION"]
            original(repo, table, row)
            if table == "capability_invocation_events" and case in (
                "FAILED",
                "CANCELLED",
                "UNKNOWN_OUTCOME",
            ):
                reached.append(case)
                original(
                    repo,
                    "capability_invocation_refs",
                    {
                        "id": new_uuid7(),
                        "project_id": g.project,
                        "research_task_id": g.task,
                        "invocation_id": g.args.invocation_id,
                        "receipt_id": row["receipt_id"],
                        "direction": "OUTPUT",
                        "artifact_version_id": g.args.input_refs[0].version_id,
                        "content_hash": g.args.input_refs[0].content_hash,
                        "hash_scheme": None,
                    },
                )

        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyGatewayRepository, "insert", insert)
            with pytest.raises(ResearchBaseError):
                if case in ("FAILED", "CANCELLED", "UNKNOWN_OUTCOME"):
                    finish(g, case)
                else:
                    finish(g, output_refs=(g.args.input_refs[0],))
        assert reached == [case] and _rows(g.engine) == before, case
    finish(g, output_refs=(replace(g.args.input_refs[0]),))
