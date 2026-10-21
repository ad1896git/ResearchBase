from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from researchbase.application.phase2_identity import CloseProjectRole, Phase2IdentityService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import _normalize_database_error


def _setup():
    now = datetime(2026, 10, 20, tzinfo=UTC)
    principal = VerifiedPrincipal(uuid4(), "r1", "OS_UID", "501", "credential", now)
    command = CloseProjectRole(principal, uuid4(), uuid4(), "  scheduled expiry  ", uuid4())
    uow = MagicMock()
    uow.__enter__.return_value = uow
    repo = uow.phase2_identity
    repo.role_assignment_for_update.return_value = {
        "project_id": command.project_id,
        "actor_id": principal.actor_id,
        "effective_from": now - timedelta(days=1),
        "effective_until": None,
    }
    repo.database_time.side_effect = [now, now + timedelta(microseconds=1)]
    repo.close_role_assignment.return_value = True
    service = Phase2IdentityService(
        lambda: uow,
        nonce_issuer=MagicMock(),
        operator_policy=MagicMock(),
        credential_verifier=MagicMock(),
        subject_credential_verifier=MagicMock(),
        attestation_verifier=MagicMock(),
    )
    return service, command, uow, now


@pytest.mark.parametrize("scheduled", [False, True])
def test_closure_uses_database_time_or_normalized_requested_time(scheduled):
    service, command, uow, now = _setup()
    requested = (now + timedelta(days=1)).astimezone(timezone(timedelta(hours=5)))
    if scheduled:
        command = replace(command, effective_until=requested)
    else:
        assert command.effective_until is None
    with patch("researchbase.application.phase2_identity._owner_authorized", return_value=True):
        service.close_project_role(command)
    target = requested.astimezone(UTC) if scheduled else now
    repo = uow.phase2_identity
    repo.close_role_assignment.assert_called_once_with(command.role_assignment_id, target)
    event = repo.create_role_event.call_args.args[0]
    assert event["occurred_at"] == target
    assert event["occurred_at"].tzinfo is UTC
    assert event["reason"] == "scheduled expiry"
    uow.begin_serializable.assert_called_once_with()
    uow.commit.assert_called_once_with()
    assert [call[0] for call in repo.method_calls] == [
        "lock_project",
        "role_assignment_for_update",
        "owner_authorization_facts",
        "database_time",
        "close_role_assignment",
        "create_role_event",
        "database_time",
    ]


@pytest.mark.parametrize("value", [datetime(2026, 10, 21), "2026-10-21", 42])
def test_invalid_expiry_rejected_before_transaction(value):
    service, command, uow, _ = _setup()
    with pytest.raises(ResearchBaseError) as caught:
        service.close_project_role(replace(command, effective_until=value))
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
    uow.__enter__.assert_not_called()


@pytest.mark.parametrize("reason", ["  ", "bad\x00reason", "bad\ud800reason", "a" * 513, 42])
def test_invalid_reason_rejected_before_transaction(reason):
    service, command, uow, _ = _setup()
    with pytest.raises(ResearchBaseError) as caught:
        service.close_project_role(replace(command, reason=reason))
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
    uow.__enter__.assert_not_called()


@pytest.mark.parametrize("offset", [-timedelta(days=2), -timedelta(days=1), -timedelta(seconds=1)])
def test_nonpositive_interval_and_backdating_rejected(offset):
    service, command, uow, now = _setup()
    with patch("researchbase.application.phase2_identity._owner_authorized", return_value=True):
        with pytest.raises(ResearchBaseError) as caught:
            service.close_project_role(replace(command, effective_until=now + offset))
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
    uow.phase2_identity.close_role_assignment.assert_not_called()
    uow.phase2_identity.create_role_event.assert_not_called()
    uow.commit.assert_not_called()


def test_explicit_expiry_equal_to_post_lock_time_is_allowed():
    service, command, uow, now = _setup()
    with patch("researchbase.application.phase2_identity._owner_authorized", return_value=True):
        service.close_project_role(replace(command, effective_until=now))
    uow.phase2_identity.close_role_assignment.assert_called_once_with(
        command.role_assignment_id, now
    )


@pytest.mark.parametrize(
    ("state", "constraint", "expected"),
    [
        ("23P01", "ex_project_role_assignments_role_interval", ErrorCode.INVALID_STATE_TRANSITION),
        ("23505", "uq_project_role_assignments_open", ErrorCode.INVALID_STATE_TRANSITION),
        ("23505", "uq_project_role_events_assignment_request", ErrorCode.IDEMPOTENCY_CONFLICT),
    ],
)
def test_role_constraints_normalize_from_driver_metadata(state, constraint, expected):
    original = Exception("database constraint")
    original.sqlstate = state  # type: ignore[attr-defined]
    original.diag = SimpleNamespace(constraint_name=constraint)  # type: ignore[attr-defined]
    result = _normalize_database_error(DBAPIError(None, None, original))
    assert result is not None and result.code is expected
