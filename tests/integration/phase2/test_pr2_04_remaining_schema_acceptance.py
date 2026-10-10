"""Targeted remaining closed schema/FK contracts with valid full-TX controls."""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _provision
from tests.integration.phase2.test_pr2_04_schema_coverage import A, C, E, Q, R, V, _insert, _material, _reject, _rows

from researchbase.domain.literature_search_execution import SearchHit, SearchQueryRecord


def complete(connection, m, probe=None):
    rows = _rows(m["engine"])
    execution = next(row for row in rows[E] if row["id"] == m["execution"])
    attempt = next(row for row in rows[A] if row["execution_id"] == execution["id"])
    at = connection.scalar(text("SELECT clock_timestamp()"))
    query = SearchQueryRecord(uuid4(), execution["id"], attempt["id"], 0,
                              "normalization evidence", "provider-a", "1", at)
    query_row = dict(id=query.id, literature_search_execution_id=execution["id"],
        provider_attempt_id=attempt["id"], query_text=query.query_text, perspective=None,
        provider_id="provider-a", provider_version="1", ordinal=0, executed_at=at,
        query_hash=query.query_hash, hash_scheme="other" if probe == "query_hash_scheme" else "sha256-cjson-v1",
        created_by=m["principal"].actor_id, created_at=at)
    _insert(connection, Q, query_row)
    retryable = probe in {"retry_negative", "retry_overflow", "retry_positive_control"}
    if not retryable:
        hit = SearchHit("hit", "Paper", None, None, None)
        _insert(connection, R, dict(id=uuid4(), search_query_record_id=query.id, rank=0,
            external_identifier=hit.external_identifier, title=hit.title, url=None, snippet=None,
            provider_score=None, retrieved_at=at, content_hash=hit.result_hash(query.query_hash, 0),
            hash_scheme="other" if probe == "result_hash_scheme" else "sha256-cjson-v1",
            created_by=m["principal"].actor_id, created_at=at))
    values = dict(id=attempt["id"], status="RETRYABLE_FAILURE" if retryable else "SUCCEEDED",
        query=query.id, at=at, returned=at, certainty="RESPONSE_RECEIVED",
        reason="PROVIDER_TRANSIENT" if retryable else None, count=0 if retryable else 1,
        retrieved=None if retryable else at,
        retry=1 if probe in {"retry_positive_control", "retry_on_success"} else None)
    if probe == "return_before_invocation":
        values["returned"] = at - timedelta(microseconds=1)
    if probe == "retry_negative":
        values["retry"] = -1
    if probe == "retry_overflow":
        values["retry"] = 2147483648
    connection.execute(text(f"UPDATE {A} SET status=:status,query_record_id=:query,invoked_at=:at,"
        "returned_at=:returned,completed_at=:at,delivery_certainty=:certainty,failure_code=:reason,"
        "result_count=:count,retrieved_at=:retrieved,retry_after_seconds=:retry,warning_codes='[]'::jsonb,"
        "row_version=2 WHERE id=:id"), values)
    connection.execute(text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"), {"id": execution["id"]})
    event = dict(id=uuid4(), execution_id=execution["id"], sequence=2,
        kind="OUTCOME_RECORDED", attempt_id=attempt["id"], prior_status="RUNNING", new_status="RUNNING",
        prior_row_version=2, new_row_version=3, occurred_at=at, created_by=m["principal"].actor_id, created_at=at)
    if probe == "event_unknown_kind":
        event["kind"] = "BOGUS"
    if probe == "event_attempt_missing":
        event["attempt_id"] = None
    if probe == "event_cancel_has_attempt":
        event["kind"] = "CANCEL_REQUESTED"
    if probe == "event_negative_sequence":
        event["sequence"] = -1
    if probe == "event_zero_version":
        event["new_row_version"] = 0
    if probe == "event_missing_actor":
        event["created_by"] = uuid4()
    _insert(connection, V, event)


def positive_control(engine, call):
    before = _rows(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            call(connection)
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        finally:
            transaction.rollback()
    assert _rows(engine) == before


@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")
@pytest.mark.parametrize("probe,sqlstate", [
    ("query_hash_scheme", "23514"), ("result_hash_scheme", "23514"),
    ("return_before_invocation", "23514"), ("retry_negative", "23514"),
    ("retry_overflow", "22003"), ("retry_on_success", "23514"),
    ("event_unknown_kind", "23514"), ("event_attempt_missing", "23514"),
    ("event_cancel_has_attempt", "23514"), ("event_negative_sequence", "P17D5"),
    ("event_zero_version", "P17D5"), ("event_missing_actor", "23503"),
])
def test_pg_remaining_complete_tuple_guard(probe, sqlstate, phase2_database_url, pr204_trace):
    m = _material(phase2_database_url, "reserved")
    engine = m["engine"]
    try:
        control = "retry_positive_control" if probe in {"retry_negative", "retry_overflow"} else None
        positive_control(engine, lambda c: complete(c, m, control))
        _reject(engine, lambda c: complete(c, m, probe), sqlstate, pr204_trace, case=probe)
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01")
@pytest.mark.parametrize("probe", ["valid_foreign_project", "actor_attribution", "missing_actor"])
def test_pg_receipt_typed_scope_and_attribution(probe, phase2_database_url, pr204_trace):
    m = _material(phase2_database_url, "planned")
    engine = m["engine"]
    try:
        row = {**_rows(engine)[C][0], "id": uuid4(), "request_id": uuid4()}
        positive_control(engine, lambda c: _insert(c, C, row))
        identity, _, _ = _identity_service(phase2_database_url)
        expected = "23503"
        if probe == "valid_foreign_project":
            row["project_id"] = identity.create_project_with_owner(m["principal"], name="foreign receipt scope", request_id=uuid4())
        elif probe == "actor_attribution":
            other, _ = _provision(identity, m["principal"])
            row["created_by"] = other.actor_id
            expected = "23514"
        else:
            absent = uuid4()
            row["created_by"] = row["actor_id"] = absent
        _reject(engine, lambda c: _insert(c, C, row), expected, pr204_trace, case=probe)
    finally:
        engine.dispose()
