"""Live PostgreSQL inventory and direct-SQL PR2-04 counterexamples.

Fixtures use accepted Application commands. Rejections execute outside the UoW so
the evidence records the actual PostgreSQL backstop, including deferred COMMIT guards.
"""

# Frozen inventory and literal SQL deliberately keep complete column lists visible.
# ruff: noqa: E501

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_plan import CreateLiteratureSearchPlan
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _material as _plan_material,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_recovery import (
    OutcomeBeforeFinalization,
    ReservedBeforeInvocation,
)
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

TABLES = (
    "literature_search_executions",
    "literature_search_provider_attempts",
    "search_query_records",
    "search_result_records",
    "literature_search_execution_events",
    "literature_search_execution_command_receipts",
)
E, A, Q, R, V, C = TABLES
JSON_COLUMNS = {"execution_context", "warning_codes", "result_dto"}

# Frozen pack §13 inventory, including the accepted concrete provider-attempt FK.
NULLABLE = {
    E: {"started_at", "finished_at", "failure_code"},
    A: {
        "query_record_id",
        "invoked_at",
        "returned_at",
        "retrieved_at",
        "completed_at",
        "delivery_certainty",
        "provider_request_id",
        "failure_code",
        "retry_after_seconds",
        "warning_codes",
        "result_count",
    },
    Q: {"perspective", "provider_version"},
    R: {"external_identifier", "url", "snippet", "provider_score"},
    V: {"attempt_id", "prior_status", "prior_row_version"},
    C: set(),
}
COLUMNS = {
    E: "id project_id search_plan_version_id strategy_id strategy_version status requested_by executed_by started_at finished_at execution_context idempotency_key failure_code row_version created_by created_at",
    A: "id execution_id query_index attempt_number provider_request_key reserved_at deadline_at recovery_after status query_record_id invoked_at returned_at retrieved_at completed_at delivery_certainty provider_request_id failure_code retry_after_seconds warning_codes result_count row_version created_by created_at",
    Q: "id literature_search_execution_id provider_attempt_id query_text perspective provider_id provider_version ordinal executed_at query_hash hash_scheme created_by created_at",
    R: "id search_query_record_id rank external_identifier title url snippet provider_score retrieved_at content_hash hash_scheme created_by created_at",
    V: "id execution_id sequence kind attempt_id prior_status new_status prior_row_version new_row_version occurred_at created_by created_at",
    C: "id deployment_id project_id actor_id command_name request_id request_hash hash_scheme result_execution_id result_dto_version result_dto completed_at created_by created_at",
}
UNIQUE_COLUMNS = {
    E: {("project_id", "idempotency_key"), ("project_id", "id")},
    A: {
        ("execution_id", "query_index", "attempt_number"),
        ("execution_id", "provider_request_key"),
        ("execution_id", "id"),
        ("query_record_id",),
    },
    Q: {
        ("provider_attempt_id",),
        ("literature_search_execution_id", "ordinal"),
        ("literature_search_execution_id", "query_hash"),
        ("literature_search_execution_id", "id"),
    },
    R: {("search_query_record_id", "rank")},
    V: {("execution_id", "sequence"), ("execution_id", "new_row_version")},
    C: {("deployment_id", "actor_id", "project_id", "command_name", "request_id")},
}


def _material(url: str, stage: str = "sealed", hits: int = 1) -> dict[str, Any]:
    engine, plans, principal, project, plan, version = _setup(url)
    _freeze(engine, plans, principal, project, plan, version)
    provider = FakeSearchCapability(
        capability_id="provider-a",
        version="1",
        responses=[
            SearchResponse.success(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
                provider_request_id="observed-request",
                hits=tuple(
                    SearchHit(f"hit-{i}", f"Title {i}", None, None, None) for i in range(hits)
                ),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ],
    )
    service_type = {
        "reserved": ReservedBeforeInvocation,
        "sealed": OutcomeBeforeFinalization,
    }.get(stage, LiteratureSearchExecutionService)
    service = service_type(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
    )
    admission = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution = UUID(admission["execution_id"])
    if stage != "planned":
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )
    return dict(
        engine=engine,
        principal=principal,
        project=project,
        version=version,
        execution=execution,
        provider=provider,
        service=service,
        plans=plans,
        plan=plan,
    )


def _rows(engine) -> dict[str, list[dict[str, Any]]]:
    with engine.connect() as connection:
        return {
            table: [
                dict(row)
                for row in connection.execute(
                    text(f"SELECT * FROM {table} ORDER BY created_at,id")
                ).mappings()
            ]
            for table in TABLES
        }


def _insert(connection, table: str, row: dict[str, Any]) -> None:
    values = {
        key: json.dumps(value) if key in JSON_COLUMNS and value is not None else value
        for key, value in row.items()
    }
    placeholders = [f"CAST(:{key} AS jsonb)" if key in JSON_COLUMNS else f":{key}" for key in row]
    connection.execute(
        text(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(placeholders)})"), values
    )


