"""A duplicate number is rejected independently of the one-RESERVED index."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_04_outcome_certainty_matrix_acceptance import (
    complete_outcome,
)
from tests.integration.phase2.test_pr2_04_remaining_schema_acceptance import positive_control
from tests.integration.phase2.test_pr2_04_schema_coverage import A, E, V, _insert, _material, _rows


@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")
def test_pg_attempt_number_unique_after_sealed_safe_predecessor(phase2_database_url, pr204_trace):
    m = _material(phase2_database_url, "reserved")
    engine = m["engine"]
    try:
        with engine.begin() as connection:
            complete_outcome(connection, m, "RETRYABLE_FAILURE", "PROVIDER_TRANSIENT", "NOT_SENT")
        before = _rows(engine)
        execution = next(row for row in before[E] if row["id"] == m["execution"])
        assert all(row["status"] != "RESERVED" for row in before[A])

        def reserve(connection, number):
            at = connection.scalar(text("SELECT clock_timestamp()"))
            attempt_id = uuid4()
            deadline = min(
                at + timedelta(seconds=execution["execution_context"]["timeout_seconds"]),
                execution["started_at"]
                + timedelta(seconds=execution["execution_context"]["execution_budget_seconds"]),
            )
            connection.execute(
                text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"),
                {"id": execution["id"]},
            )
            _insert(
                connection,
                A,
                dict(
                    id=attempt_id,
                    execution_id=execution["id"],
                    query_index=0,
                    attempt_number=number,
                    provider_request_key=attempt_id,
                    reserved_at=at,
                    deadline_at=deadline,
                    recovery_after=deadline + timedelta(seconds=30),
                    status="RESERVED",
                    row_version=1,
                    created_by=m["principal"].actor_id,
                    created_at=at,
                ),
            )
            _insert(
                connection,
                V,
                dict(
                    id=uuid4(),
                    execution_id=execution["id"],
                    sequence=3,
                    kind="ATTEMPT_RESERVED",
                    attempt_id=attempt_id,
                    prior_status="RUNNING",
                    new_status="RUNNING",
                    prior_row_version=3,
                    new_row_version=4,
                    occurred_at=at,
                    created_by=m["principal"].actor_id,
                    created_at=at,
                ),
            )

        positive_control(engine, lambda c: reserve(c, 2))
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                reserve(connection, 1)
        assert getattr(caught.value.orig, "sqlstate", None) == "23505"
        constraint = getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None)
        assert constraint == "uq_lspa_attempt_number"
        assert _rows(engine) == before
        pr204_trace.record(
            sqlstate="23505", constraint=constraint, before=before, after=_rows(engine)
        )
    finally:
        engine.dispose()
