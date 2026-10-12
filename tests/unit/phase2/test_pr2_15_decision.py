"""Independent literal R2 and closed PR2-15 command contract checks."""

from dataclasses import FrozenInstanceError
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
    assert decision_basis_material((b, a))["basis"][0]["target"]["id"] == str(a.id)
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
        command.question = "Changed"
    with pytest.raises(TypeError):
        RecordDecisionCommand(UUID(int=1), UUID(int=2), UUID(int=3), "Q", "R", actor_id=UUID(int=4))


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

    values = dict(
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
            None, RecordDecisionCommand(UUID(int=1), UUID(int=2), UUID(int=3), "Q", "R")
        )
    assert error.value.code == ErrorCode.AUTHENTICATION_REQUIRED
