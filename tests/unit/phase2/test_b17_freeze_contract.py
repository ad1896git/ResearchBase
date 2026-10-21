"""B17 closed command, saved-result compatibility and existing error categories."""

from dataclasses import FrozenInstanceError, asdict, replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.prepared_submission import FreezePreparedSubmissionCommand
from researchbase.domain.approval import PreparedSubmissionFreezeResult, decode_consumption_result
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command():
    return FreezePreparedSubmissionCommand(
        uuid4(), uuid4(), uuid4(), uuid4(), "a" * 64, (UUID(int=2), UUID(int=1))
    )


def test_normalized_closed_frozen_command():
    value = command()
    assert value.checked_review_ids == (UUID(int=1), UUID(int=2))
    with pytest.raises(FrozenInstanceError):
        cast(Any, value).grant_id = uuid4()
    with pytest.raises(TypeError):
        cast(Any, FreezePreparedSubmissionCommand)(**(asdict(value) | {"actor_id": uuid4()}))
    for field in asdict(value):
        missing = asdict(value)
        del missing[field]
        with pytest.raises(TypeError):
            FreezePreparedSubmissionCommand(**missing)


@pytest.mark.parametrize("field", ["command_key", "project_id", "grant_id", "result_id"])
@pytest.mark.parametrize("value", [None, True, 1, "00000000-0000-0000-0000-000000000001"])
def test_exact_uuid_types(field, value):
    with pytest.raises(ResearchBaseError) as exc:
        replace(command(), **{field: value})
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "value", [None, 1, True, "A" * 64, "a" * 63, "a" * 65, "g" * 64, "a" * 64 + "\n"]
)
def test_digest_is_strict(value):
    with pytest.raises(ResearchBaseError) as exc:
        replace(command(), expected_package_manifest_hash=value)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "value",
    [(), [], (True,), ("id",), (UUID(int=1), UUID(int=1)), tuple(UUID(int=i) for i in range(101))],
)
def test_review_set_is_bounded_and_duplicate_free(value):
    with pytest.raises(ResearchBaseError) as exc:
        replace(command(), checked_review_ids=value)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "name,key",
    [
        ("RECORD_INTERNAL_SCIENTIFIC_RELEASE", "scientific_conclusion_version_id"),
        ("TRANSITION_PUBLICATION_READY", "publication_id"),
        ("FREEZE_PREPARED_SUBMISSION", "prepared_submission_version_id"),
    ],
)
def test_three_concrete_v1_results_keep_old_saved_versions(name, key):
    identity, receipt = uuid4(), uuid4()
    data = {"command": name, key: str(identity), "consumption_id": str(receipt)}
    saved = decode_consumption_result(1, data)
    assert saved.command == name and saved.consumption_id == receipt
    assert getattr(saved, key) == identity
    if name == "FREEZE_PREPARED_SUBMISSION":
        assert type(saved) is PreparedSubmissionFreezeResult
    for version in (True, 0, 2):
        with pytest.raises(ValueError):
            decode_consumption_result(version, data)
    for changed in (
        data | {"status": "FROZEN"},
        data | {"publication_id": str(uuid4()), "scientific_conclusion_version_id": str(uuid4())},
        data | {"consumption_id": str(receipt).upper()},
    ):
        if changed == data:
            continue
        with pytest.raises(ValueError):
            decode_consumption_result(1, changed)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
    ],
)
def test_pinned_existing_error_mapping(name, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    code = ErrorCode(name)
    assert _STATUS[code] == http and CLI_EXIT_CODES[code] == cli


@pytest.mark.parametrize("constraint", ["uq_b17_frozen_publication", "uq_b17_package_consumption"])
def test_competing_package_constraints_do_not_become_retries(constraint):
    from types import SimpleNamespace

    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _approval_database_error

    class Failure(Exception):
        sqlstate = "23505"
        diag = SimpleNamespace(constraint_name=constraint)

    error = _approval_database_error(DBAPIError("sql", {}, Failure(), False), strict=True)
    assert error.code == ErrorCode.CONCURRENT_MODIFICATION and not error.details
