"""Bounded Runner routes into existing M3 literature Application authority.

The caller of this adapter must derive ``VerifiedPrincipal`` from trusted local
authentication. These methods never construct or accept identity claims from a
request payload. The Application service rechecks current project, binding,
credential, role, temporal, scientific and replay rules in its own transaction.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.domain.phase2_identity import VerifiedPrincipal


def _principal(value: VerifiedPrincipal) -> None:
    if not isinstance(value, VerifiedPrincipal):
        raise TypeError("trusted verified principal required")


def _fields(payload: dict[str, Any], required: set[str], optional: set[str] = frozenset()) -> None:
    if (
        not isinstance(payload, dict)
        or not required <= payload.keys()
        or payload.keys() - required - optional
    ):
        raise ValueError("invalid operation fields")


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str):
        raise ValueError("UUID string required")
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("invalid UUID") from exc


def _basis(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 4096:
        raise ValueError("bounded nonblank basis required")
    return value


class HG1ReviewOperations:
    """Narrow request adapter; all read and write authority remains in Application."""

    def __init__(self, service: LiteratureEvidenceService):
        self._service = service

    def inspect(self, principal: VerifiedPrincipal, payload: dict[str, Any]) -> dict[str, Any]:
        _principal(principal)
        if not isinstance(payload, dict):
            raise ValueError("invalid operation fields")
        if "source_version_id" in payload:
            _fields(payload, {"project_id", "source_version_id"}, {"paragraph"})
            paragraph = payload.get("paragraph", 1)
            if type(paragraph) is not int or not 1 <= paragraph <= 100000:
                raise ValueError("invalid paragraph")
            return self._service.inspect(
                principal,
                _uuid(payload["project_id"]),
                _uuid(payload["source_version_id"]),
                paragraph,
            )
        _fields(payload, {"project_id", "evidence_id"})
        return self._service.get(
            principal, _uuid(payload["project_id"]), _uuid(payload["evidence_id"])
        )

    def review_verified(
        self, principal: VerifiedPrincipal, payload: dict[str, Any]
    ) -> dict[str, Any]:
        _principal(principal)
        _fields(payload, {"project_id", "evidence_id", "basis", "request_id"})
        return self._service.review(
            principal,
            _uuid(payload["project_id"]),
            _uuid(payload["evidence_id"]),
            "VERIFIED",
            _basis(payload["basis"]),
            _uuid(payload["request_id"]),
        )

    def create_support(
        self, principal: VerifiedPrincipal, payload: dict[str, Any]
    ) -> dict[str, Any]:
        _principal(principal)
        _fields(
            payload,
            {
                "project_id",
                "target_type",
                "target_id",
                "evidence_id",
                "qualification",
                "request_id",
            },
        )
        target_type = payload["target_type"]
        if not isinstance(target_type, str) or target_type not in {
            "ClaimVersion",
            "HypothesisVersion",
            "ResearchQuestionVersion",
        }:
            raise ValueError("unsupported frozen target")
        evidence_id = _uuid(payload["evidence_id"])
        return self._service.snapshot(
            principal,
            _uuid(payload["project_id"]),
            target_type,
            _uuid(payload["target_id"]),
            [
                {
                    "evidence_id": str(evidence_id),
                    "relation_type": "SUPPORTS",
                    "qualification": _basis(payload["qualification"]),
                }
            ],
            _uuid(payload["request_id"]),
        )
