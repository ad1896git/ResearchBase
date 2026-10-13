"""Direct lifecycle shape and event-FK negatives without disabled guards."""

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
from tests.integration.phase2.test_pr2_04_structural_guard_repair import _additional_execution


@pytest.mark.pr204_requirements("PR204-DB-01")
@pytest.mark.parametrize(
    "case,sqlstate",
    [
        ("running_missing_start", "23514"),
        ("running_early_finish", "P17D4"),
        ("running_reason", "P17D4"),
        ("clear_existing_start", "P17D4"),
        ("same_state_finish", "P17D4"),
        ("success_missing_finish", "23514"),
        ("failed_missing_finish", "23514"),
        ("unknown_missing_finish", "23514"),
        ("cancelled_missing_finish", "23514"),
        ("finish_before_start", "23514"),
        ("failed_missing_reason", "23514"),
        ("unknown_missing_reason", "23514"),
        ("cancelled_wrong_reason", "23514"),
    ],
)
def test_pg_execution_timestamp_reason_shapes(case, sqlstate, phase2_database_url, pr204_trace):
    planned = case.startswith("running_")
    material = _material(phase2_database_url, "planned" if planned else "reserved")
    engine = material["engine"]
    row = next(r for r in _rows(engine)[E] if r["id"] == material["execution"])
    now = row["created_at"] if planned else row["started_at"]
    changes = {"row_version": row["row_version"] + 1}
    if planned:
        changes.update(status="RUNNING", started_at=now, executed_by=material["principal"].actor_id)
        if case == "running_missing_start":
            changes["started_at"] = None
        elif case == "running_early_finish":
            changes["finished_at"] = now
        else:
            changes["failure_code"] = "PROVIDER_PERMANENT"
    elif case == "clear_existing_start":
        changes["started_at"] = None
    elif case == "same_state_finish":
        changes["finished_at"] = now
    else:
        status = case.split("_", 1)[0].upper()
        status = "SUCCEEDED" if status in {"SUCCESS", "FINISH"} else status
        changes.update(status=status, finished_at=now)
        if "missing_finish" in case:
            changes["finished_at"] = None
        if status in {"FAILED", "UNKNOWN", "CANCELLED"}:
            changes["failure_code"] = {
                "FAILED": "PROVIDER_PERMANENT",
                "UNKNOWN": "PROVIDER_OUTCOME_UNKNOWN",
                "CANCELLED": "CANCELLED",
            }[status]
        if "missing_reason" in case:
            changes["failure_code"] = None
        if case == "cancelled_wrong_reason":
            changes["failure_code"] = "PROVIDER_PERMANENT"
        if case == "finish_before_start":
            changes["finished_at"] = now - timedelta(seconds=1)

    def mutate(connection):
        assignments = ",".join(f"{key}=:{key}" for key in changes)
        connection.execute(
            text(f"UPDATE {E} SET {assignments} WHERE id=:id"),
            {**changes, "id": material["execution"]},
        )

    try:
        _reject(engine, mutate, sqlstate, pr204_trace, case=case)
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-TRACE-01")
def test_pg_event_attempt_requires_same_execution_fk(phase2_database_url, pr204_trace):
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        other, _ = _additional_execution(material, reserved=True)
        rows = _rows(engine)
        foreign = next(row for row in rows[A] if row["execution_id"] == other)
        execution = next(row for row in rows[E] if row["id"] == material["execution"])
        events = [row for row in rows[V] if row["execution_id"] == execution["id"]]

        def mutate(connection):
            connection.execute(
                text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"),
                {"id": execution["id"]},
            )
            _insert(
                connection,
                V,
                dict(
                    id=uuid4(),
                    execution_id=execution["id"],
                    sequence=len(events),
                    kind="OUTCOME_RECORDED",
                    attempt_id=foreign["id"],
                    prior_status="RUNNING",
                    new_status="RUNNING",
                    prior_row_version=execution["row_version"],
                    new_row_version=execution["row_version"] + 1,
                    occurred_at=execution["started_at"],
                    created_by=material["principal"].actor_id,
                    created_at=execution["started_at"],
                ),
            )

        _reject(engine, mutate, "23503", pr204_trace, case="cross_execution_event_attempt")
    finally:
        engine.dispose()
