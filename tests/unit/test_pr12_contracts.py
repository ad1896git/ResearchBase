from __future__ import annotations

from dataclasses import fields
from typing import Any, cast

from researchbase.application.dto import (
    ClaimReadModel,
    ClaimVersionReadModel,
    EvidenceRelationReadModel,
)
from researchbase.application.ports import ClaimRepository, UnitOfWork
from researchbase.persistence.repositories import SqlAlchemyClaimRepository


def test_claim_read_models_are_orm_free_and_immutable() -> None:
    for model in (ClaimReadModel, ClaimVersionReadModel, EvidenceRelationReadModel):
        assert cast(Any, model).__dataclass_params__.frozen is True
        assert all(field.name != "session" for field in fields(model))


def test_claim_repository_is_narrow_and_non_committing() -> None:
    required = {
        "add",
        "add_version",
        "get",
        "get_for_update",
        "get_version",
        "get_version_for_update",
        "get_current_version",
        "list_history",
        "max_version_number",
        "update_current_version",
        "update_version",
        "add_evidence",
        "remove_evidence",
        "get_evidence",
        "list_evidence",
    }
    public_protocol = {name for name in dir(ClaimRepository) if not name.startswith("_")}
    public_adapter = {name for name in dir(SqlAlchemyClaimRepository) if not name.startswith("_")}

    assert required <= public_protocol
    assert required <= public_adapter
    assert not {"commit", "save", "delete"} & public_protocol
    assert not {"commit", "save", "delete"} & public_adapter
    assert "claims" in UnitOfWork.__annotations__
