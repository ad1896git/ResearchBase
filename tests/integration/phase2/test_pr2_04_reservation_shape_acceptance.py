"""Direct SQL reservation shape probes; no production trigger bypass."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.integration.phase2.test_pr2_04_schema_coverage import (
    A,
    E,
    V,
    _insert,
    _material,
    _reject,
    _rows,
)


def direct_first(connection, material, case):
    execution = material["execution"]
    at = connection.scalar(text("SELECT clock_timestamp()"))
    start = at - timedelta(seconds=601) if case == "expired_budget" else at
    context = next(row for row in _rows(material["engine"])[E] if row["id"] == execution)[
        "execution_context"
    ]
    deadline = at + timedelta(seconds=context["timeout_seconds"])
    if case == "deadline_exceeds_call":
        deadline += timedelta(seconds=1)
    if case == "deadline_not_after":
        deadline = at
    connection.execute(
        text(
            f"UPDATE {E} SET status='RUNNING',started_at=:at,executed_by=:actor,"
            "row_version=2 WHERE id=:execution"
        ),
        {"at": start, "actor": material["principal"].actor_id, "execution": execution},
    )
    attempt_id = uuid4()
    row = dict(
        id=attempt_id,
        execution_id=execution,
        query_index=0,
        attempt_number=1,
        provider_request_key=attempt_id,
        reserved_at=at,
        deadline_at=deadline,
        recovery_after=deadline + timedelta(seconds=30),
        status="RESERVED",
        row_version=1,
        created_by=material["principal"].actor_id,
        created_at=at,
    )
    if case == "wrong_request_key":
        row["provider_request_key"] = uuid4()
    elif case == "initial_version_two":
        row["row_version"] = 2
    elif case == "initial_nonreserved":
        row["status"] = "UNKNOWN"
    elif case == "reserved_has_outcome":
        row["result_count"] = 0
    elif case == "wrong_recovery_grace":
        row["recovery_after"] = deadline + timedelta(seconds=31)
    _insert(connection, A, row)
    _insert(
        connection,
        V,
        dict(
            id=uuid4(),
            execution_id=execution,
            sequence=1,
            kind="ATTEMPT_RESERVED",
            attempt_id=attempt_id,
            prior_status="PLANNED",
            new_status="RUNNING",
            prior_row_version=1,
            new_row_version=2,
            occurred_at=at,
            created_by=material["principal"].actor_id,
            created_at=at,
        ),
    )


@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")
@pytest.mark.parametrize(
    "case,sqlstate",
    [
        ("wrong_request_key", "P17D5"),
        ("initial_version_two", "P17D5"),
        ("initial_nonreserved", "P17D5"),
        ("reserved_has_outcome", "23514"),
        ("deadline_not_after", "23514"),
        ("wrong_recovery_grace", "23514"),
        ("deadline_exceeds_call", "P17D5"),
        ("expired_budget", "P17D5"),
    ],
)
def test_pg_direct_first_reservation_shape(case, sqlstate, phase2_database_url, pr204_trace):
    material = _material(phase2_database_url, "planned")
    try:
        _reject(
            material["engine"],
            lambda c: direct_first(c, material, case),
            sqlstate,
            pr204_trace,
            case=case,
        )
    finally:
        material["engine"].dispose()
