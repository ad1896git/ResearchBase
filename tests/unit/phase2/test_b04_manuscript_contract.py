"""Closed B04 DTOs and pure placement admission limits."""

from dataclasses import replace
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.application.manuscript_freeze import (
    FreezeManuscriptCommand,
    GetManuscriptVersionQuery,
)
from researchbase.domain.manuscript import (
    ManuscriptPlacement,
    ManuscriptReference,
    manuscript_placement_material,
    text_value,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

REF = ManuscriptReference("ClaimVersion", UUID(int=1), "a" * 64)
PLACEMENT = ManuscriptPlacement(REF, "RESULTS", "PARAGRAPH", "p1", "SUPPORTED", 0)


@pytest.mark.parametrize("field", ["project_id", "publication_id", "manuscript_version_id"])
@pytest.mark.parametrize("value", ["bad", True, 1, None])
def test_typed_ids(field, value):
    args = dict(
        project_id=UUID(int=1), publication_id=UUID(int=2), manuscript_version_id=UUID(int=3)
    )
    args[field] = value
    with pytest.raises(ResearchBaseError) as error:
        GetManuscriptVersionQuery(**args)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("bad", ["A" * 64, "a" * 63, "g" * 64, "a" * 64 + "\n", True, None])
def test_expected_digest(bad):
    with pytest.raises(ResearchBaseError):
        FreezeManuscriptCommand(UUID(int=1), UUID(int=2), UUID(int=3), bad, "b" * 64)


def test_closed_and_immutable_dto():
    with pytest.raises(TypeError):
        cast(Any, GetManuscriptVersionQuery)(
            UUID(int=1), UUID(int=2), UUID(int=3), actor_id=UUID(int=4)
        )
    query = GetManuscriptVersionQuery(UUID(int=1), UUID(int=2), UUID(int=3))
    with pytest.raises(AttributeError):
        cast(Any, query).project_id = UUID(int=5)


@pytest.mark.parametrize("bad", ["", " ", "a" * 2001, "Cafe\u0301", "\ud800"])
def test_unicode_and_bounds(bad):
    with pytest.raises((ValueError, UnicodeError)):
        text_value(bad)


@pytest.mark.parametrize(
    "change",
    [
        {"ordinal": True},
        {"ordinal": -1},
        {"ordinal": 2147483648},
        {"annotation": "TRUTH"},
        {"locator_kind": "UNKNOWN"},
    ],
)
def test_closed_placement(change):
    with pytest.raises(ValueError):
        replace(PLACEMENT, **change)


def test_gap_duplicate_and_cap():
    for items in [(PLACEMENT, PLACEMENT), (replace(PLACEMENT, ordinal=1),)]:
        with pytest.raises(ValueError):
            manuscript_placement_material(items)
    items = tuple(replace(PLACEMENT, ordinal=i) for i in range(10000))
    assert len(cast(list, manuscript_placement_material(items)["claim_placements"])) == 10000
    with pytest.raises(ValueError):
        manuscript_placement_material(items + (replace(PLACEMENT, ordinal=10000),))


@pytest.mark.parametrize(
    "state,code",
    [
        ("P04M1", "IMMUTABLE_RECORD"),
        ("P04M2", "INVALID_STATE_TRANSITION"),
        ("P04M3", "PROVENANCE_CLOSURE_VIOLATION"),
        ("23503", "REFERENTIAL_INTEGRITY_ERROR"),
        ("23514", "VALIDATION_ERROR"),
        ("23502", "VALIDATION_ERROR"),
        ("23505", "CONCURRENT_MODIFICATION"),
        ("40001", "CONCURRENT_MODIFICATION"),
        ("40P01", "CONCURRENT_MODIFICATION"),
        ("55P03", "CONCURRENT_MODIFICATION"),
        ("57014", "CONCURRENT_MODIFICATION"),
    ],
)
def test_scoped_database_errors_retry_only_serialization_and_deadlock(state, code):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _manuscript_freeze_database_error

    class DriverError(Exception):
        sqlstate = state

    error = _manuscript_freeze_database_error(DBAPIError("test", {}, DriverError()))
    assert error.code.value == code
    assert error.details is not None
    assert error.details["retryable_b04"] == (state in {"40001", "40P01"})


def test_connection_timeouts_are_opt_in_for_b04_writes(monkeypatch):
    from researchbase.persistence import database

    calls = []

    def engine(url, **options):
        calls.append(options)
        return None

    monkeypatch.setattr(database, "create_engine", engine)
    database.create_database_engine("postgresql+psycopg://unused")
    database.create_database_engine("postgresql+psycopg://unused", b04_write_timeouts=True)
    assert calls[0]["connect_args"] == {}
    assert calls[1]["connect_args"] == {
        "options": "-c lock_timeout=10000 -c statement_timeout=30000"
    }
