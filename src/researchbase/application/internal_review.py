"""Authenticated initial review of exact frozen PR2-14 scientific targets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from types import UnionType
from typing import Any, Literal, NoReturn, Union, get_args, get_origin, get_type_hints
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.manuscript_freeze import ManuscriptFreezeService
from researchbase.application.ports import UnitOfWork
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.decision import DecisionBasisReference
from researchbase.domain.internal_review import (
    _ISSUE_TYPES,
    _RECOMMENDATIONS,
    _SEVERITIES,
    _TYPES,
    review_material,
)
from researchbase.domain.internal_review import (
    _text as review_text,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.time import to_utc

_REVIEWERS = frozenset({"OWNER", "REVIEWER"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _text(value: str, label: str) -> str:
    try:
        return review_text(value, label)
    except ValueError as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from exc


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


Disposition = Literal["ADDRESSED", "DISMISSED"]
IssueStatus = Literal["OPEN", "ADDRESSED", "DISMISSED"]
Validity = Literal["VALID", "STALE", "INVALID"]


def _validate_issue_dto(value) -> None:
    """Readbacks are closed values, with strict types rather than coercion."""

    def valid(item, annotation):
        origin = get_origin(annotation)
        if origin is Literal:
            return type(item) is str and item in get_args(annotation)
        if origin in (UnionType, Union):
            return any(valid(item, arg) for arg in get_args(annotation))
        if origin is tuple:
            return type(item) is tuple and all(valid(x, get_args(annotation)[0]) for x in item)
        if annotation is datetime:
            return (
                type(item) is datetime and item.tzinfo is not None and item.utcoffset() is not None
            )
        return type(item) is annotation

    for name, annotation in get_type_hints(type(value)).items():
        item = getattr(value, name)
        if annotation is datetime and type(item) is datetime:
            item = to_utc(item)
            object.__setattr__(value, name, item)
        if not valid(item, annotation):
            raise ValueError("invalid Issue readback field: " + name)
        if name.endswith("content_hash") and item is not None:
            if type(item) is not str:
                raise ValueError("invalid saved hash")
            if ContentHash(item) != item:
                raise ValueError("saved hash must be lowercase SHA-256")
    for name in ("rationale", "description"):
        item = getattr(value, name, None)
        if item is not None and review_text(item, name) != item:
            raise ValueError("saved Issue text must be NFC")


@dataclass(frozen=True, slots=True)
class RecordIssueDispositionCommand:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    disposition: Disposition
    revision_action_id: UUID
    re_review_record_id: UUID
    rationale: str
    decision_id: UUID | None = None

    def __post_init__(self):
        from researchbase.domain.internal_review import _DISPOSITIONS

        if (
            any(
                type(getattr(self, key)) is not UUID
                for key in (
                    "id",
                    "project_id",
                    "review_issue_id",
                    "revision_action_id",
                    "re_review_record_id",
                )
            )
            or (self.decision_id is not None and type(self.decision_id) is not UUID)
            or type(self.disposition) is not str
            or self.disposition not in _DISPOSITIONS
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "exact disposition UUIDs and enum required")
        object.__setattr__(self, "rationale", _text(self.rationale, "disposition rationale"))


@dataclass(frozen=True, slots=True)
class IssueDispositionReadback:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    actor_id: UUID
    revision_action_id: UUID
    re_review_record_id: UUID
    decision_id: UUID | None
    prior_status: Literal["OPEN"]
    new_status: Disposition
    rationale: str
    occurred_at: datetime
    action_content_hash: str
    re_review_content_hash: str
    decision_content_hash: str | None
    old_target_validity: Validity
    re_review_target_validity: Validity
    has_superseding_action: bool

    def __post_init__(self):
        _validate_issue_dto(self)
        if self.new_status == "DISMISSED" and self.decision_id is None:
            raise ValueError("dismissal Decision required")
        if (self.decision_id is None) != (self.decision_content_hash is None):
            raise ValueError("Decision/hash presence mismatch")


@dataclass(frozen=True, slots=True)
class IssueEventReadback:
    id: UUID
    review_issue_id: UUID
    actor_id: UUID
    prior_status: Literal["OPEN"] | None
    new_status: IssueStatus
    occurred_at: datetime
    revision_action_id: UUID | None
    re_review_record_id: UUID | None
    decision_id: UUID | None
    rationale: str | None

    def __post_init__(self):
        _validate_issue_dto(self)
        if self.prior_status is None:
            valid = self.new_status == "OPEN" and all(
                getattr(self, key) is None
                for key in ("revision_action_id", "re_review_record_id", "decision_id", "rationale")
            )
        else:
            valid = (
                self.prior_status == "OPEN"
                and self.new_status in {"ADDRESSED", "DISMISSED"}
                and type(self.revision_action_id) is UUID
                and type(self.re_review_record_id) is UUID
                and type(self.rationale) is str
                and review_text(self.rationale, "saved rationale") == self.rationale
                and (self.new_status != "DISMISSED" or type(self.decision_id) is UUID)
            )
        if not valid:
            raise ValueError("invalid Issue event shape")


@dataclass(frozen=True, slots=True)
class IssueHistoryReadback:
    project_id: UUID
    review_issue_id: UUID
    original_review_id: UUID
    severity: Literal["INFO", "MINOR", "MAJOR", "BLOCKING"]
    issue_type: Literal[
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
    ]
    description: str
    status: IssueStatus
    created_at: datetime
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    manuscript_version_id: UUID | None
    target_content_hash: str
    target_validity: Validity
    events: tuple[IssueEventReadback, ...]
    disposition: IssueDispositionReadback | None

    def __post_init__(self):
        _validate_issue_dto(self)
        if (
            sum(
                x is not None
                for x in (
                    self.claim_version_id,
                    self.scientific_conclusion_version_id,
                    self.manuscript_version_id,
                )
            )
            != 1
        ):
            raise ValueError("exact concrete Issue target required")
        if (
            len(self.events) != (1 if self.status == "OPEN" else 2)
            or self.events[0].new_status != "OPEN"
            or (self.disposition is None) != (self.status == "OPEN")
        ):
            raise ValueError("complete root/terminal history required")


class InternalReviewService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, literature_evidence: Any
    ) -> None:
        self._factory = factory
        self._auth = ScientificConclusionService(factory, credentials, literature_evidence)
        self._literature = literature_evidence
        self._credentials = credentials
        self._manuscripts = ManuscriptFreezeService(
            factory, credentials, getattr(literature_evidence, "_store", None)
        )

    @staticmethod
    def _hash(
        project: UUID,
        target_kind: str,
        target_id: UUID,
        digest: str,
        actor: UUID,
        review_type: str,
        recommendation: str,
        summary: str,
    ) -> str:
        return str(
            sha256_canonical_json(
                review_material(
                    project,
                    target_kind,
                    target_id,
                    digest,
                    actor,
                    review_type,
                    recommendation,
                    summary,
                )
            )
        )

    def _verify(self, uow: UnitOfWork, row: dict) -> None:
        if row.get("manuscript_version_id") is not None:
            self._verify_manuscript_review(uow, row)
            return
        claim_id = row["claim_version_id"]
        conclusion_id = row["scientific_conclusion_version_id"]
        if (claim_id is None) == (conclusion_id is None):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "unsupported review target in this read boundary",
            )
        kind = "ClaimVersion" if claim_id is not None else "ScientificConclusionVersion"
        target_id = claim_id if claim_id is not None else conclusion_id
        if kind == "ClaimVersion":
            target = uow.literature_evidence.target(kind, target_id, row["project_id"])
        else:
            target = uow.internal_review.conclusion_target(target_id, row["project_id"])
        if (
            target is None
            or target["content_hash"] != row["target_content_hash"]
            or self._hash(
                row["project_id"],
                kind,
                target_id,
                row["target_content_hash"],
                row["reviewer_actor_id"],
                row["review_type"],
                row["recommendation"],
                row["summary"],
            )
            != row["content_hash"]
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "review hash or frozen target binding mismatch",
            )
        if kind == "ClaimVersion":
            self._literature._target(uow, kind, target_id, row["project_id"])
        else:
            self._auth._view(
                uow,
                row["project_id"],
                target["scientific_conclusion_id"],
                target_id,
                require_current=False,
            )

    @staticmethod
    def _view(row: dict, issues: list[dict]) -> InternalReviewReadback:
        claim_id = row["claim_version_id"]
        manuscript_id = row.get("manuscript_version_id")
        kind = (
            "MANUSCRIPT_VERSION"
            if manuscript_id is not None
            else "CLAIM_VERSION"
            if claim_id is not None
            else "SCIENTIFIC_CONCLUSION_VERSION"
        )
        return InternalReviewReadback(
            row["id"],
            row["project_id"],
            manuscript_id
            if manuscript_id is not None
            else claim_id
            if claim_id is not None
            else row["scientific_conclusion_version_id"],
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
            type(target_kind) is not str
            or target_kind
            not in {"CLAIM_VERSION", "SCIENTIFIC_CONCLUSION_VERSION", "MANUSCRIPT_VERSION"}
            or type(project) is not UUID
            or type(target_id) is not UUID
            or type(request) is not UUID
            or type(review_type) is not str
            or review_type not in _TYPES
            or type(recommendation) is not str
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
                or type(issue.severity) is not str
                or issue.severity not in _SEVERITIES
                or type(issue.issue_type) is not str
                or issue.issue_type not in _ISSUE_TYPES
            ):
                _fail(ErrorCode.VALIDATION_ERROR, "invalid review issue")
            clean_issues.append(
                ReviewIssueRequest(
                    issue.severity, issue.issue_type, _text(issue.description, "issue description")
                )
            )
        if target_kind == "MANUSCRIPT_VERSION":
            self._manuscripts._principal(principal)
            for attempt in range(3):
                try:
                    return self._create_manuscript(
                        principal,
                        project,
                        target_id,
                        review_type,
                        recommendation,
                        clean_summary,
                        tuple(clean_issues),
                        request,
                    )
                except ResearchBaseError as exc:
                    if attempt == 2 or not (exc.details or {}).get("retryable_b05"):
                        raise
            raise AssertionError("unreachable")
        self._manuscripts._principal(principal)
        is_claim = target_kind == "CLAIM_VERSION"
        with self._factory() as uow:
            uow.enable_internal_review_error_normalization()
            uow.configure_revision_transaction()
            uow.internal_review.prepare_insert()
            if is_claim:
                at = self._auth._authorize(uow, principal, project, _REVIEWERS)
            elif not isinstance(principal, VerifiedPrincipal) or type(project) is not UUID:
                _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
            identity = uuid5(
                NAMESPACE_URL,
                f"pr214:{principal.deployment_id}:{project}:{principal.actor_id}:{request}",
            )
            repo = uow.internal_review
            repo.lock_request(identity)
            if is_claim:
                # Preserve the accepted Claim review coordination and authorization.
                at = self._auth._authorize(uow, principal, project, _REVIEWERS)
                target = uow.literature_evidence.target("ClaimVersion", target_id, project)
            else:
                # Request -> exact target -> parent -> project/authority -> reviews.
                # No target information is disclosed until current authorization.
                target = repo.conclusion_target(target_id, project, lock=True)
                at = self._auth._authorize(uow, principal, project, _REVIEWERS)
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
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "review target current validity is not valid",
                    )
            else:
                checked = self._auth._view(
                    uow,
                    project,
                    target["scientific_conclusion_id"],
                    target_id,
                    require_current=True,
                )
                if checked.validity != "VALID":
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "review target current validity is not valid",
                    )
            # Target validation can wait on its own row lock after the request lock.
            at = self._auth._authorize(uow, principal, project, _REVIEWERS)
            digest = str(target["content_hash"])
            kind = "ClaimVersion" if is_claim else "ScientificConclusionVersion"
            own_hash = self._hash(
                project,
                kind,
                target_id,
                digest,
                principal.actor_id,
                review_type,
                recommendation,
                clean_summary,
            )
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
        self._manuscripts._principal(principal)
        if type(project) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact project UUID required")
        with self._factory() as uow:
            uow.enable_internal_review_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._authorize_snapshot(uow, principal, project)
            row = uow.internal_review.review(review_id, project)
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "review not found")
            self._verify(uow, row)
            result = self._view(row, self._issues(uow, row))
            self._authorize_snapshot(uow, principal, project)
            return result

    def _authorize_snapshot(
        self, uow: UnitOfWork, principal: VerifiedPrincipal, project: UUID
    ) -> Any:
        rows = uow.internal_review.authority(principal, project)
        at = uow.manuscript_freeze.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live:
            for row in rows:
                if (
                    row["actor_type"] == "HUMAN"
                    and row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in _REVIEWERS
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                    and row["project_status"] == "ACTIVE"
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current review authority unavailable")

    def _manuscript_target(
        self, uow: UnitOfWork, project: UUID, identity: UUID, *, current: bool = False
    ) -> dict:
        row = uow.internal_review.manuscript_target(identity, project)
        if (
            row is None
            or row["status"] not in {"FROZEN", "SUPERSEDED"}
            or any(
                row[field] is None for field in ("frozen_at", "content_hash", "placement_set_hash")
            )
        ):
            _fail(ErrorCode.REVIEW_TARGET_NOT_FROZEN, "exact sealed manuscript required")
        parent = uow.publication.publication(row["publication_id"], project)
        if parent is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript parent missing")
        # SUPERSEDED remains unreachable in B04's schema. Verify its immutable
        # seal with the same literal B04 algorithm if a later contract enables it.
        checked_row = row if row["status"] == "FROZEN" else {**row, "status": "FROZEN"}
        checked_parent = (
            parent
            if row["status"] == "FROZEN"
            else {**parent, "current_manuscript_version_id": identity}
        )
        try:
            result = self._manuscripts.verify_in_uow(uow, project, checked_parent, checked_row)
        except ResearchBaseError as exc:
            if exc.code == ErrorCode.FROZEN_REFERENCE_REQUIRED:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript frozen closure invalid")
            raise
        if current and result.current_validity != "VALID":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current manuscript closure invalid")
        return row

    def _verify_manuscript_review(self, uow: UnitOfWork, row: dict) -> None:
        if any(
            row.get(field) is not None
            for field in (
                "claim_version_id",
                "scientific_conclusion_version_id",
                "artifact_version_id",
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "ambiguous review target")
        try:
            if review_text(row["summary"], "saved summary") != row["summary"]:
                raise ValueError("saved summary must be NFC")
            target = self._manuscript_target(uow, row["project_id"], row["manuscript_version_id"])
            own_hash = self._hash(
                row["project_id"],
                "ManuscriptVersion",
                target["id"],
                target["content_hash"],
                row["reviewer_actor_id"],
                row["review_type"],
                row["recommendation"],
                row["summary"],
            )
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved review material"
            ) from exc
        except ResearchBaseError as exc:
            if exc.code == ErrorCode.REVIEW_TARGET_NOT_FROZEN:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review seal missing")
            raise
        if (
            own_hash != row["content_hash"]
            or target["content_hash"] != row["target_content_hash"]
            or row["hash_scheme"] != "sha256-cjson-v1"
            or row["reviewer_actor_id"] in uow.internal_review.material_authors(target["id"])
            or not uow.internal_review.review_creation_authorized(row)
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid historical reviewer binding")

    def _issues(self, uow: UnitOfWork, row: dict) -> list[dict]:
        issues = uow.internal_review.issues(row["id"])
        events = uow.internal_review.issue_events(row["id"])
        by_issue = {}
        for event in events:
            by_issue.setdefault(event["issue_id"], []).append(event)
        for ordinal, issue in enumerate(issues):
            try:
                if (
                    review_text(issue["description"], "saved issue") != issue["description"]
                    or issue["severity"] not in _SEVERITIES
                    or issue["issue_type"] not in _ISSUE_TYPES
                    or issue["ordinal"] != ordinal
                ):
                    raise ValueError("invalid saved issue")
                self._history_events(uow, row, issue, by_issue.get(issue["id"], []))
            except (ValueError, TypeError, UnicodeError, KeyError):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved issue history")
        return issues

    def _create_manuscript(
        self, principal, project, target_id, review_type, recommendation, summary, issues, request
    ) -> InternalReviewReadback:
        identity = uuid5(
            NAMESPACE_URL,
            f"pr214:{principal.deployment_id}:{project}:{principal.actor_id}:{request}",
        )
        with self._factory() as uow:
            uow.enable_internal_review_error_normalization()
            uow.configure_revision_transaction()
            repo = uow.internal_review
            repo.prepare_insert()
            repo.prepare_write()
            uow.enable_revision_action_snapshot_reads()
            repo.lock_request(identity)
            repo.lock_manuscript(target_id)
            uow.literature_search_plan.lock_project(project)
            repo.lock_publication(target_id, project)
            self._authorize_snapshot(uow, principal, project)
            existing = repo.review(identity, project)
            if existing is not None:
                if existing.get("manuscript_version_id") != target_id:
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "review request target differs")
                self._verify(uow, existing)
                found_issues = self._issues(uow, existing)
                expected = self._hash(
                    project,
                    "ManuscriptVersion",
                    target_id,
                    existing["target_content_hash"],
                    principal.actor_id,
                    review_type,
                    recommendation,
                    summary,
                )
                if existing["content_hash"] != expected or tuple(
                    (i["severity"], i["issue_type"], i["description"]) for i in found_issues
                ) != tuple((i.severity, i.issue_type, i.description) for i in issues):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "review request material differs")
                result = self._view(existing, found_issues)
                self._authorize_snapshot(uow, principal, project)
                return result
            target = self._manuscript_target(uow, project, target_id, current=True)
            if principal.actor_id in repo.material_authors(target_id):
                _fail(ErrorCode.CONFLICT_OF_INTEREST, "reviewer is a manuscript material author")
            # Include all preexisting reviews/issues after acquiring the target.
            for review in repo.manuscript_reviews(target_id, project):
                self._issues(uow, review)
            at = self._authorize_snapshot(uow, principal, project)
            repo.insert_review(
                {
                    "id": identity,
                    "project_id": project,
                    "manuscript_version_id": target_id,
                    "claim_version_id": None,
                    "scientific_conclusion_version_id": None,
                    "target_content_hash": target["content_hash"],
                    "reviewer_actor_id": principal.actor_id,
                    "review_type": review_type,
                    "recommendation": recommendation,
                    "summary": summary,
                    "created_at": at,
                    "content_hash": self._hash(
                        project,
                        "ManuscriptVersion",
                        target_id,
                        target["content_hash"],
                        principal.actor_id,
                        review_type,
                        recommendation,
                        summary,
                    ),
                    "hash_scheme": "sha256-cjson-v1",
                }
            )
            for ordinal, issue in enumerate(issues):
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
            repo.force_constraints()
            created = repo.review(identity, project)
            if created is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "created review missing")
            result = self._view(created, self._issues(uow, created))
            self._authorize_snapshot(uow, principal, project)
            uow.commit()
            return result

    def _revision_service(self):
        from researchbase.application.revision_action import RevisionActionService

        return RevisionActionService(self._factory, self._credentials, self._literature)

    def _disposition_authorize(
        self, uow, principal, project, *, write=False, opener=None, dismiss=False
    ):
        from researchbase.application.decision import _READERS

        rows = uow.internal_review.authority(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        for row in rows if live else ():
            if (
                row["retired_at"] is None
                and row["membership_status"] == "ACTIVE"
                and row["binding_status"] == "ACTIVE"
                and row["role"] in _READERS
                and row["effective_from"] <= at
                and (row["effective_until"] is None or at < row["effective_until"])
                and row["bound_at"] <= at
                and (row["revoked_at"] is None or at < row["revoked_at"])
            ):
                if not write:
                    return at
                if (
                    row["actor_type"] == "HUMAN"
                    and row["project_status"] == "ACTIVE"
                    and (
                        row["role"] == "OWNER"
                        or (
                            not dismiss
                            and opener == principal.actor_id
                            and row["role"] == "REVIEWER"
                        )
                    )
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current disposition authority unavailable")

    @staticmethod
    def _disposition_input(principal, project, identity):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project) is not UUID or type(identity) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact project and Issue event UUID required")

    def _history_events(self, uow, review, issue, events):
        uow.internal_review.validate_issue_history(issue["id"])
        roots = [e for e in events if e["prior_status"] is None]
        terminal = [e for e in events if e["prior_status"] == "OPEN"]
        if (
            len(roots) != 1
            or len(events) != 1 + len(terminal)
            or len(terminal) > 1
            or roots[0]["new_status"] != "OPEN"
            or roots[0]["actor_id"] != review["reviewer_actor_id"]
            or roots[0]["occurred_at"] != issue["created_at"]
            or issue["status"] != (terminal[0]["new_status"] if terminal else "OPEN")
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "Issue projection/history mismatch")
        ordered = roots + terminal
        result = tuple(
            IssueEventReadback(
                **{
                    f.name: event["issue_id" if f.name == "review_issue_id" else f.name]
                    for f in fields(IssueEventReadback)
                }
            )
            for event in ordered
        )
        if terminal:
            self._disposition_readback(uow, review["project_id"], issue, terminal[0])
        return result

    def _disposition_readback(self, uow, project, issue, event, *, current=False):
        from researchbase.domain.internal_review import disposition_policy

        revisions = self._revision_service()
        action = uow.revision_action.action(event["revision_action_id"], project)
        link = uow.revision_action.link(event["revision_action_id"], event["re_review_record_id"])
        review = uow.internal_review.review(event["re_review_record_id"], project)
        if current and action is None:
            revisions._absent(uow, "RevisionAction", event["revision_action_id"])
        if current and review is None:
            revisions._absent(uow, "InternalReviewRecord", event["re_review_record_id"])
        if action is None or link is None or review is None:
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact saved disposition basis unavailable"
            )
        effective, decision = revisions._effective_issue(uow, action, project)
        if effective["id"] != issue["id"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unrelated action concern")
        if event["decision_id"] != action["decision_record_id"]:
            _fail(
                ErrorCode.DECISION_BASIS_INVALID
                if current
                else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "event must retain exact action Decision",
            )
        choice = decision.decision if decision else None
        if not disposition_policy(
            event["new_status"],
            issue["severity"],
            "OWNER",
            opener=False,
            action_type=action["action_type"],
            decision=choice,
        ):
            _fail(
                ErrorCode.DECISION_BASIS_INVALID
                if current
                else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "disposition requires matching changed/no-change Decision basis",
            )
        changed = event["new_status"] == "ADDRESSED"
        checked = revisions._verify(uow, action, project, current=current and changed)
        correspondence = revisions._correspondence(
            uow,
            link,
            action,
            project,
            current=current and changed,
            independent_actor=event["actor_id"],
            new_disposition=current,
        )
        if review["id"] == issue["review_record_id"] or review["recommendation"] not in {
            "ACCEPT",
            "MINOR_REVISION",
        }:
            _fail(
                ErrorCode.INVALID_STATE_TRANSITION
                if current
                else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "acceptable exact new re-review required",
            )
        if current and (
            uow.revision_action.has_successor(action["id"])
            or any(
                i["status"] == "OPEN" and i["severity"] in {"MAJOR", "BLOCKING"}
                for i in uow.internal_review.issues(review["id"])
            )
        ):
            _fail(
                ErrorCode.INVALID_STATE_TRANSITION,
                "action superseded or re-review concern remains open",
            )
        if not current and (
            event["occurred_at"]
            < max(
                issue["created_at"],
                action["created_at"],
                review["created_at"],
                link["recorded_at"],
                decision.decided_at if decision else issue["created_at"],
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid disposition time")
        return IssueDispositionReadback(
            event["id"],
            project,
            issue["id"],
            event["actor_id"],
            action["id"],
            review["id"],
            event["decision_id"],
            "OPEN",
            event["new_status"],
            event["rationale"],
            event["occurred_at"],
            checked[0],
            review["content_hash"],
            decision.content_hash if decision else None,
            checked[2],
            correspondence.target_validity,
            uow.revision_action.has_successor(action["id"]),
        )

    def record_issue_disposition(
        self, principal: VerifiedPrincipal, command: RecordIssueDispositionCommand
    ) -> IssueDispositionReadback:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordIssueDispositionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed disposition command required")
        for attempt in range(3):
            try:
                return self._record_disposition_once(principal, command)
            except ResearchBaseError as error:
                if error.message == "reload issue disposition":
                    # The failed UoW has rolled back; compare saved history only.
                    return self._record_disposition_once(principal, command, reload_only=True)
                if (
                    error.code == ErrorCode.CONCURRENT_MODIFICATION
                    and (error.details or {}).get("retryable_b08")
                    and attempt < 2
                ):
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable disposition retry")

    def _record_disposition_once(
        self, principal, command, *, reload_only=False
    ) -> IssueDispositionReadback:
        with self._factory() as uow:
            uow.enable_issue_disposition_error_normalization()
            uow.configure_revision_transaction()
            repo = uow.internal_review
            repo.prepare_disposition(command.id)
            uow.enable_revision_action_snapshot_reads()
            project = command.project_id
            self._disposition_authorize(uow, principal, project)
            event = repo.disposition_event(command.id)
            if event is not None:
                if event["project_id"] != project or event["actor_id"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "event unavailable")
                expected = {
                    **asdict(command),
                    "new_status": command.disposition,
                    "issue_id": command.review_issue_id,
                }
                if any(
                    event[k] != expected[k]
                    for k in (
                        "issue_id",
                        "new_status",
                        "revision_action_id",
                        "re_review_record_id",
                        "decision_id",
                        "rationale",
                    )
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "event UUID reused with changed material")
                result = self._issue_history(uow, project, command.review_issue_id).disposition
                if result is None:
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "event UUID identifies root")
                self._disposition_authorize(uow, principal, project)
                return result
            issue = repo.issue(command.review_issue_id, project)
            if issue is None:
                self._issue_absent(uow, command.review_issue_id)
            if reload_only:
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "Issue already disposed")
            if (
                issue["claim_version_id"] is None
                and issue["scientific_conclusion_version_id"] is None
            ):
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "target disposition deferred")
            writer = dict(
                write=True,
                opener=issue["reviewer_actor_id"],
                dismiss=command.disposition == "DISMISSED",
            )
            self._disposition_authorize(uow, principal, project, **writer)
            repo.lock_disposition_issues(
                issue["id"],
                (issue["review_record_id"], command.re_review_record_id),
                command.re_review_record_id,
            )
            issue = repo.issue(command.review_issue_id, project)
            if issue is None:
                self._issue_absent(uow, command.review_issue_id)
            if issue["status"] != "OPEN":
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "Issue already disposed")
            event = {
                **asdict(command),
                "issue_id": issue["id"],
                "actor_id": principal.actor_id,
                "new_status": command.disposition,
                "occurred_at": uow.source_version.at(),
            }
            self._disposition_readback(uow, project, issue, event, current=True)
            self._disposition_authorize(uow, principal, project, **writer)
            repo.insert_disposition({**asdict(command), "actor_id": principal.actor_id})
            repo.force_constraints()
            result = self._issue_history(uow, project, issue["id"]).disposition
            if result is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved disposition missing")
            self._disposition_authorize(uow, principal, project, **writer)
            uow.commit()
            return result

    @staticmethod
    def _issue_absent(uow, identity) -> NoReturn:
        if uow.revision_action.reference_exists("ReviewIssue", identity):
            _fail(ErrorCode.FORBIDDEN, "Issue unavailable")
        _fail(ErrorCode.NOT_FOUND, "Issue not found")

    def _issue_history(self, uow, project, identity):
        issue = uow.internal_review.issue(identity, project)
        if issue is None:
            self._issue_absent(uow, identity)
        review = uow.internal_review.review(issue["review_record_id"], project)
        self._verify(uow, review)
        self._issues(uow, review)
        events = [
            e for e in uow.internal_review.issue_events(review["id"]) if e["issue_id"] == identity
        ]
        try:
            history = self._history_events(uow, review, issue, events)
        except (ValueError, KeyError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved Issue history")
        terminal = next((e for e in events if e["prior_status"] == "OPEN"), None)
        disposition = (
            self._disposition_readback(uow, project, issue, terminal) if terminal else None
        )
        if issue["manuscript_version_id"] is not None:
            target = self._manuscript_target(uow, project, issue["manuscript_version_id"])
            parent = uow.publication.publication(target["publication_id"], project)
            validity = self._manuscripts.verify_in_uow(
                uow, project, parent, target
            ).current_validity
        else:
            validity = self._revision_service()._basis(uow, issue, project)[1]
        return IssueHistoryReadback(
            project,
            identity,
            review["id"],
            issue["severity"],
            issue["issue_type"],
            issue["description"],
            issue["status"],
            issue["created_at"],
            issue["claim_version_id"],
            issue["scientific_conclusion_version_id"],
            issue["manuscript_version_id"],
            issue["target_content_hash"],
            validity,
            history,
            disposition,
        )

    def get_issue_history(
        self, principal: VerifiedPrincipal, project_id: UUID, review_issue_id: UUID
    ) -> IssueHistoryReadback:
        self._disposition_input(principal, project_id, review_issue_id)
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._disposition_authorize(uow, principal, project_id)
            result = self._issue_history(uow, project_id, review_issue_id)
            self._disposition_authorize(uow, principal, project_id)
            return result

    def get_issue_disposition(
        self, principal: VerifiedPrincipal, project_id: UUID, id: UUID
    ) -> IssueDispositionReadback:
        self._disposition_input(principal, project_id, id)
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._disposition_authorize(uow, principal, project_id)
            event = uow.internal_review.disposition_event(id)
            if event is not None and event["project_id"] != project_id:
                _fail(ErrorCode.FORBIDDEN, "event unavailable")
            if event is None or event["prior_status"] != "OPEN":
                _fail(ErrorCode.NOT_FOUND, "disposition not found")
            result = self._issue_history(uow, project_id, event["issue_id"]).disposition
            if result is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved disposition missing")
            self._disposition_authorize(uow, principal, project_id)
            return result

    def collect_manuscript_review_basis(
        self,
        uow: UnitOfWork,
        project_id: UUID,
        manuscript_version_id: UUID,
        *,
        prepared: bool = False,
    ) -> ManuscriptReviewBasis:
        """Inside a SHARE-first write UoW after caller locks and authorization.

        This observation cannot be reused outside its transaction. Caller retains
        authority/effect responsibility and must recheck credentials after waits.
        """
        if type(project_id) is not UUID or type(manuscript_version_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact manuscript basis required")
        if prepared:
            uow.decision.require_readiness_snapshot()
        else:
            uow.internal_review.require_write_prepared()
            uow.internal_review.lock_manuscript(manuscript_version_id)
            uow.literature_search_plan.lock_project(project_id)
            uow.internal_review.lock_publication(manuscript_version_id, project_id)
        uow.enable_revision_action_snapshot_reads()
        target = self._manuscript_target(uow, project_id, manuscript_version_id, current=True)
        rows = uow.internal_review.manuscript_reviews_snapshot(manuscript_version_id, project_id)
        reviews = []
        blockers = []
        refs = [("ManuscriptVersion", manuscript_version_id, target["content_hash"])]
        for row in rows:
            self._verify_manuscript_review(uow, row)
            issues = self._issues(uow, row)
            reviews.append(self._view(row, issues))
            blockers.extend(
                i["id"] for i in issues if i["status"] == "OPEN" and i["severity"] == "BLOCKING"
            )
            refs.append(("InternalReviewRecord", row["id"], row["content_hash"]))
        basis = tuple(
            DecisionBasisReference(kind, identity, digest, ordinal)
            for ordinal, (kind, identity, digest) in enumerate(
                sorted(refs, key=lambda r: (r[0], str(r[1]), r[2]))
            )
        )
        return ManuscriptReviewBasis(
            project_id,
            manuscript_version_id,
            target["content_hash"],
            basis,
            tuple(reviews),
            tuple(sorted(blockers, key=str)),
        )


@dataclass(frozen=True, slots=True)
class ManuscriptReviewBasis:
    project_id: UUID
    manuscript_version_id: UUID
    target_content_hash: str
    basis: tuple[DecisionBasisReference, ...]
    reviews: tuple[InternalReviewReadback, ...]
    blocking_issue_ids: tuple[UUID, ...]

    gate_satisfied: bool = field(init=False)

    def __post_init__(self) -> None:
        from researchbase.domain.scientific_conclusion import _digest

        if type(self.project_id) is not UUID or type(self.manuscript_version_id) is not UUID:
            raise ValueError("exact basis UUIDs required")
        _digest(self.target_content_hash, "manuscript hash")
        if (
            type(self.basis) is not tuple
            or type(self.reviews) is not tuple
            or type(self.blocking_issue_ids) is not tuple
            or any(type(ref) is not DecisionBasisReference for ref in self.basis)
            or any(type(review) is not InternalReviewReadback for review in self.reviews)
            or any(type(identity) is not UUID for identity in self.blocking_issue_ids)
        ):
            raise ValueError("closed manuscript review basis required")
        object.__setattr__(
            self, "gate_satisfied", bool(self.reviews) and not self.blocking_issue_ids
        )
