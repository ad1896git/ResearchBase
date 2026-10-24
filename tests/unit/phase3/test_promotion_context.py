"""Promotion request boundaries admit only the two approved target families."""

from dataclasses import replace
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.context_contracts import PromotionContextRequest
from researchbase.agent_runtime.application.promotion_context import PromotionContextService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def test_closed_targets_and_revision():
    request = PromotionContextRequest(
        project_id=UUID(int=1),
        task_id=UUID(int=2),
        candidate_artifact_version_id=UUID(int=3),
        candidate_content_hash="a" * 64,
        expected_task_row_version=1,
        target_type="HYPOTHESIS_VERSION",
        canonical_basis=(),
    )
    for changes in (
        {"target_type": "CLAIM_VERSION"},
        {"expected_task_row_version": 0},
        {"candidate_content_hash": "bad"},
        {"canonical_basis": []},
    ):
        with pytest.raises((ValueError, TypeError)):
            replace(request, **changes)


def test_invalid_public_request_never_opens_uow():
    def forbidden():
        raise AssertionError("unexpected UoW")

    with pytest.raises(ResearchBaseError) as caught:
        PromotionContextService(forbidden, object()).validate_promotion_context(
            cast(Any, object()), cast(Any, object())
        )
    assert caught.value.code == ErrorCode.VALIDATION_ERROR
