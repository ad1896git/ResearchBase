"""Independent literal R2 and closed PR2-15 command contract checks."""

from dataclasses import FrozenInstanceError
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.application.decision import RecordDecisionCommand
from researchbase.domain.decision import (
    DecisionBasisReference,
    decision_basis_material,
    decision_content_material,
)
from researchbase.foundation.hashing import sha256_canonical_json


def test_literal_r2_golden_basis_and_content():
    basis = decision_basis_material(
        (
            DecisionBasisReference(
                "InternalReviewRecord",
                UUID(int=18),
                "e" * 64,
                0,
            ),
        )
    )
    assert basis == {
        "type": "DecisionRecordBasisSet",
        "material_version": 1,
        "basis": [
            {
                "target": {
                    "type": "InternalReviewRecord",
                    "id": str(UUID(int=18)),
                    "content_hash": "e" * 64,
                },
                "ordinal": 0,
            },
        ],
    }
    basis_hash = str(sha256_canonical_json(basis))
    assert basis_hash == "0c9c9d2a5d207ec7c425192e42e1023c66075ae52eb2da5e26b56360bc8e3af5"
    content = decision_content_material(
        UUID(int=16),
        "PUBLICATION",
        "Proceed?",
        "PROCEED",
        "Review complete.",
        UUID(int=19),
        basis_hash,
    )
    assert str(sha256_canonical_json(content)) == (
        "aa4f886f7b59baab737d7990700057fe7c2ac3751c9b546fd6f40bbab2c21cf3"
    )
    assert "decided_at" not in content
    assert content["supersedes_decision_id"] is None


def test_basis_requires_canonical_contiguous_order_and_no_duplicates():
    a = DecisionBasisReference("InternalReviewRecord", UUID(int=2), "a" * 64, 0)
    b = DecisionBasisReference("ScientificConclusionVersion", UUID(int=1), "b" * 64, 1)
    rows = decision_basis_material((b, a))["basis"]
    assert isinstance(rows, list)
    assert isinstance(rows[0], dict)
    target = rows[0]["target"]
    assert isinstance(target, dict)
    assert target["id"] == str(a.id)
    with pytest.raises(ValueError):
        decision_basis_material((a, a))
    with pytest.raises(ValueError):
        decision_basis_material(
            (DecisionBasisReference("ScientificConclusionVersion", UUID(int=1), "b" * 64, 0), a)
        )


def test_command_is_frozen_closed_and_normalizes_nfc():
    command = RecordDecisionCommand(
        UUID(int=1), UUID(int=2), UUID(int=3), "Cafe\u0301? ", "Evidence.\n"
    )
    assert command.question == "Caf\u00e9? "
    assert command.rationale == "Evidence.\n"
    assert command.decision_type == "INTERNAL_SCIENTIFIC_RELEASE"
    assert command.decision == "PROCEED"
    with pytest.raises(FrozenInstanceError):
        cast(Any, command).question = "Changed"
    with pytest.raises(TypeError):
        cast(Any, RecordDecisionCommand)(
            UUID(int=1), UUID(int=2), UUID(int=3), "Q", "R", actor_id=UUID(int=4)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("question", " "),
        ("rationale", "\ud800"),
        ("decision_type", "PUBLICATION"),
        ("decision", "REJECT"),
        ("id", "bad"),
    ],
)
def test_command_rejects_invalid_material(field, value):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    values: dict[str, Any] = dict(
        id=UUID(int=1),
        project_id=UUID(int=2),
        scientific_conclusion_version_id=UUID(int=3),
        question="Q",
        rationale="R",
    )
    values[field] = value
    with pytest.raises(ResearchBaseError) as error:
        RecordDecisionCommand(**values)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


def test_service_rejects_unverified_actor_before_opening_transaction():
    from researchbase.application.decision import DecisionService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service = DecisionService(
        lambda: pytest.fail("must authenticate before transaction"), None, None
    )
    with pytest.raises(ResearchBaseError) as error:
        service.record_decision(
            cast(Any, None), RecordDecisionCommand(UUID(int=1), UUID(int=2), UUID(int=3), "Q", "R")
        )
    assert error.value.code == ErrorCode.AUTHENTICATION_REQUIRED


@pytest.mark.parametrize("actor_type", ["HUMAN", "AGENT", "SERVICE"])
def test_decider_authority_does_not_invent_human_only_policy(actor_type):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from researchbase.application.decision import DecisionService
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    at = datetime(2026, 1, 1, tzinfo=UTC)
    principal = VerifiedPrincipal(UUID(int=4), "test", "MTLS_URI", "test:actor", "test", at)
    row = dict(
        actor_type=actor_type,
        retired_at=None,
        membership_status="ACTIVE",
        binding_status="ACTIVE",
        role="APPROVER",
        effective_from=at,
        effective_until=None,
        bound_at=at,
        revoked_at=None,
    )
    uow = SimpleNamespace(
        literature_search_plan=SimpleNamespace(
            lock_project=lambda project: None,
            authorize=lambda actor, project: [row],
            project_active=lambda project: True,
        ),
        source_version=SimpleNamespace(at=lambda: at),
    )
    credentials = SimpleNamespace(is_valid=lambda actor, clock: True)
    service = DecisionService(
        lambda: pytest.fail("authorization unit test has an explicit UoW"), credentials, None
    )
    assert service._authorize(uow, principal, UUID(int=5), frozenset({"OWNER", "APPROVER"})) == at


def test_decision_bounds_database_waits_before_request_coordination():
    from sqlalchemy.orm import Session

    from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository

    class RecordingSession:
        def __init__(self):
            self.statements: list[str] = []

        def execute(self, statement, parameters=None):
            self.statements.append(str(statement))

    session = RecordingSession()
    repository = SqlAlchemyDecisionRepository(cast(Session, session))
    repository.lock_request(UUID(int=7))
    assert session.statements[:2] == [
        "SET LOCAL lock_timeout = '10s'",
        "SET LOCAL statement_timeout = '30s'",
    ]
    assert "pg_advisory_xact_lock" in session.statements[2]
