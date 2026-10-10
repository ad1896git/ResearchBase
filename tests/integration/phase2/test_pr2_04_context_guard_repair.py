"""Frozen pack §§8/13.2: direct-SQL context types, bounds and identifier text."""

from copy import deepcopy
from uuid import uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy.exc import DBAPIError
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    E,
    V,
    _execution_with_created_event,
    _material,
    _rows,
)

LIMITS = [
    ("max_results", 100, 20),
    ("max_provider_attempts", 3, 2),
    ("timeout_seconds", 30, 10),
    ("execution_budget_seconds", 600, 120),
]


def _observe_context(phase2_database_url, pr204_trace, changes, accepted):
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        before = _rows(engine)
        row = deepcopy(before[E][0])
        row.update(id=uuid4(), idempotency_key=uuid4())
        row["execution_context"].update(changes)
        caught = None
        try:
            with engine.begin() as connection:
                _execution_with_created_event(connection, row, before[V][0])
        except DBAPIError as error:
            caught = error
        after = _rows(engine)
        sqlstate = caught.orig.sqlstate if caught is not None else None
        pr204_trace.record(
            supplied_context_changes=changes,
            expected_acceptance=accepted,
            actual_sqlstate=sqlstate,
            durable_rows_unchanged=after == before,
            before_counts={t: len(rows) for t, rows in before.items()},
            after_counts={t: len(rows) for t, rows in after.items()},
            provider_calls=len(material["provider"].calls),
        )
        if accepted:
            assert caught is None
            admitted = next(item for item in after[E] if item["id"] == row["id"])
            assert admitted["execution_context"] == row["execution_context"]
            assert len(after[E]) == len(before[E]) + 1
            assert len(after[V]) == len(before[V]) + 1
            assert all(after[t] == before[t] for t in before if t not in {E, V})
        else:
            assert caught is not None
            assert sqlstate == "P17D5"
            assert after == before
        assert material["provider"].calls == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("field,maximum,ordinary", LIMITS)
@pytest.mark.parametrize("boundary", ["minimum", "maximum", "ordinary"])
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_context_integer_boundaries(
    phase2_database_url, pr204_trace: FactRecorder, field, maximum, ordinary, boundary
):
    value = {"minimum": 1, "maximum": maximum, "ordinary": ordinary}[boundary]
    _observe_context(phase2_database_url, pr204_trace, {field: value}, True)


@pytest.mark.parametrize("field,maximum,ordinary", LIMITS)
@pytest.mark.parametrize("shape", ["object", "array", "decimal", "below", "above", "huge"])
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_context_integer_shapes_reject_atomically(
    phase2_database_url, pr204_trace: FactRecorder, field, maximum, ordinary, shape
):
    value = {
        "object": {"value": 1},
        "array": [1],
        "decimal": 1.0,
        "below": 0,
        "above": maximum + 1,
        "huge": 10**40,
    }[shape]
    _observe_context(phase2_database_url, pr204_trace, {field: value}, False)


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_context_optional_perspective_null_is_preserved(phase2_database_url, pr204_trace):
    _observe_context(
        phase2_database_url,
        pr204_trace,
        {"queries": [{"query_type": "TEXT", "query_text": "normalization evidence", "perspective": None}]},
        True,
    )


@pytest.mark.parametrize("field", ["provider_id", "provider_version"])
@pytest.mark.parametrize(
    "value,accepted",
    [
        ("caf\u00e9", True),
        ("a" * 128, True),
        ("\u200b", True),
        ("  provider  ", True),
        ("", False),
        ("a" * 129, False),
        ("\u00a0\u2003", False),
        ("\u001c", False),
    ],
    ids=["nfc", "max_length", "non_whitespace_format", "untrimmed", "empty", "too_long", "unicode_blank", "python_separator_blank"],
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_context_provider_identifier_frozen_text(
    phase2_database_url, pr204_trace: FactRecorder, field, value, accepted
):
    _observe_context(phase2_database_url, pr204_trace, {field: value}, accepted)