def _reject(
    engine,
    operation: Callable,
    sqlstate: str,
    trace: FactRecorder,
    *,
    case: str,
    diagnostic: str | None = None,
) -> None:
    before = _rows(engine)
    caught = None
    try:
        with engine.begin() as connection:
            operation(connection)
    except DBAPIError as exc:
        caught = exc
    actual = getattr(caught.orig, "sqlstate", None) if caught is not None else None
    primary = (
        getattr(getattr(caught.orig, "diag", None), "message_primary", None) if caught else None
    )
    after = _rows(engine)
    trace.record(
        case=case,
        rejected_sqlstate=actual,
        primary_diagnostic=primary,
        expected_sqlstate=sqlstate,
        before_counts={t: len(r) for t, r in before.items()},
        after_counts={t: len(r) for t, r in after.items()},
        durable_rows_unchanged=after == before,
    )
    assert caught is not None, f"database accepted forbidden SQL case {case}"
    assert actual == sqlstate
    if diagnostic is not None:
        assert primary == diagnostic
    assert after == before


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_live_column_pk_nullability_and_fk_restrict_inventory(
    phase2_database_url: str,
    table: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table)
        fks = inspector.get_foreign_keys(table)
        uniques = inspector.get_unique_constraints(table)
        pr204_trace.record(
            table=table,
            columns=[
                {
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": c["nullable"],
                    "default": c["default"],
                }
                for c in columns
            ],
            foreign_keys=fks,
            unique_constraints=uniques,
            primary_key=inspector.get_pk_constraint(table),
            durable_counts={t: len(r) for t, r in _rows(engine).items()},
        )
        assert {c["name"] for c in columns} == set(COLUMNS[table].split())
        assert {c["name"] for c in columns if c["nullable"]} == NULLABLE[table]
        assert inspector.get_pk_constraint(table)["constrained_columns"] == ["id"]
        assert all(fk["options"].get("ondelete") == "RESTRICT" for fk in fks)
        assert UNIQUE_COLUMNS[table] <= {tuple(u["column_names"]) for u in uniques}
        assert (
            "row_version" in COLUMNS[table].split()
            if table in (E, A)
            else "row_version" not in COLUMNS[table].split()
        )
        assert all(str(c["type"]) == "UUID" for c in columns if c["name"] in {"id", "created_by"})
        assert all(
            str(c["type"]) == "TIMESTAMP" and c["type"].timezone
            for c in columns
            if c["name"] == "created_at"
        )
        uuid_columns = {
            "id",
            "created_by",
            "project_id",
            "search_plan_version_id",
            "requested_by",
            "executed_by",
            "idempotency_key",
            "execution_id",
            "provider_request_key",
            "query_record_id",
            "literature_search_execution_id",
            "provider_attempt_id",
            "search_query_record_id",
            "attempt_id",
            "actor_id",
            "request_id",
            "result_execution_id",
        }
        integer_columns = {
            "row_version",
            "query_index",
            "attempt_number",
            "retry_after_seconds",
            "result_count",
            "ordinal",
            "rank",
            "sequence",
            "prior_row_version",
            "new_row_version",
        }
        for column in columns:
            name, kind = column["name"], str(column["type"])
            if name in uuid_columns:
                assert kind == "UUID"
            elif name in JSON_COLUMNS:
                assert kind == "JSONB"
            elif name in integer_columns:
                assert kind == "INTEGER"
            elif name == "result_dto_version":
                assert kind == "SMALLINT"
            elif name.endswith("_at") or name == "recovery_after":
                assert kind == "TIMESTAMP" and column["type"].timezone
            elif name in {"query_hash", "content_hash", "request_hash"}:
                assert kind == "CHAR(64)"
            elif name == "provider_score":
                assert kind == "NUMERIC"
            else:
                assert kind == "TEXT" or kind.startswith("VARCHAR(")
        if table in (E, A):
            row_version = next(c for c in columns if c["name"] == "row_version")
            assert row_version["default"] == "1"
    finally:
        engine.dispose()


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.pr204_requirements("PR204-DB-02")
def test_every_fk_has_unconditional_leading_btree_index(
    phase2_database_url: str,
    table: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        with engine.connect() as connection:
            indexes = [
                dict(row)
                for row in connection.execute(
                    text("""
                SELECT ci.relname AS name, am.amname AS method,
                       i.indpred IS NULL AS unconditional,
                       ARRAY(SELECT a.attname FROM unnest(i.indkey::smallint[]) WITH ORDINALITY k(attnum,n)
                             JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
                             WHERE k.n <= i.indnkeyatts ORDER BY k.n) AS columns
                  FROM pg_index i JOIN pg_class ct ON ct.oid=i.indrelid
                  JOIN pg_class ci ON ci.oid=i.indexrelid
                  JOIN pg_am am ON am.oid=ci.relam
                 WHERE ct.oid=CAST(:table AS regclass) AND i.indisvalid
            """),
                    {"table": table},
                ).mappings()
            ]
        fks = inspect(engine).get_foreign_keys(table)
        missing = [
            fk["constrained_columns"]
            for fk in fks
            if not any(
                i["method"] == "btree"
                and i["unconditional"]
                and i["columns"][: len(fk["constrained_columns"])] == fk["constrained_columns"]
                for i in indexes
            )
        ]
        pr204_trace.record(
            table=table,
            indexes=indexes,
            foreign_keys=fks,
            missing_leading_indexes=missing,
            durable_counts={t: len(r) for t, r in _rows(engine).items()},
        )
        assert not missing
        if table == E:
            assert any(
                i["columns"] == ["project_id", "status", "created_at", "id"] for i in indexes
            )
        if table == C:
            assert any(
                i["columns"]
                == ["deployment_id", "actor_id", "project_id", "command_name", "request_id"]
                for i in indexes
            )
    finally:
        engine.dispose()


NOT_NULL_CASES = [
    (table, column)
    for table in (E, A, Q, R, C)
    for column in COLUMNS[table].split()
    if column not in NULLABLE[table]
]


@pytest.mark.parametrize(
    "table,column", NOT_NULL_CASES, ids=[f"{t}.{c}" for t, c in NOT_NULL_CASES]
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_insert_required_column_null_is_rejected(
    phase2_database_url: str,
    table: str,
    column: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved" if table == A else "sealed")
    engine = material["engine"]
    try:
        row = _rows(engine)[table][0].copy()
        row["id"] = uuid4()
        if table == A:
            row["provider_request_key"] = row["id"]
        row[column] = None
        attribution = table == E and column in {"requested_by", "executed_by", "created_by"}
        _reject(
            engine,
            lambda c: _insert(c, table, row),
            "P17D5" if attribution else "23502",
            pr204_trace,
            case=f"{table}.{column}=NULL",
            diagnostic="PR2-04 initial attribution must equal requester" if attribution else None,
        )
    finally:
        engine.dispose()


IMMUTABLE_CASES = [
    pytest.param(
        table,
        operation,
        marks=pytest.mark.pr204_requirements(
            "PR204-DB-04" if table in (Q, R) else "PR204-DB-05" if table == A else "PR204-DB-06"
        ),
        id=f"{table}-{operation}",
    )
    for table in (Q, R, V, C, A)
    for operation in ("update", "delete")
]


@pytest.mark.parametrize("table,operation", IMMUTABLE_CASES)
def test_immutable_rows_reject_update_and_delete(
    phase2_database_url: str,
    table: str,
    operation: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url)
    engine = material["engine"]
    try:
        identifier = _rows(engine)[table][0]["id"]
        sql = (
            f"DELETE FROM {table} WHERE id=:id"
            if operation == "delete"
            else f"UPDATE {table} SET created_at=created_at+interval '1 second' WHERE id=:id"
        )
        _reject(
            engine,
            lambda c: c.execute(text(sql), {"id": identifier}),
            "P17D1",
            pr204_trace,
            case=f"{table}-{operation}",
        )
    finally:
        engine.dispose()


EXECUTION_MATERIAL = {
    "id": "gen_random_uuid()",
    "project_id": "gen_random_uuid()",
    "search_plan_version_id": "gen_random_uuid()",
    "strategy_id": "'other'",
    "strategy_version": "'2'",
    "requested_by": "gen_random_uuid()",
    "execution_context": "execution_context || jsonb_build_object('max_results',2)",
    "idempotency_key": "gen_random_uuid()",
    "created_by": "gen_random_uuid()",
    "created_at": "created_at+interval '1 second'",
    "executed_by": "gen_random_uuid()",
}


@pytest.mark.parametrize("column", list(EXECUTION_MATERIAL))
@pytest.mark.pr204_requirements("PR204-DB-03")
def test_execution_material_cannot_be_changed(
    phase2_database_url: str,
    column: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        _reject(
            engine,
            lambda c: c.execute(
                text(
                    f"UPDATE {E} SET {column}={EXECUTION_MATERIAL[column]},row_version=row_version+1 WHERE id=:id"
                ),
                {"id": material["execution"]},
            ),
            "P17D1",
            pr204_trace,
            case=column,
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("version", [0, 1, 3], ids=["zero", "no_increment", "double_increment"])
@pytest.mark.pr204_requirements("PR204-DB-03")
def test_execution_row_version_requires_exact_increment(
    phase2_database_url: str,
    version: int,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        _reject(
            engine,
            lambda c: c.execute(
                text(f"UPDATE {E} SET row_version=:v WHERE id=:id"),
                {"id": material["execution"], "v": version},
            ),
            "P17D5",
            pr204_trace,
            case=f"row_version={version}",
        )
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-03", "PR204-DB-06")
def test_execution_increment_without_matching_event_rolls_back_at_commit(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        _reject(
            engine,
            lambda c: c.execute(
                text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"),
                {"id": material["execution"]},
            ),
            "P17D5",
            pr204_trace,
            case="increment_without_event",
        )
    finally:
        engine.dispose()


RESERVATION_MATERIAL = {
    "id": "gen_random_uuid()",
    "execution_id": "gen_random_uuid()",
    "query_index": "1",
    "attempt_number": "2",
    "provider_request_key": "gen_random_uuid()",
    "reserved_at": "reserved_at+interval '1 second'",
    "deadline_at": "deadline_at+interval '1 second'",
    "recovery_after": "recovery_after+interval '1 second'",
    "created_by": "gen_random_uuid()",
    "created_at": "created_at+interval '1 second'",
}


@pytest.mark.parametrize("column", list(RESERVATION_MATERIAL))
@pytest.mark.pr204_requirements("PR204-DB-05")
def test_reserved_attempt_material_is_fixed(
    phase2_database_url: str,
    column: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        identifier = _rows(engine)[A][0]["id"]
        _reject(
            engine,
            lambda c: c.execute(
                text(f"UPDATE {A} SET {column}={RESERVATION_MATERIAL[column]} WHERE id=:id"),
                {"id": identifier},
            ),
            "P17D1",
            pr204_trace,
            case=column,
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "table",
    [
        pytest.param(
            t,
            marks=pytest.mark.pr204_requirements(
                "PR204-DB-04" if t in (Q, R) else "PR204-DB-05" if t == A else "PR204-DB-06"
            ),
            id=t,
        )
        for t in (A, Q, R, V)
    ],
)
def test_terminal_execution_rejects_new_attempt_query_result_and_event(
    phase2_database_url: str,
    table: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "terminal")
    engine = material["engine"]
    try:
        rows = _rows(engine)
        row = rows[table][-1].copy()
        row["id"] = uuid4()
        if table == A:
            row.update(
                provider_request_key=row["id"],
                status="RESERVED",
                row_version=1,
                **{k: None for k in NULLABLE[A]},
            )
        if table == V:
            row.update(
                kind="CANCEL_REQUESTED",
                attempt_id=None,
                sequence=row["sequence"] + 1,
                prior_status="SUCCEEDED",
                prior_row_version=row["new_row_version"] - 1,
            )
        _reject(engine, lambda c: _insert(c, table, row), "P17D3", pr204_trace, case=table)
    finally:
        engine.dispose()


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.pr204_requirements("PR204-DB-03")
def test_terminal_execution_rejects_update_and_delete(
    phase2_database_url: str,
    operation: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "terminal")
    engine = material["engine"]
    try:
        sql = (
            f"DELETE FROM {E} WHERE id=:id"
            if operation == "delete"
            else f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"
        )
        # The immutable CREATED event is a permanent concrete FK dependent:
        # DELETE is rejected by RESTRICT; UPDATE has a dedicated terminal guard.
        _reject(
            engine,
            lambda c: c.execute(text(sql), {"id": material["execution"]}),
            "23001" if operation == "delete" else "P17D1",
            pr204_trace,
            case=f"terminal-{operation}",
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", ["same_parent", "ordinal_gap", "missing_seal", "input_mismatch"])
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-04")
def test_query_same_parent_and_atomic_observation_guards(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        attempt = _rows(engine)[A][0]
        row = dict(
            id=uuid4(),
            literature_search_execution_id=material["execution"],
            provider_attempt_id=attempt["id"],
            query_text="normalization evidence",
            perspective=None,
            provider_id="provider-a",
            provider_version="1",
            ordinal=0,
            executed_at=attempt["reserved_at"],
            query_hash="a" * 64,
            hash_scheme="sha256-cjson-v1",
            created_by=material["principal"].actor_id,
            created_at=attempt["reserved_at"],
        )
        if case == "same_parent":
            principal = material["principal"]
            second = material["service"].create(
                CreateLiteratureSearchExecution(
                    material["project"],
                    material["version"],
                    principal.actor_id,
                    principal.deployment_id,
                    uuid4(),
                    "provider-a",
                    "1",
                    ("normalization evidence",),
                    principal=principal,
                )
            )
            second_id = UUID(second["execution_id"])
            material["service"].execute(
                ExecuteLiteratureSearchExecution(
                    second_id,
                    principal.actor_id,
                    principal.deployment_id,
                    uuid4(),
                    project_id=material["project"],
                    principal=principal,
                )
            )
            row["provider_attempt_id"] = next(
                a["id"] for a in _rows(engine)[A] if a["execution_id"] == second_id
            )
        if case == "ordinal_gap":
            row["ordinal"] = 2
        if case == "input_mismatch":
            row["query_text"] = "unadmitted query"

        def mutate(connection):
            _insert(connection, Q, row)
            if case in ("ordinal_gap", "input_mismatch"):
                connection.execute(
                    text(f"""UPDATE {A} SET status='SUCCEEDED',query_record_id=:q,
                    invoked_at=:now,returned_at=:now,retrieved_at=:now,completed_at=clock_timestamp(),
                    delivery_certainty='RESPONSE_RECEIVED',result_count=0,warning_codes='[]'::jsonb,
                    row_version=2 WHERE id=:id"""),
                    {"q": row["id"], "now": row["executed_at"], "id": attempt["id"]},
                )

        _reject(
            engine, mutate, "23503" if case == "same_parent" else "P17D5", pr204_trace, case=case
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", ["rank_gap", "orphan", "late_append", "different_retrieved_at"])
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-04")
def test_result_orphan_rank_late_append_and_retrieval_guards(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url)
    engine = material["engine"]
    try:
        row = _rows(engine)[R][0].copy()
        row.update(id=uuid4(), rank=2 if case == "rank_gap" else 1)
        if case == "orphan":
            row["search_query_record_id"] = uuid4()
        if case == "different_retrieved_at":
            row["retrieved_at"] += timedelta(seconds=1)
        _reject(
            engine,
            lambda c: _insert(c, R, row),
            "23503" if case == "orphan" else "P17D5",
            pr204_trace,
            case=case,
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case", ["gap", "wrong_status", "wrong_version", "wrong_prior", "event_only"]
)
@pytest.mark.pr204_requirements("PR204-DB-06")
def test_event_coordinates_cannot_fabricate_execution_mutation(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        row = _rows(engine)[V][0].copy()
        row.update(
            id=uuid4(),
            sequence=1,
            kind="CANCEL_REQUESTED",
            prior_status="PLANNED",
            new_status="PLANNED",
            prior_row_version=1,
            new_row_version=2,
        )
        if case == "gap":
            row["sequence"] = 3
        if case == "wrong_status":
            row["new_status"] = "RUNNING"
        if case == "wrong_version":
            row["new_row_version"] = 3
        if case == "wrong_prior":
            row["prior_row_version"] = 0

        def mutate(connection):
            if case != "event_only":
                connection.execute(
                    text(f"UPDATE {E} SET row_version=2 WHERE id=:id"),
                    {"id": material["execution"]},
                )
            _insert(connection, V, row)

        _reject(engine, mutate, "P17D5", pr204_trace, case=case)
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-06")
def test_terminal_recovery_receipt_and_exact_replay_preserve_all_provenance(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "terminal")
    engine, principal = material["engine"], material["principal"]
    try:
        before = _rows(engine)
        calls = len(material["provider"].calls)
        command = RecoverLiteratureSearchExecution(
            material["execution"],
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=material["project"],
            principal=principal,
        )
        admission = material["service"].recover(command)
        after = _rows(engine)
        replay = material["service"].recover(command)
        replay_rows = _rows(engine)
        pr204_trace.record(
            before_counts={t: len(r) for t, r in before.items()},
            after_counts={t: len(r) for t, r in after.items()},
            replay_counts={t: len(r) for t, r in replay_rows.items()},
            provider_calls_before=calls,
            provider_calls_after=len(material["provider"].calls),
            admission=admission,
            replay=replay,
            execution=after[E],
        )
        assert admission == replay
        assert after == replay_rows
        assert len(after[C]) == len(before[C]) + 1
        assert all(after[t] == before[t] for t in TABLES if t != C)
        assert len(material["provider"].calls) == calls
    finally:
        engine.dispose()


INVALID_INSERTS = [
    (E, "status", "BOGUS", "23514"),
    (E, "strategy_id", "other", "23514"),
    (E, "strategy_version", "2", "23514"),
    (E, "row_version", 0, "23514"),
    (E, "failure_code", "PROVIDER_PERMANENT", "23514"),
    (E, "requested_by", "absent_uuid", "P17D5"),
    (E, "created_by", "absent_uuid", "P17D5"),
    (E, "search_plan_version_id", "absent_uuid", "23503"),
    (E, "project_id", "absent_uuid", "23503"),
    (A, "query_index", -1, "23514"),
    (A, "attempt_number", 0, "23514"),
    (A, "status", "BOGUS", "P17D5"),
    (A, "row_version", 2, "P17D5"),
    (A, "provider_request_key", "absent_uuid", "P17D5"),
    (A, "created_by", "absent_uuid", "23503"),
    (Q, "ordinal", -1, "23514"),
    (Q, "query_hash", "A" * 64, "23514"),
    (Q, "created_by", "absent_uuid", "23503"),
    (R, "rank", -1, "23514"),
    (R, "content_hash", "A" * 64, "23514"),
    (R, "provider_score", "NaN", "23514"),
    (R, "provider_score", "Infinity", "23514"),
    (R, "provider_score", "-Infinity", "23514"),
    (R, "title", "x" * 2049, "22001"),
    (R, "url", "x" * 4097, "22001"),
    (R, "external_identifier", "x" * 1025, "22001"),
    (R, "snippet", "x" * 4097, "22001"),
    (R, "created_by", "absent_uuid", "23503"),
    (C, "deployment_id", " ", "23514"),
    (C, "command_name", "BOGUS", "23514"),
    (C, "request_hash", "A" * 64, "23514"),
    (C, "hash_scheme", "other", "23514"),
    (C, "result_dto_version", 2, "23514"),
    (C, "result_execution_id", "absent_uuid", "23514"),
]


@pytest.mark.parametrize(
    "table,column,value,sqlstate",
    INVALID_INSERTS,
    ids=[f"{t}.{c}-{i}" for i, (t, c, _, _) in enumerate(INVALID_INSERTS)],
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_insert_checks_lengths_and_missing_foreign_parents(
    phase2_database_url: str,
    table: str,
    column: str,
    value: Any,
    sqlstate: str,
    pr204_trace: FactRecorder,
) -> None:
    stage = "planned" if table == E else "reserved" if table == A else "sealed"
    query_creator = table == Q and column == "created_by"
    if query_creator:
        stage = "reserved"
    material = _material(phase2_database_url, stage)
    engine = material["engine"]
    try:
        if query_creator:
            attempt = _rows(engine)[A][0]
            row = dict(
                id=uuid4(),
                literature_search_execution_id=material["execution"],
                provider_attempt_id=attempt["id"],
                query_text="normalization evidence",
                perspective=None,
                provider_id="provider-a",
                provider_version="1",
                ordinal=0,
                executed_at=attempt["reserved_at"],
                query_hash="a" * 64,
                hash_scheme="sha256-cjson-v1",
                created_by=material["principal"].actor_id,
                created_at=attempt["reserved_at"],
            )
        else:
            row = _rows(engine)[table][0].copy()
        row["id"] = uuid4()
        if table == E:
            row["idempotency_key"] = uuid4()
        if table == A:
            row["provider_request_key"] = row["id"]
        if table == C:
            row["request_id"] = uuid4()
        if table == Q and not query_creator:
            row.update(ordinal=1, query_hash="b" * 64)
        if table == R:
            row["rank"] = 1
        row[column] = uuid4() if value == "absent_uuid" else value

        def mutate(connection):
            if table == A and column == "created_by":
                connection.execute(
                    text(f"""UPDATE {A} SET status='RETRYABLE_FAILURE',
                    completed_at=clock_timestamp(),delivery_certainty='NOT_SENT',
                    failure_code='PROVIDER_TRANSIENT',warning_codes='[]'::jsonb,
                    result_count=0,row_version=2 WHERE execution_id=:execution"""),
                    {"execution": material["execution"]},
                )
                row["attempt_number"] = 2
            _insert(connection, table, row)

        attribution = table == E and column in {"requested_by", "created_by"}
        _reject(
            engine,
            mutate,
            sqlstate,
            pr204_trace,
            case=f"{table}.{column}",
            diagnostic="PR2-04 initial attribution must equal requester" if attribution else None,
        )
        if attribution:
            # Also reach the actor FK with a coherent initial attribution tuple.
            absent_actor = row[column]
            coherent = {
                **row,
                "requested_by": absent_actor,
                "executed_by": absent_actor,
                "created_by": absent_actor,
            }
            _reject(
                engine,
                lambda c: _insert(c, E, coherent),
                "23503",
                pr204_trace,
                case=f"{table}.{column}-coherent-missing-actor",
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", ["one_reserved", "number_gap", "invalid_input_index"])
@pytest.mark.pr204_requirements("PR204-DB-05")
def test_reservation_uniqueness_contiguity_and_input_bounds(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        row = _rows(engine)[A][0].copy()
        row.update(id=uuid4(), attempt_number=2)
        row["provider_request_key"] = row["id"]
        if case != "one_reserved":
            row.update(
                attempt_number=3 if case == "number_gap" else 1,
                query_index=0 if case == "number_gap" else 1,
            )

        def mutate(connection):
            if case != "one_reserved":
                # Seal a safe non-invoked failure so the new reservation is tested
                # against bounds rather than the one-RESERVED partial unique index.
                connection.execute(
                    text(f"""UPDATE {A} SET status='RETRYABLE_FAILURE',
                    completed_at=clock_timestamp(),delivery_certainty='NOT_SENT',
                    failure_code='PROVIDER_TRANSIENT',warning_codes='[]'::jsonb,
                    result_count=0,row_version=2 WHERE execution_id=:execution"""),
                    {"execution": material["execution"]},
                )
            _insert(connection, A, row)

        _reject(
            engine, mutate, "23505" if case == "one_reserved" else "P17D5", pr204_trace, case=case
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "field,value",
    [
        ("result_dto", {}),
        ("result_dto", {"extra": True}),
        ("accepted_row_version", 0),
        ("accepted_row_version", "1"),
        ("accepted_at", None),
        ("execution_id", str(UUID(int=0))),
        ("command_name", "EXECUTE_LITERATURE_SEARCH_EXECUTION"),
    ],
)
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-06")
def test_receipt_projection_is_closed_typed_and_fk_bound(
    phase2_database_url: str,
    field: str,
    value: Any,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        row = _rows(engine)[C][0].copy()
        row.update(id=uuid4(), request_id=uuid4())
        if field == "result_dto":
            row[field] = value
        else:
            row["result_dto"] = {**row["result_dto"], field: value}
        _reject(engine, lambda c: _insert(c, C, row), "23514", pr204_trace, case=field)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case",
    ["absent_execution", "wrong_project", "wrong_terminal_command", "wrong_terminal_version"],
)
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-06")
def test_new_receipt_terminal_exception_requires_existing_scoped_execution(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "terminal")
    engine = material["engine"]
    try:
        rows = _rows(engine)
        row = rows[C][0].copy()
        row.update(
            id=uuid4(), request_id=uuid4(), command_name="RECOVER_LITERATURE_SEARCH_EXECUTION"
        )
        row["result_dto"] = {
            **row["result_dto"],
            "command_name": row["command_name"],
            "accepted_row_version": rows[E][0]["row_version"],
        }
        if case == "absent_execution":
            row["result_execution_id"] = uuid4()
            row["result_dto"]["execution_id"] = str(row["result_execution_id"])
        if case == "wrong_project":
            row["project_id"] = uuid4()
        if case == "wrong_terminal_command":
            row["command_name"] = "EXECUTE_LITERATURE_SEARCH_EXECUTION"
            row["result_dto"]["command_name"] = row["command_name"]
        if case == "wrong_terminal_version":
            row["result_dto"]["accepted_row_version"] += 1
        _reject(
            engine,
            lambda c: _insert(c, C, row),
            "23503" if case in ("absent_execution", "wrong_project") else "P17D3",
            pr204_trace,
            case=case,
        )
    finally:
        engine.dispose()


def _execution_with_created_event(connection, row, event) -> None:
    _insert(connection, E, row)
    _insert(connection, V, {**event, "id": uuid4(), "execution_id": row["id"]})


CONTEXT_INVALID = [
    ("schema_version", 2),
    ("provider_id", ""),
    ("provider_version", ""),
    ("provider_id", "x" * 129),
    ("provider_version", "x" * 129),
    ("max_results", 0),
    ("max_results", 101),
    ("max_results", "1"),
    ("max_provider_attempts", 0),
    ("max_provider_attempts", 4),
    ("timeout_seconds", 0),
    ("timeout_seconds", 31),
    ("execution_budget_seconds", 0),
    ("execution_budget_seconds", 601),
    ("queries", []),
    ("queries", [{"query_type": "TEXT", "query_text": "x", "perspective": None}] * 33),
    ("queries", [{"query_type": "OTHER", "query_text": "x", "perspective": None}]),
    ("queries", [{"query_type": "TEXT", "query_text": " ", "perspective": None}]),
    ("queries", [{"query_type": "TEXT", "query_text": "x" * 4097, "perspective": None}]),
    ("queries", [{"query_type": "TEXT", "query_text": "x", "perspective": "x" * 257}]),
    ("extra_key", "unadmitted"),
]


@pytest.mark.parametrize(
    "field,value",
    CONTEXT_INVALID,
    ids=[f"{field}-{i}" for i, (field, _) in enumerate(CONTEXT_INVALID)],
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_execution_closed_context_schema_and_bounds_are_database_enforced(
    phase2_database_url: str,
    field: str,
    value: Any,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        rows = _rows(engine)
        row = {**rows[E][0], "id": uuid4(), "idempotency_key": uuid4()}
        row["execution_context"] = {**row["execution_context"], field: value}
        _reject(
            engine,
            lambda c: _execution_with_created_event(c, row, rows[V][0]),
            "P17D5",
            pr204_trace,
            case=f"context.{field}",
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", ["draft_plan", "other_project_plan"])
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_execution_insert_requires_frozen_plan_in_same_project(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        rows = _rows(engine)
        row = {**rows[E][0], "id": uuid4(), "idempotency_key": uuid4()}
        if case == "draft_plan":
            draft = material["plans"].create(
                CreateLiteratureSearchPlan(
                    material["principal"],
                    material["project"],
                    _plan_material(UUID(int=0), language_scope=()),
                    uuid4(),
                )
            )
            row["search_plan_version_id"] = UUID(draft["version_id"])
        else:
            with engine.begin() as connection:
                project = dict(
                    connection.execute(
                        text("SELECT * FROM projects WHERE id=:id"), {"id": material["project"]}
                    )
                    .mappings()
                    .one()
                )
                project["id"] = uuid4()
                _insert(connection, "projects", project)
            row["project_id"] = project["id"]
        _reject(
            engine,
            lambda c: _execution_with_created_event(c, row, rows[V][0]),
            "P17D5",
            pr204_trace,
            case=case,
        )
    finally:
        engine.dispose()


SEAL_INVALID = [
    ("result_count", -1, "23514"),
    ("result_count", 1, "23514"),
    ("retry_after_seconds", -1, "23514"),
    ("retry_after_seconds", 2147483648, "22003"),
    ("delivery_certainty", "BOGUS", "23514"),
    ("failure_code", "BOGUS", "23514"),
    ("warning_codes", ["BOGUS"], "23514"),
    ("warning_codes", {}, "23514"),
    ("warning_codes", ["RATE_LIMITED", "RATE_LIMITED"], "P17D5"),
    ("row_version", 1, "P17D5"),
    ("row_version", 3, "P17D5"),
    ("status", "UNKNOWN", "23514"),
]


@pytest.mark.parametrize(
    "field,value,sqlstate",
    SEAL_INVALID,
    ids=[f"{field}-{i}" for i, (field, _, _) in enumerate(SEAL_INVALID)],
)
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")
def test_attempt_outcome_shape_certainty_reason_warnings_and_version_guards(
    phase2_database_url: str,
    field: str,
    value: Any,
    sqlstate: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        values = dict(
            status="PERMANENT_FAILURE",
            completed_at=None,
            delivery_certainty="NOT_SENT",
            failure_code="PROVIDER_PERMANENT",
            warning_codes=[],
            result_count=0,
            row_version=2,
        )
        values[field] = value

        def mutate(connection):
            assignments = ["completed_at=clock_timestamp()"]
            parameters = {"id": _rows(engine)[A][0]["id"]}
            for key, item in values.items():
                if key == "completed_at":
                    continue
                assignments.append(
                    f"{key}=CAST(:{key} AS jsonb)" if key in JSON_COLUMNS else f"{key}=:{key}"
                )
                parameters[key] = json.dumps(item) if key in JSON_COLUMNS else item
            connection.execute(
                text(f"UPDATE {A} SET {','.join(assignments)} WHERE id=:id"), parameters
            )

        _reject(engine, mutate, sqlstate, pr204_trace, case=field)
    finally:
        engine.dispose()


@pytest.mark.parametrize("column", sorted(set(COLUMNS[V].split()) - NULLABLE[V]))
@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-06")
def test_event_required_columns_reject_null_in_matching_mutation(
    phase2_database_url: str,
    column: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        row = _rows(engine)[V][0].copy()
        row.update(
            id=uuid4(),
            sequence=1,
            kind="CANCEL_REQUESTED",
            prior_status="PLANNED",
            new_status="PLANNED",
            prior_row_version=1,
            new_row_version=2,
        )
        row[column] = None

        def mutate(connection):
            connection.execute(
                text(f"UPDATE {E} SET row_version=2 WHERE id=:id"), {"id": material["execution"]}
            )
            _insert(connection, V, row)

        sqlstate = (
            "P17D2" if column == "execution_id" else "P17D5" if column == "new_status" else "23502"
        )
        _reject(engine, mutate, sqlstate, pr204_trace, case=f"event.{column}=NULL")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case", ["execution_idempotency", "query_ordinal", "query_hash", "result_rank", "receipt_scope"]
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_direct_sql_unique_scopes_reject_duplicate_material(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(
        phase2_database_url, "planned" if case == "execution_idempotency" else "sealed"
    )
    engine = material["engine"]
    try:
        table = {
            "execution_idempotency": E,
            "query_ordinal": Q,
            "query_hash": Q,
            "result_rank": R,
            "receipt_scope": C,
        }[case]
        row = {**_rows(engine)[table][0], "id": uuid4()}
        if case == "query_ordinal":
            row["query_hash"] = "b" * 64
        if case == "query_hash":
            row["ordinal"] = 1
        _reject(engine, lambda c: _insert(c, table, row), "23505", pr204_trace, case=case)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case", ["rank_gap_at_seal", "mixed_retrieval_times", "failed_attempt_has_results"]
)
@pytest.mark.pr204_requirements("PR204-DB-04", "PR204-DB-05")
def test_atomic_outcome_rejects_invalid_complete_response_set(
    phase2_database_url: str,
    case: str,
    pr204_trace: FactRecorder,
) -> None:
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        attempt = _rows(engine)[A][0]
        actor, now = material["principal"].actor_id, attempt["reserved_at"]
        query = dict(
            id=uuid4(),
            literature_search_execution_id=material["execution"],
            provider_attempt_id=attempt["id"],
            query_text="normalization evidence",
            perspective=None,
            provider_id="provider-a",
            provider_version="1",
            ordinal=0,
            executed_at=now,
            query_hash="a" * 64,
            hash_scheme="sha256-cjson-v1",
            created_by=actor,
            created_at=now,
        )
        results: list[dict[str, Any]] = [
            dict(
                id=uuid4(),
                search_query_record_id=query["id"],
                rank=i,
                external_identifier=f"hit-{i}",
                title=f"Title {i}",
                url=None,
                snippet=None,
                provider_score=None,
                retrieved_at=now,
                content_hash="b" * 64,
                hash_scheme="sha256-cjson-v1",
                created_by=actor,
                created_at=now,
            )
            for i in range(2)
        ]
        if case == "rank_gap_at_seal":
            results[1]["rank"] = 2
        if case == "mixed_retrieval_times":
            results[1]["retrieved_at"] += timedelta(seconds=1)

        def mutate(connection):
            _insert(connection, Q, query)
            for row in results:
                _insert(connection, R, row)
            connection.execute(
                text(f"""UPDATE {A} SET status=:status,query_record_id=:q,
                invoked_at=:now,returned_at=:now,completed_at=clock_timestamp(),
                delivery_certainty='RESPONSE_RECEIVED',failure_code=:reason,
                retrieved_at=:retrieved,
                result_count=:count,warning_codes='[]'::jsonb,row_version=2 WHERE id=:id"""),
                {
                    "id": attempt["id"],
                    "q": query["id"],
                    "now": now,
                    "retrieved": None if case == "failed_attempt_has_results" else now,
                    "status": "PERMANENT_FAILURE"
                    if case == "failed_attempt_has_results"
                    else "SUCCEEDED",
                    "reason": "PROVIDER_PERMANENT"
                    if case == "failed_attempt_has_results"
                    else None,
                    "count": 0 if case == "failed_attempt_has_results" else 2,
                },
            )

        _reject(engine, mutate, "P17D5", pr204_trace, case=case)
    finally:
        engine.dispose()
