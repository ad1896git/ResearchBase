"""Closed READY inputs, unchanged R3 material and concrete saved v1 result."""

from dataclasses import FrozenInstanceError, fields, replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.publication import (
    GetPublicationReadyTransitionQuery,
    TransitionPublicationReadyCommand,
)
from researchbase.domain.approval import PublicationReadyResult, decode_consumption_result
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.unit.phase2.test_b13_grant_contract import (
    material,
    test_independent_r3_golden_vectors,
    test_pinned_error_pairs,
)

_SHARED = (test_independent_r3_golden_vectors, test_pinned_error_pairs)


def command():
    return TransitionPublicationReadyCommand(uuid4(), uuid4(), uuid4(), uuid4(), (uuid4(),))


def test_closed_frozen_required_inputs():
    cmd = command()
    assert {f.name for f in fields(cmd)} == {
        "command_key",
        "project_id",
        "grant_id",
        "result_id",
        "checked_review_ids",
    }
    assert not hasattr(cmd, "__dict__")
    with pytest.raises(FrozenInstanceError):
        cast(Any, cmd).result_id = uuid4()
    with pytest.raises(TypeError):
        cast(Any, TransitionPublicationReadyCommand)(
            **{f.name: getattr(cmd, f.name) for f in fields(cmd)} | {"actor_id": uuid4()}
        )
    for missing in fields(cmd):
        with pytest.raises(TypeError):
            cast(Any, TransitionPublicationReadyCommand)(
                **{f.name: getattr(cmd, f.name) for f in fields(cmd) if f != missing}
            )


@pytest.mark.parametrize("name", ["command_key", "project_id", "grant_id", "result_id"])
@pytest.mark.parametrize("value", [None, 1, True, "00000000-0000-0000-0000-000000000001"])
def test_uuid_types_are_strict(name, value):
    with pytest.raises(ResearchBaseError) as error:
        replace(command(), **{name: value})
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "value",
    [(), (UUID(int=1),) * 2, [UUID(int=1)], (True,), tuple(UUID(int=i) for i in range(101))],
)
def test_closed_bounded_review_set(value):
    with pytest.raises(ResearchBaseError):
        replace(command(), checked_review_ids=cast(Any, value))


@pytest.mark.parametrize("count", [1, 100])
def test_canonical_review_order_and_explicit_null(count):
    ids = tuple(UUID(int=i) for i in reversed(range(count)))
    cmd = replace(command(), checked_review_ids=ids)
    assert cmd.checked_review_ids == tuple(sorted(ids, key=str))
    payload = material(checked_review_ids=ids)
    assert payload["expected_package_manifest_hash"] is None
    assert payload["command"] == "TRANSITION_PUBLICATION_READY"
    assert material(checked_review_ids=tuple(reversed(ids))) == payload


def test_exact_query_and_saved_result():
    cmd = command()
    assert (
        GetPublicationReadyTransitionQuery(cmd.project_id, cmd.grant_id).consumption_id
        == cmd.grant_id
    )
    with pytest.raises(ResearchBaseError):
        GetPublicationReadyTransitionQuery(cast(Any, str(cmd.project_id)), cmd.grant_id)
    value = dict(
        command="TRANSITION_PUBLICATION_READY",
        publication_id=str(cmd.result_id),
        consumption_id=str(cmd.grant_id),
    )
    result = decode_consumption_result(1, value)
    assert result == PublicationReadyResult(cmd.result_id, cmd.grant_id)
    with pytest.raises(ValueError):
        decode_consumption_result(True, value)
    for extra in (
        {"status": "READY"},
        {"publication_id": str(cmd.result_id).upper()},
        {"version": 1},
    ):
        with pytest.raises(ValueError):
            decode_consumption_result(1, value | extra)


@pytest.mark.parametrize("state", ["XX000", "23514", "08S01"])
def test_unknown_database_failure_is_unexpected_sanitized_and_not_retryable(state):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _approval_database_error

    class DriverFailure(Exception):
        sqlstate: str

    original = DriverFailure("immutable SYNTHETIC_SECRET sql credential CAS/path")
    original.sqlstate = state
    with pytest.raises(RuntimeError) as caught:
        _approval_database_error(DBAPIError("SYNTHETIC_SECRET", None, original), strict=True)
    assert "SYNTHETIC_SECRET" not in str(caught.value)
    assert "immutable" not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "state,code",
    [
        ("P17F2", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P14I1", ErrorCode.IMMUTABLE_RECORD),
        ("23503", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
    ],
)
def test_named_ready_database_errors_keep_pinned_categories(state, code):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _approval_database_error

    class DriverFailure(Exception):
        sqlstate: str

    original = DriverFailure("SYNTHETIC_SECRET")
    original.sqlstate = state
    error = _approval_database_error(DBAPIError("secret", None, original), strict=True)
    assert error.code == code and error.details is None
