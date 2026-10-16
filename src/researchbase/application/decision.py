"""Minimal authenticated PR2-15 decision command over exact immutable basis."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, NoReturn
from uuid import UUID

from researchbase.application.internal_review import InternalReviewService
from researchbase.application.ports import UnitOfWork
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.decision import (
    DecisionBasisReference,
    RevisionChoice,
    RevisionPurpose,
    decision_basis_material,
    decision_content_material,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.scientific_conclusion import _text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class RecordDecisionCommand:
    id: UUID
    project_id: UUID
    scientific_conclusion_version_id: UUID
    question: str
    rationale: str
    decision_type: str = "INTERNAL_SCIENTIFIC_RELEASE"
    decision: str = "PROCEED"

    def __post_init__(self) -> None:
        try:
            if (
                any(
                    type(x) is not UUID
                    for x in (
                        self.id,
                        self.project_id,
                        self.scientific_conclusion_version_id,
                    )
                )
                or self.decision_type != "INTERNAL_SCIENTIFIC_RELEASE"
                or self.decision != "PROCEED"
            ):
                raise ValueError("exact UUIDs and initial internal PROCEED command required")
            object.__setattr__(self, "question", _text(self.question, "question"))
            object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        except ValueError as exc:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from None


_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_WRITERS = frozenset({"OWNER", "APPROVER"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class DecisionReadback:
    id: UUID
    project_id: UUID
    decision_type: str
    decision: str
    question: str
    rationale: str
    decided_by: UUID
    decided_at: datetime
    scientific_conclusion_version_id: UUID
    target_content_hash: str
    basis: tuple[DecisionBasisReference, ...]
    basis_set_hash: str
    content_hash: str


class DecisionService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, literature_evidence: Any
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._conclusions = ScientificConclusionService(factory, credentials, literature_evidence)
        self._reviews = InternalReviewService(factory, credentials, literature_evidence)

    def _authorize(self, uow, principal, project, roles):
        # This command imposes no HUMAN-only decider/read policy. It still checks
        # the canonical exact verified subject binding and effective assignments.
        uow.literature_search_plan.lock_project(project)
        rows = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READERS or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (
                    row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    @staticmethod
    def _basis(rows):
        try:
            return tuple(
                DecisionBasisReference(row["type"], row["id"], row["content_hash"], row["ordinal"])
                for row in rows
            )
        except (ValueError, KeyError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision basis invalid")

    def _readback(self, uow, row):
        basis = self._basis(uow.decision.basis(row["id"]))
        conclusions = [ref for ref in basis if ref.type == "ScientificConclusionVersion"]
        reviews = [ref for ref in basis if ref.type == "InternalReviewRecord"]
        if (
            len(conclusions) != 1
            or not reviews
            or len(basis) != 1 + len(reviews)
            or row["supersedes_decision_id"] is not None
            or row["decision_type"] != "INTERNAL_SCIENTIFIC_RELEASE"
            or row["decision"] != "PROCEED"
            or row["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved initial decision invalid")
        target = conclusions[0]
        target_row = uow.internal_review.conclusion_target(target.id, row["project_id"])
        if target_row is None or target_row["content_hash"] != target.content_hash:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved target binding invalid")
        self._conclusions._view(
            uow,
            row["project_id"],
            target_row["scientific_conclusion_id"],
            target.id,
            require_current=False,
        )
        for ref in reviews:
            review = uow.internal_review.review(ref.id, row["project_id"])
            if (
                review is None
                or review["scientific_conclusion_version_id"] != target.id
                or review["target_content_hash"] != target.content_hash
                or review["content_hash"] != ref.content_hash
                or not uow.decision.review_creation_authorized(review)
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review binding invalid")
            self._reviews._verify(uow, review)
        try:
            basis_hash = str(sha256_canonical_json(decision_basis_material(basis)))
            content_hash = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        row["decided_by"],
                        basis_hash,
                    )
                )
            )
        except ValueError:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision material invalid")
        if basis_hash != row["basis_set_hash"] or content_hash != row["content_hash"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision hash mismatch")
        return DecisionReadback(
            row["id"],
            row["project_id"],
            row["decision_type"],
            row["decision"],
            row["question"],
            row["rationale"],
            row["decided_by"],
            row["decided_at"],
            target.id,
            target.content_hash,
            basis,
            basis_hash,
            content_hash,
        )

    def record_decision(
        self, principal: VerifiedPrincipal, command: RecordDecisionCommand
    ) -> DecisionReadback:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordDecisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed RecordDecisionCommand required")
        for attempt in range(3):
            try:
                return self._record_once(principal, command)
            except ResearchBaseError as error:
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                # No driver or credential exception chain crosses this boundary.
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable decision retry")

    def _record_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            repo = uow.decision
            repo.lock_request(command.id)
            target = repo.target(command.scientific_conclusion_version_id, command.project_id)
            repo.lock_snapshot()
            self._authorize(uow, principal, command.project_id, _READERS)
            existing = repo.decision(command.id, command.project_id)
            if existing is not None:
                if existing["decided_by"] != principal.actor_id:
                    _fail(
                        ErrorCode.FORBIDDEN, "current authenticated project authority unavailable"
                    )
                result = self._readback(uow, existing)
                if (
                    result.scientific_conclusion_version_id
                    != command.scientific_conclusion_version_id
                    or result.decision_type != command.decision_type
                    or result.decision != command.decision
                    or result.question != command.question
                    or result.rationale != command.rationale
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "decision request material conflicts")
                self._authorize(uow, principal, command.project_id, _READERS)
                return result
            if repo.decision_exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
            self._authorize(uow, principal, command.project_id, _WRITERS)
            if target is None or target["status"] != "FROZEN" or target["frozen_at"] is None:
                _fail(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen same-project target required"
                )
            view = self._conclusions._view(
                uow,
                command.project_id,
                target["scientific_conclusion_id"],
                target["id"],
                require_current=True,
            )
            if view.validity != "VALID":
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current target closure invalid")
            authors = repo.material_authors(target["id"])
            if principal.actor_id in authors:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST,
                    "decider must be independent of material authors",
                )
            rows = repo.reviews(target["id"], command.project_id)
            if not rows:
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "complete eligible review basis required",
                )
            for review in rows:
                self._reviews._verify(uow, review)
                if (
                    review["target_content_hash"] != target["content_hash"]
                    or review["reviewer_actor_id"] in authors
                    or not repo.review_creation_authorized(review)
                ):
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "matching review provenance invalid"
                    )
            if repo.has_blockers(target["id"], command.project_id):
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "applicable blocking issue remains open"
                )
            if repo.scoped_decision(target["id"], command.project_id) is not None:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "initial decision scope already recorded")
            refs = [("ScientificConclusionVersion", target["id"], target["content_hash"])]
            refs += [("InternalReviewRecord", row["id"], row["content_hash"]) for row in rows]
            basis = tuple(
                DecisionBasisReference(kind, identity, digest, ordinal)
                for ordinal, (kind, identity, digest) in enumerate(
                    sorted(refs, key=lambda ref: (ref[0], str(ref[1]), ref[2]))
                )
            )
            basis_hash = str(sha256_canonical_json(decision_basis_material(basis)))
            content_hash = str(
                sha256_canonical_json(
                    decision_content_material(
                        command.project_id,
                        command.decision_type,
                        command.question,
                        command.decision,
                        command.rationale,
                        principal.actor_id,
                        basis_hash,
                    )
                )
            )
            at = self._authorize(uow, principal, command.project_id, _WRITERS)
            repo.insert_decision(
                {
                    "id": command.id,
                    "project_id": command.project_id,
                    "decision_type": command.decision_type,
                    "decision": command.decision,
                    "question": command.question,
                    "rationale": command.rationale,
                    "decided_by": principal.actor_id,
                    "decided_at": at,
                    "supersedes_decision_id": None,
                    "basis_set_hash": basis_hash,
                    "content_hash": content_hash,
                    "hash_scheme": "sha256-cjson-v1",
                }
            )
            for ref in basis:
                if ref.type == "ScientificConclusionVersion":
                    repo.insert_conclusion_basis(
                        {
                            "decision_id": command.id,
                            "scientific_conclusion_version_id": ref.id,
                            "ordinal": ref.ordinal,
                        }
                    )
                else:
                    repo.insert_review_basis(
                        {
                            "decision_id": command.id,
                            "internal_review_record_id": ref.id,
                            "ordinal": ref.ordinal,
                        }
                    )
            result = self._readback(uow, repo.decision(command.id, command.project_id))
            self._authorize(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def _revision_policy(self):
        from researchbase.application.revision_action import RevisionActionService

        return RevisionActionService(
            self._factory, self._credentials, self._conclusions._literature
        )

    def _revision_readback(self, uow, row):
        from researchbase.domain.decision import validate_revision_choice

        try:
            validate_revision_choice(row["decision_type"], row["decision"])
            if row["supersedes_decision_id"] is not None or row["hash_scheme"] != "sha256-cjson-v1":
                raise ValueError("revision Decision material invalid")
            concern = uow.decision.concern(row["id"])
            issue = (
                uow.revision_action.issue(concern["review_issue_id"], row["project_id"])
                if concern
                else None
            )
            if issue is None:
                raise ValueError("exact concern absent")
            policy = self._revision_policy()
            old, validity, _ = policy._basis(uow, issue, row["project_id"])
            kind = (
                "ClaimVersion"
                if issue["claim_version_id"] is not None
                else "ScientificConclusionVersion"
            )
            basis = self._basis(uow.decision.revision_basis(row["id"]))
            targets = [r for r in basis if r.type != "InternalReviewRecord"]
            reviews = [r for r in basis if r.type == "InternalReviewRecord"]
            if (
                len(targets) != 1
                or targets[0].type != kind
                or targets[0].id != old["id"]
                or targets[0].content_hash != old["content_hash"]
                or not reviews
                or issue["review_record_id"] not in {r.id for r in reviews}
            ):
                raise ValueError("exact saved basis invalid")
            authors = uow.decision.material_authors(old["id"], claim=kind == "ClaimVersion")
            if row["decided_by"] in authors or not uow.decision.revision_creation_authorized(row):
                raise ValueError("saved decider independence invalid")
            for ref in reviews:
                review = uow.internal_review.review(ref.id, row["project_id"])
                if (
                    review is None
                    or review["claim_version_id"] != issue["claim_version_id"]
                    or review["scientific_conclusion_version_id"]
                    != issue["scientific_conclusion_version_id"]
                    or review["target_content_hash"] != old["content_hash"]
                    or review["content_hash"] != ref.content_hash
                    or review["hash_scheme"] != "sha256-cjson-v1"
                    or review["reviewer_actor_id"] in authors
                    or not uow.decision.review_creation_authorized(review)
                ):
                    raise ValueError("saved review binding invalid")
                self._reviews._verify(uow, review)
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        row["decided_by"],
                        bh,
                    )
                )
            )
            if bh != row["basis_set_hash"] or digest != row["content_hash"]:
                raise ValueError("saved Decision hash invalid")
            return RevisionDecisionReadback(
                row["id"],
                row["project_id"],
                issue["id"],
                row["decided_by"],
                row["decision_type"],
                row["decision"],
                row["question"],
                row["rationale"],
                row["decided_at"],
                issue["claim_version_id"],
                issue["scientific_conclusion_version_id"],
                old["content_hash"],
                bh,
                digest,
                row["hash_scheme"],
                basis,
                validity,
            )
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision Decision invalid")

    def record_revision_decision(self, principal, command):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordRevisionDecisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed revision Decision command required")
        for attempt in range(3):
            try:
                return self._record_revision_once(principal, command)
            except ResearchBaseError as error:
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable revision Decision retry")

    def _record_revision_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction()
            uow.revision_action.lock_snapshot()
            uow.decision.lock_request(command.id)
            uow.enable_revision_action_snapshot_reads()
            policy = self._revision_policy()
            auth = policy._authorize
            auth(uow, principal, command.project_id, _READERS)
            repo = uow.decision
            saved = repo.decision(command.id, command.project_id)
            if saved is not None:
                if saved["decided_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
                result = self._revision_readback(uow, saved)
                if any(
                    getattr(result, k) != getattr(command, k)
                    for k in (
                        "review_issue_id",
                        "question",
                        "rationale",
                        "decision",
                        "decision_type",
                    )
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision request material conflicts")
                auth(uow, principal, command.project_id, _READERS)
                return result
            if repo.decision_exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
            auth(uow, principal, command.project_id, _WRITERS)
            issue = uow.revision_action.issue(command.review_issue_id, command.project_id)
            if issue is None:
                policy._absent(uow, "ReviewIssue", command.review_issue_id)
            reviews = repo.revision_reviews(issue, command.project_id, lock=True)
            uow.revision_action.lock_issue(command.review_issue_id)
            if repo.concern_decision(issue["id"]) is not None:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "concern Decision already recorded")
            old, _, _ = policy._basis(uow, issue, command.project_id)
            kind = (
                "ClaimVersion"
                if issue["claim_version_id"] is not None
                else "ScientificConclusionVersion"
            )
            authors = repo.material_authors(old["id"], claim=kind == "ClaimVersion")
            if principal.actor_id in authors:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST,
                    "decider must be independent of material authors",
                )
            if not reviews or issue["review_record_id"] not in {r["id"] for r in reviews}:
                _fail(ErrorCode.DECISION_BASIS_INVALID, "complete review basis required")
            for review in reviews:
                self._reviews._verify(uow, review)
                if (
                    review["target_content_hash"] != old["content_hash"]
                    or review["hash_scheme"] != "sha256-cjson-v1"
                    or review["reviewer_actor_id"] in authors
                    or not repo.review_creation_authorized(review)
                ):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "matching review invalid")
            refs = [(kind, old["id"], old["content_hash"])] + [
                ("InternalReviewRecord", r["id"], r["content_hash"]) for r in reviews
            ]
            basis = tuple(
                DecisionBasisReference(k, i, h, n)
                for n, (k, i, h) in enumerate(sorted(refs, key=lambda r: (r[0], str(r[1]), r[2])))
            )
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        command.project_id,
                        command.decision_type,
                        command.question,
                        command.decision,
                        command.rationale,
                        principal.actor_id,
                        bh,
                    )
                )
            )
            at = auth(uow, principal, command.project_id, _WRITERS)
            repo.insert_decision(
                dict(
                    id=command.id,
                    project_id=command.project_id,
                    decision_type=command.decision_type,
                    decision=command.decision,
                    question=command.question,
                    rationale=command.rationale,
                    decided_by=principal.actor_id,
                    decided_at=at,
                    supersedes_decision_id=None,
                    basis_set_hash=bh,
                    content_hash=digest,
                    hash_scheme="sha256-cjson-v1",
                )
            )
            repo.insert_concern(command.id, issue["id"])
            for ref in basis:
                if ref.type == "ClaimVersion":
                    repo.insert_claim_basis(
                        dict(decision_id=command.id, claim_version_id=ref.id, ordinal=ref.ordinal)
                    )
                elif ref.type == "ScientificConclusionVersion":
                    repo.insert_conclusion_basis(
                        dict(
                            decision_id=command.id,
                            scientific_conclusion_version_id=ref.id,
                            ordinal=ref.ordinal,
                        )
                    )
                else:
                    repo.insert_review_basis(
                        dict(
                            decision_id=command.id,
                            internal_review_record_id=ref.id,
                            ordinal=ref.ordinal,
                        )
                    )
            repo.force_revision_constraints()
            result = self._revision_readback(uow, repo.decision(command.id, command.project_id))
            auth(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def get_revision_decision(self, principal, project_id, identity):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project_id) is not UUID or type(identity) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact UUIDs required")
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            policy = self._revision_policy()
            policy._authorize(uow, principal, project_id, _READERS)
            row = uow.decision.decision(identity, project_id)
            if row is None:
                policy._absent(uow, "DecisionRecord", identity)
            result = self._revision_readback(uow, row)
            policy._authorize(uow, principal, project_id, _READERS)
            return result


@dataclass(frozen=True, slots=True)
class RecordRevisionDecisionCommand:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    question: str
    rationale: str
    decision: RevisionChoice
    decision_type: RevisionPurpose = "REVISION_RESPONSE"

    def __post_init__(self):
        from researchbase.domain.decision import revision_decision_text, validate_revision_choice

        try:
            if any(type(x) is not UUID for x in (self.id, self.project_id, self.review_issue_id)):
                raise ValueError("exact UUIDs required")
            validate_revision_choice(self.decision_type, self.decision)
            for name in ("question", "rationale"):
                object.__setattr__(self, name, revision_decision_text(getattr(self, name), name))
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "closed revision Decision material required")


@dataclass(frozen=True, slots=True)
class RevisionDecisionReadback:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    decided_by: UUID
    decision_type: RevisionPurpose
    decision: RevisionChoice
    question: str
    rationale: str
    decided_at: datetime
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    target_content_hash: str
    basis_set_hash: str
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    basis: tuple[DecisionBasisReference, ...]
    target_validity: str
