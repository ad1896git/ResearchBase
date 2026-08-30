from __future__ import annotations

from dataclasses import asdict, is_dataclass

from researchbase.application.provenance_queries import (
    ClosureReportDTO,
    ClosureViolationDTO,
    RunInputDTO,
)


def test_query_dtos_are_frozen_finite_and_primitive_friendly() -> None:
    violation = ClosureViolationDTO(
        code="NOT_FOUND",
        object_type="Run",
        object_id="00000000-0000-0000-0000-000000000001",
        path=("claim_version", "run"),
        message="run was not found",
    )
    report = ClosureReportDTO(False, 1, (violation,))
    item = RunInputDTO(
        target_id="00000000-0000-0000-0000-000000000002",
        role="test",
        ordinal=0,
        content_hash=None,
    )

    assert is_dataclass(report)
    assert asdict(report)["violations"][0]["code"] == "NOT_FOUND"
    assert asdict(item) == {
        "target_id": "00000000-0000-0000-0000-000000000002",
        "role": "test",
        "ordinal": 0,
        "content_hash": None,
    }
