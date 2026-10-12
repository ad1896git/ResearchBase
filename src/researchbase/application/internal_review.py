"""Authenticated initial review of exact frozen PR2-14 scientific targets."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NoReturn
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.ports import UnitOfWork
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_REVIEWERS = frozenset({"OWNER", "REVIEWER"})
_TYPES = frozenset(
    {"SCIENTIFIC", "STATISTICAL", "LITERATURE", "REPRODUCIBILITY", "EDITORIAL", "COMPREHENSIVE"}
)
_RECOMMENDATIONS = frozenset({"ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"})
_SEVERITIES = frozenset({"INFO", "MINOR", "MAJOR", "BLOCKING"})
_ISSUE_TYPES = frozenset(
    {
        "UNSUPPORTED_CLAIM",
        "CITATION",
        "STATISTICAL",
        "METHODOLOGICAL",
        "REPRODUCIBILITY",
        "OVERCLAIM",
        "CONTRADICTION",
        "NOVELTY",
        "WRITING",
        "OTHER",
    }
)


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _text(value: str, label: str) -> str:
    if not isinstance(value, str):
        _fail(ErrorCode.VALIDATION_ERROR, f"{label} must be text")
    result = unicodedata.normalize("NFC", value)
    if not result.strip() or len(result) > 16000:
        _fail(ErrorCode.VALIDATION_ERROR, f"{label} must be nonblank and bounded")
    try:
        result.encode("utf-8", "strict")
    except UnicodeError:
        _fail(ErrorCode.VALIDATION_ERROR, f"{label} contains invalid Unicode")
    return result


@dataclass(frozen=True, slots=True)
class ReviewIssueRequest:
    severity: str
    issue_type: str
    description: str


@dataclass(frozen=True, slots=True)
class ReviewIssueReadback:
    id: UUID
    severity: str
    issue_type: str
    description: str
    status: str


@dataclass(frozen=True, slots=True)
class InternalReviewReadback:
    id: UUID
    project_id: UUID
    target_id: UUID
    target_content_hash: str
    reviewer_actor_id: UUID
    review_type: str
    recommendation: str
    summary: str
    content_hash: str
    issues: tuple[ReviewIssueReadback, ...]
    target_kind: str


class InternalReviewService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, literature_evidence: Any
    ) -> None:
        self._factory = factory
        self._auth = ScientificConclusionService(factory, credentials, literature_evidence)
        self._literature = literature_evidence

    @staticmethod
    def _hash(project: UUID, target_kind: str, target_id: UUID, digest: str, actor: UUID,
              review_type: str, recommendation: str, summary: str) -> str:
        material = {
            "type": "InternalReviewRecord", "material_version": 1,
            "project_id": str(project),
            "target": {"type": target_kind, "id": str(target_id),
                       "content_hash": digest},
            "reviewer_actor_id": str(actor), "review_type": review_type,
            "recommendation": recommendation, "summary": summary,
        }
        return str(sha256_canonical_json(material))

    def _verify(self, uow: UnitOfWork, row: dict) -> None:
        claim_id = row["claim_version_id"]
        conclusion_id = row["scientific_conclusion_version_id"]
        if (claim_id is None) == (conclusion_id is None):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                  "unsupported review target in this read boundary")
        kind = "ClaimVersion" if claim_id is not None else "ScientificConclusionVersion"
        target_id = claim_id if claim_id is not None else conclusion_id
        if kind == "ClaimVersion":
            target = uow.literature_evidence.target(kind, target_id, row["project_id"])
        else:
            target = uow.internal_review.conclusion_target(target_id, row["project_id"])
        if (target is None or target["content_hash"] != row["target_content_hash"]
            or self._hash(row["project_id"], kind, target_id, row["target_content_hash"],
                          row["reviewer_actor_id"], row["review_type"],
                          row["recommendation"], row["summary"]) != row["content_hash"]):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                  "review hash or frozen target binding mismatch")
        if kind == "ClaimVersion":
            self._literature._target(uow, kind, target_id, row["project_id"])
        else:
            self._auth._view(uow, row["project_id"],
                             target["scientific_conclusion_id"], target_id,
                             require_current=False)

    @staticmethod
    def _view(row: dict, issues: list[dict]) -> InternalReviewReadback:
        claim_id = row["claim_version_id"]
        kind = "CLAIM_VERSION" if claim_id is not None else "SCIENTIFIC_CONCLUSION_VERSION"
        return InternalReviewReadback(
            row["id"],
            row["project_id"],
            claim_id if claim_id is not None else row["scientific_conclusion_version_id"],
            row["target_content_hash"],
            row["reviewer_actor_id"],
            row["review_type"],
            row["recommendation"],
            row["summary"],
            row["content_hash"],
            tuple(
                ReviewIssueReadback(
                    i["id"], i["severity"], i["issue_type"], i["description"], i["status"]
                )
                for i in issues
            ),
            kind,
        )

    def create(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        target_kind: str,
        target_id: UUID,
        review_type: str,
        recommendation: str,
        summary: str,
        issues: tuple[ReviewIssueRequest, ...],
        request: UUID,
    ) -> InternalReviewReadback:
        if (
            target_kind not in {"CLAIM_VERSION", "SCIENTIFIC_CONCLUSION_VERSION"}
            or type(target_id) is not UUID
            or type(request) is not UUID
            or review_type not in _TYPES
            or recommendation not in _RECOMMENDATIONS
            or not isinstance(issues, tuple)
            or len(issues) > 100
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "bounded exact frozen review required")
        clean_summary = _text(summary, "review summary")
        clean_issues: list[ReviewIssueRequest] = []
        for issue in issues:
            if (
                not isinstance(issue, ReviewIssueRequest)
                or issue.severity not in _SEVERITIES
                or issue.issue_type not in _ISSUE_TYPES
            ):
                _fail(ErrorCode.VALIDATION_ERROR, "invalid review issue")
            clean_issues.append(
                ReviewIssueRequest(
                    issue.severity, issue.issue_type, _text(issue.description, "issue description")
                )
            )
        with self._factory() as uow:
            at = self._auth._authorize(uow, principal, project, _REVIEWERS)
            identity = uuid5(
                NAMESPACE_URL,
                f"pr214:{principal.deployment_id}:{project}:{principal.actor_id}:{request}",
            )
            repo = uow.internal_review
            repo.lock_request(identity)
            # The advisory lock can wait past role or credential expiry (R4 TEMP-AUTH-01).
            at = self._auth._authorize(uow, principal, project, _REVIEWERS)
            is_claim = target_kind == "CLAIM_VERSION"
            if is_claim:
                target = uow.literature_evidence.target("ClaimVersion", target_id, project)
            else:
                target = repo.conclusion_target(target_id, project, lock=True)
            if (
                target is None
                or target["status"] not in {"FROZEN", "SUPERSEDED"}
                or target["frozen_at"] is None
            ):
                _fail(
                    ErrorCode.REVIEW_TARGET_NOT_FROZEN,
                    "exact same-project frozen review target required",
                )
            if target["created_by"] == principal.actor_id:
                _fail(ErrorCode.CONFLICT_OF_INTEREST, "reviewer must be independent")
            if is_claim:
                checked = self._literature._target(uow, "ClaimVersion", target_id, project)
                if checked["current_validity"] != "VALID":
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                          "review target current validity is not valid")
            else:
                checked = self._auth._view(uow, project,
                                           target["scientific_conclusion_id"], target_id,
                                           require_current=True)
                if checked.validity != "VALID":
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                          "review target current validity is not valid")
            # Target validation can wait on its own row lock after the request lock.
            at = self._auth._authorize(uow, principal, project, _REVIEWERS)
            digest = str(target["content_hash"])
            kind = "ClaimVersion" if is_claim else "ScientificConclusionVersion"
            own_hash = self._hash(project, kind, target_id, digest, principal.actor_id,
                                  review_type, recommendation, clean_summary)
            existing = repo.review(identity, project)
            if existing is not None:
                self._verify(uow, existing)
                found = self._view(existing, repo.issues(identity))
                expected_issues = tuple(
                    (x.severity, x.issue_type, x.description) for x in clean_issues
                )
                actual_issues = tuple(
                    (x.severity, x.issue_type, x.description) for x in found.issues
                )
                if (
                    found.target_id != target_id
                    or found.content_hash != own_hash
                    or actual_issues != expected_issues
                ):
                    _fail(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "review request reused with different material",
                    )
                return found
            repo.insert_review(
                {
                    "id": identity,
                    "project_id": project,
                    "claim_version_id": target_id if is_claim else None,
                    "scientific_conclusion_version_id": None if is_claim else target_id,
                    "target_content_hash": digest,
                    "reviewer_actor_id": principal.actor_id,
                    "review_type": review_type,
                    "recommendation": recommendation,
                    "summary": clean_summary,
                    "created_at": at,
                    "content_hash": own_hash,
                    "hash_scheme": "sha256-cjson-v1",
                }
            )
            for ordinal, issue in enumerate(clean_issues):
                repo.insert_issue(
                    {
                        "id": uuid5(identity, f"issue:{ordinal}"),
                        "review_record_id": identity,
                        "severity": issue.severity,
                        "issue_type": issue.issue_type,
                        "description": issue.description,
                        "created_at": at,
                        "ordinal": ordinal,
                    }
                )
            created = repo.review(identity, project)
            if created is None:
                _fail(ErrorCode.NOT_FOUND, "created review unavailable")
            result = self._view(created, repo.issues(identity))
            uow.commit()
            return result

    def read(
        self, principal: VerifiedPrincipal, project: UUID, review_id: UUID
    ) -> InternalReviewReadback:
        if type(review_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact review UUID required")
        with self._factory() as uow:
            self._auth._authorize(uow, principal, project, _REVIEWERS)
            row = uow.internal_review.review(review_id, project)
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "review not found")
            self._verify(uow, row)
            return self._view(row, uow.internal_review.issues(review_id))
