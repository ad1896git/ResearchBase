"""Frozen pack §13.2: closed planned-input integer slots are enforced on direct SQL."""

from copy import deepcopy
from unicodedata import normalize
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


@pytest.mark.parametrize(
    "field",
    [
        "max_results",
        "max_provider_attempts",
        "timeout_seconds",
        "execution_budget_seconds",
    ],
)
@pytest.mark.parametrize(
    "value", ["1", None, True, 1.5], ids=["string", "null", "boolean", "fraction"]
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_pg_direct_context_rejects_noninteger_options_without_durable_effects(
    phase2_database_url, field, value, pr204_trace: FactRecorder
):
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        before = _rows(engine)
        row = deepcopy(before[E][0])
        row.update(id=uuid4(), idempotency_key=uuid4())
        row["execution_context"][field] = value
        error = None
        try:
            with engine.begin() as connection:
                _execution_with_created_event(connection, row, before[V][0])
        except DBAPIError as caught:
            error = caught
        after = _rows(engine)
        sqlstate = getattr(error.orig, "sqlstate", None) if error is not None else None
        pr204_trace.record(
            field=field,
            supplied_value=value,
            sqlstate=sqlstate,
            before_counts={t: len(r) for t, r in before.items()},
            after_counts={t: len(r) for t, r in after.items()},
            durable_rows_unchanged=before == after,
            provider_calls=len(material["provider"].calls),
        )
        assert error is not None, f"DB accepted noninteger context.{field}"
        assert sqlstate in {"P17D5", "23514", "22P02"}
        assert after == before
        assert material["provider"].calls == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("field", ["provider_id", "provider_version"])
@pytest.mark.parametrize(
    "value",
    ["cafe\u0301", "\t\n", "bad\x01identifier"],
    ids=["non_nfc", "blank_unicode_space", "control_character"],
)
@pytest.mark.pr204_requirements("PR204-DB-01")
def test_pg_direct_context_identifiers_enforce_frozen_normalized_nonblank_text(
    phase2_database_url, field, value, pr204_trace: FactRecorder
):
    """Frozen pack §§8/13: NFC, nonblank, bounded; no provider control ban."""
    material = _material(phase2_database_url, "planned")
    engine = material["engine"]
    try:
        before = _rows(engine)
        row = deepcopy(before[E][0])
        row.update(id=uuid4(), idempotency_key=uuid4())
        row["execution_context"][field] = value
        error = None
        try:
            with engine.begin() as connection:
                _execution_with_created_event(connection, row, before[V][0])
        except DBAPIError as caught:
            error = caught
        after = _rows(engine)
        sqlstate = getattr(error.orig, "sqlstate", None) if error is not None else None
        pr204_trace.record(
            field=field,
            supplied_value=value,
            sqlstate=sqlstate,
            durable_rows_unchanged=before == after,
            before_counts={t: len(r) for t, r in before.items()},
            after_counts={t: len(r) for t, r in after.items()},
        )
        if value == "bad\x01identifier":
            assert normalize("NFC", value) == value and value.strip() and 1 <= len(value) <= 128
            assert error is None and sqlstate is None
            admitted = next(r for r in after[E] if r["id"] == row["id"])
            assert admitted["execution_context"] == row["execution_context"]
            assert len(after[E]) == len(before[E]) + 1
            assert len(after[V]) == len(before[V]) + 1
            assert all(after[t] == before[t] for t in before if t not in {E, V})
        else:
            assert error is not None, f"DB accepted invalid identifier context.{field}"
            assert sqlstate in {"P17D5", "23514"}
            assert after == before
        assert material["provider"].calls == []
    finally:
        engine.dispose()
