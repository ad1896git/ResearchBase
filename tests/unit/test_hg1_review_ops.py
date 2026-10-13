"""The local review adapter adds no authority of its own."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.hg1_review_ops import HG1ReviewOperations

PROJECT = "3a850c58-07b2-47e7-a425-750409a920b1"
SOURCE = "4a850c58-07b2-47e7-a425-750409a920b1"
EVIDENCE = "5a850c58-07b2-47e7-a425-750409a920b1"
TARGET = "6a850c58-07b2-47e7-a425-750409a920b1"
REQUEST = "7a850c58-07b2-47e7-a425-750409a920b1"


def principal():
    return VerifiedPrincipal(
        actor_id=UUID("8a850c58-07b2-47e7-a425-750409a920b1"),
        deployment_id="test",
        subject_kind="OS_UID",
        subject_value="502",
        credential_id="credential",
        verified_at=datetime.now(UTC),
    )


class Service(LiteratureEvidenceService):
    def __init__(self):
        self.calls = []

    def inspect(self, *args):
        self.calls.append(("inspect", args))
        return {"ok": True}

    def get(self, *args):
        self.calls.append(("get", args))
        return {"ok": True}

    def review(self, *args):
        self.calls.append(("review", args))
        return {"ok": True}

    def snapshot(self, *args):
        self.calls.append(("snapshot", args))
        return {"ok": True}


def test_inspection_routes_to_authorized_service():
    service = Service()
    adapter = HG1ReviewOperations(service)
    actor = principal()
    assert adapter.inspect(actor, {"project_id": PROJECT, "source_version_id": SOURCE}) == {
        "ok": True
    }
    assert service.calls == [("inspect", (actor, UUID(PROJECT), UUID(SOURCE), 1))]
    assert adapter.inspect(actor, {"project_id": PROJECT, "evidence_id": EVIDENCE}) == {"ok": True}
    assert service.calls[-1] == ("get", (actor, UUID(PROJECT), UUID(EVIDENCE)))


def test_review_is_verified_only_and_passes_server_principal():
    service = Service()
    actor = principal()
    HG1ReviewOperations(service).review_verified(
        actor,
        {
            "project_id": PROJECT,
            "evidence_id": EVIDENCE,
            "basis": "I checked the exact passage",
            "request_id": REQUEST,
        },
    )
    assert service.calls == [
        (
            "review",
            (
                actor,
                UUID(PROJECT),
                UUID(EVIDENCE),
                "VERIFIED",
                "I checked the exact passage",
                UUID(REQUEST),
            ),
        )
    ]


def test_support_is_exactly_one_supports_edge_through_service():
    service = Service()
    actor = principal()
    HG1ReviewOperations(service).create_support(
        actor,
        {
            "project_id": PROJECT,
            "target_type": "ClaimVersion",
            "target_id": TARGET,
            "evidence_id": EVIDENCE,
            "qualification": "Direct relevant passage",
            "request_id": REQUEST,
        },
    )
    assert service.calls == [
        (
            "snapshot",
            (
                actor,
                UUID(PROJECT),
                "ClaimVersion",
                UUID(TARGET),
                [
                    {
                        "evidence_id": EVIDENCE,
                        "relation_type": "SUPPORTS",
                        "qualification": "Direct relevant passage",
                    }
                ],
                UUID(REQUEST),
            ),
        )
    ]


@pytest.mark.parametrize(
    "method,payload",
    [
        ("inspect", {"project_id": PROJECT, "evidence_id": EVIDENCE, "actor_id": TARGET}),
        ("inspect", {"project_id": PROJECT, "source_version_id": SOURCE, "evidence_id": EVIDENCE}),
        ("inspect", {"project_id": PROJECT, "source_version_id": SOURCE, "paragraph": True}),
        (
            "review_verified",
            {
                "project_id": PROJECT,
                "evidence_id": EVIDENCE,
                "basis": "a",
                "request_id": REQUEST,
                "status": "VERIFIED",
            },
        ),
        (
            "review_verified",
            {"project_id": PROJECT, "evidence_id": EVIDENCE, "basis": " ", "request_id": REQUEST},
        ),
        (
            "create_support",
            {
                "project_id": PROJECT,
                "target_type": "Artifact",
                "target_id": TARGET,
                "evidence_id": EVIDENCE,
                "qualification": "x",
                "request_id": REQUEST,
            },
        ),
        (
            "create_support",
            {
                "project_id": PROJECT,
                "target_type": "ClaimVersion",
                "target_id": TARGET,
                "evidence_id": EVIDENCE,
                "qualification": "x",
                "request_id": "../../../etc/passwd",
            },
        ),
    ],
)
def test_invalid_or_authority_bearing_payload_fails_before_service(method, payload):
    service = Service()
    with pytest.raises(ValueError):
        getattr(HG1ReviewOperations(service), method)(principal(), payload)
    assert service.calls == []


def test_non_verified_principal_fails_before_service():
    service = Service()
    with pytest.raises(TypeError):
        HG1ReviewOperations(service).inspect(
            # Deliberately pass an unverified identity to exercise the runtime rejection.
            SimpleNamespace(actor_id=UUID(TARGET)),  # pyright: ignore[reportArgumentType]
            {
                "project_id": PROJECT,
                "evidence_id": EVIDENCE,
            },
        )
    assert service.calls == []
