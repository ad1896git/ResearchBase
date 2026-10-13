"""Each frozen attempt outcome/reason and certainty combination on PostgreSQL."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.domain.literature_search_execution import SearchQueryRecord
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    A,
    E,
    Q,
    V,
    _insert,
    _material,
    _rows,
)

OUTCOMES = [
    ("SUCCEEDED", None, ("RESPONSE_RECEIVED",)),
    ("RETRYABLE_FAILURE", "PROVIDER_RATE_LIMIT", ("NOT_SENT", "RESPONSE_RECEIVED")),
    ("RETRYABLE_FAILURE", "PROVIDER_TRANSIENT", ("NOT_SENT", "RESPONSE_RECEIVED")),
    ("RETRYABLE_FAILURE", "PROVIDER_TIMEOUT", ("NOT_SENT",)),
    ("PERMANENT_FAILURE", "PROVIDER_PERMANENT", ("NOT_SENT", "RESPONSE_RECEIVED")),
    ("PERMANENT_FAILURE", "PROVIDER_MALFORMED", ("RESPONSE_RECEIVED",)),
    ("CANCELLED", "CANCELLED", ("NOT_SENT", "RESPONSE_RECEIVED")),
    ("UNKNOWN", "PROVIDER_OUTCOME_UNKNOWN", ("MAY_HAVE_BEEN_SENT",)),
    ("UNKNOWN", "RECOVERY_OUTCOME_UNKNOWN", ("MAY_HAVE_BEEN_SENT",)),
]


def complete_outcome(connection, m, outcome, reason, certainty):
    rows = _rows(m["engine"])
    execution = next(row for row in rows[E] if row["id"] == m["execution"])
    attempt = next(row for row in rows[A] if row["execution_id"] == execution["id"])
    at = connection.scalar(text("SELECT clock_timestamp()"))
    query = SearchQueryRecord(
        uuid4(), execution["id"], attempt["id"], 0, "normalization evidence", "provider-a", "1", at
    )
    # Actual direct-SQL TX B includes all causal rows and exact frozen query hash.
    _insert(
        connection,
        Q,
        dict(
            id=query.id,
            literature_search_execution_id=execution["id"],
            provider_attempt_id=attempt["id"],
            query_text=query.query_text,
            perspective=None,
            provider_id="provider-a",
            provider_version="1",
            ordinal=0,
            executed_at=at,
            query_hash=query.query_hash,
            hash_scheme="sha256-cjson-v1",
            created_by=m["principal"].actor_id,
            created_at=at,
        ),
    )
    connection.execute(
        text(
            f"UPDATE {A} SET status=:status,query_record_id=:query,invoked_at=:at,"
            "returned_at=:at,completed_at=:at,delivery_certainty=:certainty,"
            "failure_code=:reason,warning_codes='[]'::jsonb,result_count=0,"
            "retrieved_at=:retrieved,row_version=2 WHERE id=:id"
        ),
        dict(
            status=outcome,
            query=query.id,
            at=at,
            certainty=certainty,
            reason=reason,
            retrieved=at if outcome == "SUCCEEDED" else None,
            id=attempt["id"],
        ),
    )
    connection.execute(
        text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"), {"id": execution["id"]}
    )
    _insert(
        connection,
        V,
        dict(
            id=uuid4(),
            execution_id=execution["id"],
            sequence=2,
            kind="OUTCOME_RECORDED",
            attempt_id=attempt["id"],
            prior_status="RUNNING",
            new_status="RUNNING",
            prior_row_version=2,
            new_row_version=3,
            occurred_at=at,
            created_by=m["principal"].actor_id,
            created_at=at,
        ),
    )


@pytest.mark.pr204_requirements("PR204-DOM-02", "PR204-DB-01", "PR204-DB-05")
@pytest.mark.parametrize(
    "outcome,reason,allowed", OUTCOMES, ids=[reason or "SUCCEEDED" for _, reason, _ in OUTCOMES]
)
@pytest.mark.parametrize("certainty", ["NOT_SENT", "RESPONSE_RECEIVED", "MAY_HAVE_BEEN_SENT"])
def test_pg_complete_outcome_reason_certainty_matrix(
    outcome, reason, allowed, certainty, phase2_database_url, pr204_trace
):
    m = _material(phase2_database_url, "reserved")
    engine = m["engine"]
    before = _rows(engine)
    try:
        if certainty in allowed:
            with engine.begin() as connection:
                complete_outcome(connection, m, outcome, reason, certainty)
            after = _rows(engine)
            attempt = next(row for row in after[A] if row["execution_id"] == m["execution"])
            assert attempt["status"] == outcome and attempt["delivery_certainty"] == certainty
            assert attempt["failure_code"] == reason and attempt["row_version"] == 2
            assert len(after[Q]) == len(before[Q]) + 1
            assert len(after[V]) == len(before[V]) + 1
            rejected = None
        else:
            with pytest.raises(DBAPIError) as caught:
                with engine.begin() as connection:
                    complete_outcome(connection, m, outcome, reason, certainty)
            rejected = getattr(caught.value.orig, "sqlstate", None)
            assert rejected == "23514"
            assert _rows(engine) == before
        pr204_trace.record(
            outcome=outcome,
            reason=reason,
            certainty=certainty,
            expected_valid=certainty in allowed,
            rejected_sqlstate=rejected,
            before=before,
            after=_rows(engine),
            provider_calls=len(m["provider"].calls),
        )
    finally:
        engine.dispose()
