"""Finite Issue disposition policy and closed normalized command material."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from itertools import product
from uuid import uuid4

import pytest

from researchbase.application.internal_review import (
    IssueEventReadback,
    RecordIssueDispositionCommand,
)
from researchbase.domain.internal_review import disposition_policy
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command():
    return RecordIssueDispositionCommand(
        uuid4(), uuid4(), uuid4(), "ADDRESSED", uuid4(), uuid4(), "Attested"
    )


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "project_id",
        "review_issue_id",
        "revision_action_id",
        "re_review_record_id",
        "decision_id",
    ],
)
@pytest.mark.parametrize("bad", [True, 1, "uuid", "00000000-0000-0000-0000-000000000001"])
def test_uuid_fields_are_strict(field, bad):
    with pytest.raises(ResearchBaseError) as caught:
        replace(command(), **{field: bad})
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("bad", [None, True, 1, "", " ", "\n\t", "x" * 16001, "\ud800"])
def test_rationale_rejects_blank_oversize_nontext_and_invalid_unicode(bad):
    with pytest.raises(ResearchBaseError) as caught:
        replace(command(), rationale=bad)
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


def test_nfc_normalization_boundary_and_extra_rejection():
    assert replace(command(), rationale="e\u0301").rationale == "é"
    assert len(replace(command(), rationale="é" * 16000).rationale) == 16000
    with pytest.raises(TypeError):
        RecordIssueDispositionCommand(**{**asdict(command()), "actor_id": uuid4()})


@pytest.mark.parametrize("bad", [None, True, 1, "OPEN", "addressed"])
def test_finite_disposition_enum(bad):
    with pytest.raises(ResearchBaseError):
        replace(command(), disposition=bad)


@pytest.mark.parametrize(
    "disposition,severity,role,opener,action,decision",
    list(
        product(
            ["ADDRESSED", "DISMISSED"],
            ["INFO", "MINOR", "MAJOR", "BLOCKING"],
            ["OWNER", "REVIEWER", "RESEARCHER", "VIEWER", "APPROVER"],
            [False, True],
            [
                "NEW_EXPERIMENT",
                "ANALYSIS_CHANGE",
                "CLAIM_CHANGE",
                "CONCLUSION_CHANGE",
                "SOURCE_CHANGE",
                "NO_CHANGE",
                "MANUSCRIPT_CHANGE",
            ],
            [None, "REQUIRE_CHANGE", "ACCEPT_NO_CHANGE", "PROCEED"],
        )
    ),
)
def test_all_finite_transition_authority_and_basis_tuples(
    disposition, severity, role, opener, action, decision
):
    if disposition == "DISMISSED":
        expected = role == "OWNER" and action == "NO_CHANGE" and decision == "ACCEPT_NO_CHANGE"
    else:
        expected = (
            (role == "OWNER" or role == "REVIEWER" and opener)
            and action != "NO_CHANGE"
            and (decision == "REQUIRE_CHANGE" or decision is None and severity != "BLOCKING")
        )
    assert (
        disposition_policy(
            disposition, severity, role, opener=opener, action_type=action, decision=decision
        )
        == expected
    )


def test_root_and_terminal_readback_shapes():
    root = IssueEventReadback(
        uuid4(), uuid4(), uuid4(), None, "OPEN", datetime.now(UTC), None, None, None, None
    )
    with pytest.raises(ValueError):
        replace(root, rationale="Late basis")
    terminal = replace(
        root,
        prior_status="OPEN",
        new_status="ADDRESSED",
        revision_action_id=uuid4(),
        re_review_record_id=uuid4(),
        rationale="Attested",
    )
    with pytest.raises(ValueError):
        replace(terminal, new_status="DISMISSED")
    assert replace(terminal, new_status="DISMISSED", decision_id=uuid4()).decision_id is not None


def readbacks():
    from researchbase.application.internal_review import (
        IssueDispositionReadback,
        IssueHistoryReadback,
    )

    now = datetime.now(UTC)
    ids = [uuid4() for _ in range(7)]
    terminal = IssueDispositionReadback(
        ids[0],
        ids[1],
        ids[2],
        ids[3],
        ids[4],
        ids[5],
        None,
        "OPEN",
        "ADDRESSED",
        "Attested",
        now,
        "a" * 64,
        "b" * 64,
        None,
        "VALID",
        "VALID",
        False,
    )
    root = IssueEventReadback(uuid4(), ids[2], ids[3], None, "OPEN", now, None, None, None, None)
    history = IssueHistoryReadback(
        ids[1],
        ids[2],
        ids[6],
        "MINOR",
        "OTHER",
        "Concern",
        "OPEN",
        now,
        uuid4(),
        None,
        None,
        "c" * 64,
        "VALID",
        (root,),
        None,
    )
    return terminal, history, root


@pytest.mark.parametrize("which", [0, 1, 2])
def test_every_readback_field_rejects_wrong_type_and_extras(which):
    from dataclasses import fields

    value = readbacks()[which]
    for field in fields(value):
        with pytest.raises(ValueError):
            replace(value, **{field.name: object()})
    with pytest.raises(TypeError):
        type(value)(**{**asdict(value), "caller_actor": uuid4()})


def test_readback_hash_time_target_and_event_projection_constraints():
    terminal, history, root = readbacks()
    for field, bad in [
        ("action_content_hash", "z" * 64),
        ("re_review_content_hash", "a" * 63),
        ("occurred_at", datetime.now()),
        ("new_status", "OPEN"),
        ("has_superseding_action", 1),
    ]:
        with pytest.raises(ValueError):
            replace(terminal, **{field: bad})
    for changes in (
        {"claim_version_id": None},
        {"manuscript_version_id": uuid4()},
        {"events": ()},
        {"status": "ADDRESSED"},
        {"target_validity": "UNKNOWN"},
        {"severity": "UNKNOWN"},
    ):
        with pytest.raises(ValueError):
            replace(history, **changes)


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT"])
@pytest.mark.parametrize("role", ["OWNER", "REVIEWER"])
@pytest.mark.parametrize("dismiss", [False, True])
def test_human_only_disposer_policy_uses_verified_authority_not_caller_assertions(
    actor_type, role, dismiss
):
    from unittest.mock import Mock

    from researchbase.application.internal_review import InternalReviewService
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    now = datetime.now(UTC)
    principal = VerifiedPrincipal(uuid4(), "test", "OS_UID", "1", "credential", now)
    uow = Mock()
    uow.source_version.at.return_value = now
    uow.internal_review.authority.return_value = [
        {
            "actor_type": actor_type,
            "role": role,
            "retired_at": None,
            "membership_status": "ACTIVE",
            "binding_status": "ACTIVE",
            "effective_from": now,
            "effective_until": None,
            "bound_at": now,
            "revoked_at": None,
            "project_status": "ACTIVE",
        }
    ]
    service = object.__new__(InternalReviewService)
    service._credentials = Mock()
    service._credentials.is_valid.return_value = True
    project = uuid4()
    # Same verified Application boundary admits historical reads by either type.
    assert service._disposition_authorize(uow, principal, project) == now
    allowed = actor_type == "HUMAN" and (role == "OWNER" or not dismiss)
    if allowed:
        assert (
            service._disposition_authorize(
                uow, principal, project, write=True, opener=principal.actor_id, dismiss=dismiss
            )
            == now
        )
    else:
        with pytest.raises(ResearchBaseError) as caught:
            service._disposition_authorize(
                uow, principal, project, write=True, opener=principal.actor_id, dismiss=dismiss
            )
        assert caught.value.code == ErrorCode.FORBIDDEN
